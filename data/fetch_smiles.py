"""
SMILES extractor — extracts canonical SMILES from FlavorDB2 molecules_json column
in ingredients.csv, then queries PubChem PUG-REST for any remaining gaps.

Writes all results to data/raw/pubchem_cache.json as {pubchem_id: smiles_or_null}.

Run standalone:
    python data/fetch_smiles.py
    python data/fetch_smiles.py --force   # re-run even if cache already complete

PubChem PUG-REST endpoint:
    https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/CanonicalSMILES/txt
    Rate limit: ≤5 req/sec (300/min) per PubChem policy
"""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

# ---------------------------------------------------------------------------
# Logging — file + console
# ---------------------------------------------------------------------------
os.makedirs("logs", exist_ok=True)

_log_format = "%(asctime)s %(levelname)-8s %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=_log_format,
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("fetch_smiles")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/CanonicalSMILES/txt"
SEMAPHORE_LIMIT = 5  # ≤5 req/sec per PubChem policy
CACHE_PATH = Path("data/raw/pubchem_cache.json")
INGREDIENTS_CSV = Path("data/raw/ingredients.csv")
MOLECULES_CSV = Path("data/raw/molecules.csv")


# ---------------------------------------------------------------------------
# Async PubChem fetch helpers
# ---------------------------------------------------------------------------

async def fetch_smiles_for_id(
    client: "httpx.AsyncClient",
    sem: asyncio.Semaphore,
    pubchem_id: int,
) -> tuple[int, "str | None"]:
    """Fetch SMILES for a single PubChem CID.

    Returns (pubchem_id, smiles_string) on 200.
    Returns (pubchem_id, None) on 404 — legitimate: molecule not in PubChem.
    Raises on 5xx — do NOT store as null; caller must handle.
    """
    async with sem:
        try:
            resp = await client.get(
                PUBCHEM_URL.format(cid=pubchem_id),
                timeout=15.0,
            )
            if resp.status_code == 200:
                return pubchem_id, resp.text.strip()
            elif 400 <= resp.status_code < 500:
                # 404 = legitimate: molecule not in PubChem
                # 400 = bad request (e.g., CID=0 is invalid) — treat as not found
                logger.info(
                    "PubChem %d for pubchem_id=%d (stored as null)",
                    resp.status_code,
                    pubchem_id,
                )
                return pubchem_id, None  # client error → no SMILES
            else:
                # 5xx and other errors — raise so caller doesn't store as null
                resp.raise_for_status()
        except Exception:
            raise  # re-raise; caller handles per-ID


async def fetch_smiles_for_ids(pubchem_ids: list[int]) -> dict[int, "str | None"]:
    """Fetch SMILES for a list of PubChem CIDs concurrently.

    Returns dict mapping pubchem_id → smiles_or_None.
    IDs that raise 5xx errors are NOT included in the result (they abort the run).

    This function is also the public API used by test_smiles_missing_logged.
    """
    if not _HTTPX_AVAILABLE:
        raise ImportError("httpx is required for PubChem fetching. Install with: pip install httpx")

    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    results: dict[int, "str | None"] = {}

    async with httpx.AsyncClient() as client:
        tasks = [fetch_smiles_for_id(client, sem, cid) for cid in pubchem_ids]
        for coro in asyncio.as_completed(tasks):
            try:
                cid, smiles = await coro
                results[cid] = smiles
            except Exception as exc:
                # 5xx / network error — re-raise to abort (do NOT store as null)
                logger.error("PubChem fetch failed (aborting): %s", exc)
                raise

    return results


