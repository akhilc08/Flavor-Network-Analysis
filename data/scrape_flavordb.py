"""
FlavorDB2 scraper — fetches entity IDs 1-1100, caches all HTTP responses to
SQLite via requests_cache, and writes two CSVs:

    data/raw/ingredients.csv   — one row per ingredient entity
    data/raw/molecules.csv     — deduplicated molecule table

Run standalone:
    python data/scrape_flavordb.py
    python data/scrape_flavordb.py --force   # re-scrape even if outputs exist

API endpoint (RESEARCH.md confirmed):
    https://cosylab.iiitd.edu.in/flavordb/entities_json?id=<N>
    NOTE: path is /flavordb/ (no "2") — this is correct.
"""

import argparse
import json
import logging
import os

import pandas as pd
import requests_cache
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

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
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://cosylab.iiitd.edu.in/flavordb/entities_json?id="
CACHE_PATH = "data/raw/flavordb_cache"
OUT_INGREDIENTS = "data/raw/ingredients.csv"
OUT_MOLECULES = "data/raw/molecules.csv"
MAX_ID = 1100
CONSECUTIVE_404_STOP = 10


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

def scrape_flavordb(force: bool = False) -> None:
    """Fetch FlavorDB2 entities 1–MAX_ID and write ingredients.csv + molecules.csv.

    Parameters
    ----------
    force:
        If True, re-scrape and overwrite even when output files already exist.
    """
    # --- Idempotence check ---
    if not force and os.path.exists(OUT_INGREDIENTS):
        logger.info("[SKIP] %s already exists. Use --force to re-scrape.", OUT_INGREDIENTS)
        return

    # --- Directory setup ---
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data/raw", exist_ok=True)

    # --- requests_cache session ---
    # Cache 404s too — entity gaps in FlavorDB2 are stable/permanent.
    session = requests_cache.CachedSession(
        cache_name=CACHE_PATH,
        backend="sqlite",
        allowable_codes=[200, 404],
        expire_after=None,  # never expire
    )

    ingredients: list[dict] = []
    molecules: dict[int, dict] = {}  # keyed by pubchem_id for deduplication
    scraped = 0
    failed = 0
    consecutive_404s = 0

    # --- Validate first real fetch (Content-Type guard) ---
    # This detects the "wrong URL returns HTML" pitfall from RESEARCH.md.
    first_id_to_check = 1
    try:
        probe = session.get(BASE_URL + str(first_id_to_check), timeout=15)
        if probe.status_code == 200:
            ct = probe.headers.get("Content-Type", "")
            if "application/json" not in ct and "text/javascript" not in ct:
                raise RuntimeError(
                    f"FlavorDB2 endpoint returned non-JSON Content-Type: '{ct}'. "
                    "Likely HTML — check BASE_URL. "
                    f"URL used: {BASE_URL}{first_id_to_check}"
                )
    except requests_cache.exceptions.RequestException as exc:
        logger.warning("Probe request failed (%s) — continuing anyway.", exc)

    logger.info("Starting FlavorDB2 scrape: IDs 1–%d", MAX_ID)

    with logging_redirect_tqdm():
        for entity_id in tqdm(range(1, MAX_ID + 1), desc="FlavorDB2 entities"):
            try:
                resp = session.get(BASE_URL + str(entity_id), timeout=15)
            except Exception as exc:
                logger.error("Request error for entity %d: %s", entity_id, exc)
                failed += 1
                continue

            if resp.status_code == 404:
                consecutive_404s += 1
                failed += 1
                logger.debug("404 for entity %d (consecutive: %d)", entity_id, consecutive_404s)
                if consecutive_404s >= CONSECUTIVE_404_STOP:
                    logger.info(
                        "Stopping early — %d consecutive 404s at entity %d.",
                        CONSECUTIVE_404_STOP,
                        entity_id,
                    )
                    break
                continue

            if resp.status_code != 200:
                logger.warning(
                    "Unexpected status %d for entity %d — skipping.",
                    resp.status_code,
                    entity_id,
                )
                failed += 1
                continue

            # Reset streak on any non-404 response
            consecutive_404s = 0

            try:
                data = resp.json()
            except Exception as exc:
                logger.error("JSON decode error for entity %d: %s", entity_id, exc)
                failed += 1
                continue

            # --- Build ingredient row ---
            ingredient = {
                "ingredient_id": int(data.get("entity_id", entity_id)),
                "name": data.get("entity_alias_readable", ""),
                "category": data.get("category_readable", ""),
                "molecules_json": json.dumps(data.get("molecules", [])),
            }
            ingredients.append(ingredient)

            # --- Accumulate deduplicated molecules ---
            for mol in data.get("molecules", []):
                pid = mol.get("pubchem_id")
                if pid is not None and pid not in molecules:
                    molecules[pid] = {
                        "pubchem_id": pid,
                        "common_name": mol.get("common_name", ""),
                        "flavor_profile": mol.get("flavor_profile", ""),
                    }

            scraped += 1

    # --- Write outputs ---
    if ingredients:
        pd.DataFrame(ingredients).to_csv(OUT_INGREDIENTS, index=False)
        logger.info("Wrote %d rows to %s", len(ingredients), OUT_INGREDIENTS)
    else:
        logger.warning("No ingredients scraped — ingredients.csv NOT written.")

    if molecules:
        pd.DataFrame(list(molecules.values())).to_csv(OUT_MOLECULES, index=False)
        logger.info("Wrote %d rows to %s", len(molecules), OUT_MOLECULES)
    else:
        logger.warning("No molecules scraped — molecules.csv NOT written.")

    # --- Summary line (required by CONTEXT.md spec) ---
    logger.info("FlavorDB: %d scraped, %d failed (404)", scraped, failed)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape FlavorDB2 entities and write ingredients/molecules CSVs."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-scrape even if output files already exist.",
    )
    args = parser.parse_args()
    scrape_flavordb(force=args.force)


if __name__ == "__main__":
    main()