async def fetch_missing_smiles(missing_ids: list[int]) -> dict[int, "str | None"]:
    """Fetch SMILES for gap IDs only. Wraps fetch_smiles_for_ids with tqdm progress.

    Returns dict mapping pubchem_id → smiles_or_None.
    """
    if not missing_ids:
        return {}

    if not _HTTPX_AVAILABLE:
        raise ImportError("httpx is required for PubChem fetching. Install with: pip install httpx")

    sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
    results: dict[int, "str | None"] = {}

    logger.info("Fetching %d SMILES from PubChem (rate ≤%d req/sec)...", len(missing_ids), SEMAPHORE_LIMIT)

    async with httpx.AsyncClient() as client:
        tasks = [fetch_smiles_for_id(client, sem, cid) for cid in missing_ids]
        with tqdm(total=len(tasks), desc="PubChem fetch", unit="mol") as pbar:
            for coro in asyncio.as_completed(tasks):
                try:
                    cid, smiles = await coro
                    results[cid] = smiles
                except Exception as exc:
                    logger.error("PubChem fetch failed (aborting): %s", exc)
                    raise
                finally:
                    pbar.update(1)

    return results


# ---------------------------------------------------------------------------
# FlavorDB2 extraction
# ---------------------------------------------------------------------------

def _extract_flavordb2_smiles() -> dict[int, "str | None"]:
    """Extract SMILES from molecules_json column in ingredients.csv.

    Returns {pubchem_id: smile_or_none} — deduped by pubchem_id.
    Only stores non-empty smile values; missing/empty smile fields return None.
    """
    if not INGREDIENTS_CSV.exists():
        logger.error("ingredients.csv not found at %s", INGREDIENTS_CSV)
        return {}

    ing_df = pd.read_csv(INGREDIENTS_CSV)
    if "molecules_json" not in ing_df.columns:
        logger.error("molecules_json column not found in ingredients.csv")
        return {}

    smiles_dict: dict[int, "str | None"] = {}
    parse_errors = 0

    for _, row in ing_df.iterrows():
        raw_json = row.get("molecules_json")
        if pd.isna(raw_json) or not raw_json:
            continue
        try:
            molecules = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            parse_errors += 1
            continue

        for mol in molecules:
            pubchem_id = mol.get("pubchem_id")
            if pubchem_id is None:
                continue
            pubchem_id = int(pubchem_id)
            smile = mol.get("smile") or None  # convert empty string to None

            # Deduplicate: first non-null smile wins
            if pubchem_id not in smiles_dict:
                smiles_dict[pubchem_id] = smile
            elif smiles_dict[pubchem_id] is None and smile is not None:
                smiles_dict[pubchem_id] = smile  # upgrade null to actual value

    if parse_errors:
        logger.warning("Skipped %d rows with unparseable molecules_json", parse_errors)

    logger.info("FlavorDB2 extraction: %d unique pubchem_ids", len(smiles_dict))
    return smiles_dict


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def fetch_smiles(force: bool = False) -> dict:
    """Extract SMILES for all molecules. Returns the complete cache dict.

    Steps:
    1. Skip-if-exists gate: return early if cache is complete and not force.
    2. Extract SMILES from FlavorDB2 molecules_json in ingredients.csv.
    3. Find gap IDs (in molecules.csv but not in FlavorDB2 extraction).
    4. Fetch gaps from PubChem via async httpx (likely zero for this dataset).
    5. Merge, write pubchem_cache.json, assert set equality gate.
    6. Log summary table.
    """
    # ----------------------------------------------------------------
    # Step 1: Skip-if-exists gate
    # ----------------------------------------------------------------
    if CACHE_PATH.exists() and not force:
        try:
            with open(CACHE_PATH) as f:
                existing_cache: dict = json.load(f)

            # Check completeness
            if MOLECULES_CSV.exists():
                mol_df = pd.read_csv(MOLECULES_CSV)
                all_ids = set(str(int(pid)) for pid in mol_df["pubchem_id"].dropna())
                cache_keys = set(existing_cache.keys())

                if cache_keys == all_ids:
                    n = len(existing_cache)
                    logger.info("[SKIP] pubchem_cache.json already complete (%d entries)", n)
                    return existing_cache
                else:
                    missing_count = len(all_ids - cache_keys)
                    logger.info(
                        "pubchem_cache.json incomplete: %d IDs missing; re-running",
                        missing_count,
                    )
            else:
                logger.warning("molecules.csv not found; cannot verify cache completeness")
                logger.info("[SKIP] pubchem_cache.json exists (could not verify completeness)")
                return existing_cache
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("Could not load existing cache (%s); re-running", exc)

    # ----------------------------------------------------------------
    # Step 2: Extract FlavorDB2 SMILES
    # ----------------------------------------------------------------
    logger.info("Extracting SMILES from FlavorDB2 molecules_json...")
    flavordb_smiles = _extract_flavordb2_smiles()

    # ----------------------------------------------------------------
    # Step 3: Load all pubchem_ids from molecules.csv, find gaps
    # ----------------------------------------------------------------
    if not MOLECULES_CSV.exists():
        raise FileNotFoundError(f"molecules.csv not found at {MOLECULES_CSV}")

    mol_df = pd.read_csv(MOLECULES_CSV)
    all_pubchem_ids: list[int] = [int(pid) for pid in mol_df["pubchem_id"].dropna()]
    all_ids_set: set[str] = set(str(pid) for pid in all_pubchem_ids)

    # Find gap IDs: in molecules.csv but not extracted from FlavorDB2
    gap_ids: list[int] = [
        pid for pid in all_pubchem_ids
        if pid not in flavordb_smiles
    ]

    if gap_ids:
        logger.info("Found %d gap IDs not in FlavorDB2 extraction; querying PubChem...", len(gap_ids))
    else:
        logger.info("No gap IDs — FlavorDB2 SMILES cover 100%% of molecules.csv (0 PubChem queries needed)")

    # ----------------------------------------------------------------
    # Step 4: Fetch gaps from PubChem (async)
    # ----------------------------------------------------------------
    pubchem_results: dict[int, "str | None"] = {}
    if gap_ids:
        pubchem_results = asyncio.run(fetch_missing_smiles(gap_ids))

    # ----------------------------------------------------------------
    # Step 5: Merge and write
    # ----------------------------------------------------------------
    # Build final cache: every pubchem_id gets an entry (may be None)
    cache: dict[str, "str | None"] = {}
    for pid in all_pubchem_ids:
        key = str(pid)
        # Priority: FlavorDB2 SMILES > PubChem SMILES > None
        if pid in flavordb_smiles and flavordb_smiles[pid] is not None:
            cache[key] = flavordb_smiles[pid]
        elif pid in pubchem_results:
            cache[key] = pubchem_results[pid]
        elif pid in flavordb_smiles:
            # FlavorDB2 had None for this ID
            cache[key] = None
            logger.info("No SMILES found for pubchem_id=%d (FlavorDB2 null, not in PubChem gap list)", pid)
        else:
            cache[key] = None

    # Log molecules with missing SMILES
    missing_smiles_pids = [k for k, v in cache.items() if v is None]
    if missing_smiles_pids:
        logger.warning(
            "%d molecules have no SMILES (null in cache): %s",
            len(missing_smiles_pids),
            missing_smiles_pids[:10],
        )

    # Write cache
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
    logger.info("Wrote pubchem_cache.json: %d entries", len(cache))

    # ----------------------------------------------------------------
    # Step 6: Gate check — assert set equality
    # ----------------------------------------------------------------
    cache_keys = set(cache.keys())
    if cache_keys != all_ids_set:
        extra = cache_keys - all_ids_set
        missing = all_ids_set - cache_keys
        msg = (
            f"Cache completeness gate FAILED: "
            f"{len(missing)} IDs missing, {len(extra)} extra IDs"
        )
        logger.error(msg)
        raise AssertionError(msg)

    # ----------------------------------------------------------------
    # Step 7: Summary table
    # ----------------------------------------------------------------
    n_total = len(cache)
    n_with_smiles = sum(1 for v in cache.values() if v is not None)
    n_missing = n_total - n_with_smiles

    logger.info(
        "=== SMILES fetch summary: total=%d, with_smiles=%d, missing_smiles=%d ===",
        n_total,
        n_with_smiles,
        n_missing,
    )

    return cache


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch SMILES for all molecules from FlavorDB2 + PubChem gap-fill.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python data/fetch_smiles.py              # run (skip if cache already complete)
  python data/fetch_smiles.py --force      # re-run even if cache exists
""",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if pubchem_cache.json already exists and is complete.",
    )
    args = parser.parse_args()
    fetch_smiles(force=args.force)


if __name__ == "__main__":
    main()
