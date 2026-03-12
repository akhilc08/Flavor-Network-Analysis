"""
Pipeline Orchestrator — runs all data ingestion and feature engineering stages in order.

Stages:
    1. FlavorDB2 scraper  → data/raw/ingredients.csv + data/raw/molecules.csv
    2. Recipe co-occurrence → data/raw/recipes.csv
    3. FooDB fuzzy join   → enriches data/raw/molecules.csv
    4. SMILES fetch       → data/raw/pubchem_cache.json

Usage:
    python run_pipeline.py                          # run all stages
    python run_pipeline.py --skip-scrape            # skip FlavorDB2 stage
    python run_pipeline.py --skip-foodb             # skip FooDB join stage
    python run_pipeline.py --skip-recipes           # skip recipe co-occurrence stage
    python run_pipeline.py --skip-smiles            # skip SMILES fetch stage
    python run_pipeline.py --force                  # re-run all stages even if outputs exist
"""

import argparse
import logging
import os
import sys
import time
import traceback

import pandas as pd

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
# Stage imports
# ---------------------------------------------------------------------------
# Import the callable functions from each data module.
# These are imported at module level but errors are caught per-stage at runtime.

def _import_stages():
    """Import stage functions; return dict or raise on import failure."""
    try:
        from data.scrape_flavordb import scrape_flavordb
    except ImportError as exc:
        logger.error("Cannot import scrape_flavordb: %s", exc)
        scrape_flavordb = None

    try:
        from data.scrape_recipes import main as scrape_recipes
    except ImportError as exc:
        logger.error("Cannot import scrape_recipes: %s", exc)
        scrape_recipes = None

    try:
        from data.join_foodb import join_foodb
    except ImportError as exc:
        logger.error("Cannot import join_foodb: %s", exc)
        join_foodb = None

    try:
        from data.fetch_smiles import fetch_smiles
    except ImportError as exc:
        logger.error("Cannot import fetch_smiles: %s", exc)
        fetch_smiles = None

    return {
        "scrape_flavordb": scrape_flavordb,
        "scrape_recipes": scrape_recipes,
        "join_foodb": join_foodb,
        "fetch_smiles": fetch_smiles,
    }


# ---------------------------------------------------------------------------
# Summary table helper
# ---------------------------------------------------------------------------

def _print_summary() -> None:
    """Read the output files and print the pipeline summary table."""
    ingredients_path = "data/raw/ingredients.csv"
    molecules_path = "data/raw/molecules.csv"
    recipes_path = "data/raw/recipes.csv"
    smiles_cache_path = "data/raw/pubchem_cache.json"

    # Gather stats for each file
    def _read_stat(path: str) -> str | int:
        if not os.path.exists(path):
            return "NOT YET CREATED"
        try:
            df = pd.read_csv(path)
            return len(df)
        except Exception as exc:
            return f"ERROR ({exc})"

    n_ingredients = _read_stat(ingredients_path)
    n_molecules = _read_stat(molecules_path)
    n_recipes = _read_stat(recipes_path)

    # FooDB match stats (requires foodb_matched column in molecules.csv)
    foodb_info = "N/A"
    if isinstance(n_ingredients, int) and os.path.exists(molecules_path):
        try:
            mol_df = pd.read_csv(molecules_path)
            if "foodb_matched" in mol_df.columns:
                matched = mol_df["foodb_matched"].sum()
                total = n_ingredients if isinstance(n_ingredients, int) else len(mol_df)
                pct = int(matched / total * 100) if total > 0 else 0
                foodb_info = f"{matched}/{total} matched ({pct}%)"
        except Exception:
            foodb_info = "N/A"

    # SMILES cache stats
    smiles_info = "NOT YET CREATED"
    if os.path.exists(smiles_cache_path):
        try:
            import json
            with open(smiles_cache_path) as f:
                cache = json.load(f)
            n_total = len(cache)
            n_with = sum(1 for v in cache.values() if v is not None)
            smiles_info = f"{n_with}/{n_total} with SMILES ({int(n_with/n_total*100) if n_total else 0}%)"
        except Exception:
            smiles_info = "ERROR reading cache"

    # Format rows
    def _fmt_row(count) -> str:
        if isinstance(count, int):
            return f"{count:,} rows"
        return str(count)

    n_ingredients_str = f"{n_ingredients:,}" if isinstance(n_ingredients, int) else str(n_ingredients)
    n_molecules_str = f"{n_molecules:,}" if isinstance(n_molecules, int) else str(n_molecules)
    n_recipes_str = f"{n_recipes:,}" if isinstance(n_recipes, int) else str(n_recipes)

    print()
    print("=== Pipeline Summary ===")
    print(f"FlavorDB:    {n_ingredients_str} ingredients, {n_molecules_str} molecules")
    print(f"FooDB:       {foodb_info}")
    print(f"Recipes:     {n_recipes_str} co-occurrence pairs")
    print(f"SMILES:      {smiles_info}")
    print()
    print(f"Output:      {ingredients_path:<38} [{_fmt_row(n_ingredients)}]")
    print(f"             {molecules_path:<38} [{_fmt_row(n_molecules)}]")
    print(f"             {recipes_path:<38} [{_fmt_row(n_recipes)}]")
    print(f"             {smiles_cache_path:<38} [smiles_fetch]")
    print("========================")
    print()


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main(args: argparse.Namespace) -> None:
    """Run all pipeline stages in order.

    Each stage is isolated: exceptions are logged and execution continues
    to the next stage.
    """
    pipeline_start = time.time()
    logger.info("=== Phase 1 Pipeline starting ===")

    stages = _import_stages()

    # --- Stage 1: FlavorDB2 scraper ---
    if args.skip_scrape:
        logger.info("[SKIP] FlavorDB2 scrape (--skip-scrape)")
    else:
        scrape_fn = stages.get("scrape_flavordb")
        if scrape_fn is None:
            logger.error("[SKIP] FlavorDB2 scrape — import failed")
        else:
            logger.info("--- Stage 1: FlavorDB2 scrape ---")
            try:
                scrape_fn(force=args.force)
            except Exception:
                logger.error(
                    "Stage 1 (FlavorDB2 scrape) failed:\n%s",
                    traceback.format_exc(),
                )

    # --- Stage 2: Recipe co-occurrence ---
    if args.skip_recipes:
        logger.info("[SKIP] Recipe co-occurrence (--skip-recipes)")
    else:
        scrape_recipes_fn = stages.get("scrape_recipes")
        if scrape_recipes_fn is None:
            logger.error("[SKIP] Recipe co-occurrence — import failed")
        else:
            logger.info("--- Stage 2: Recipe co-occurrence ---")
            try:
                scrape_recipes_fn(force=args.force)
            except Exception:
                logger.error(
                    "Stage 2 (Recipe co-occurrence) failed:\n%s",
                    traceback.format_exc(),
                )

    # --- Stage 3: FooDB fuzzy join ---
    if args.skip_foodb:
        logger.info("[SKIP] FooDB join (--skip-foodb)")
    else:
        join_fn = stages.get("join_foodb")
        if join_fn is None:
            logger.error("[SKIP] FooDB join — import failed")
        else:
            logger.info("--- Stage 3: FooDB fuzzy join ---")
            try:
                join_fn(force=args.force)
            except Exception:
                logger.error(
                    "Stage 3 (FooDB join) failed:\n%s",
                    traceback.format_exc(),
                )

    # --- Phase 2: SMILES fetch ---
    if args.skip_smiles:
        logger.info("[SKIP] fetch_smiles (--skip-smiles)")
    else:
        fetch_smiles_fn = stages.get("fetch_smiles")
        if fetch_smiles_fn is None:
            logger.error("[SKIP] fetch_smiles — import failed")
        else:
            logger.info("--- Phase 2: SMILES fetch ---")
            try:
                fetch_smiles_fn(force=args.force)
            except Exception:
                logger.error(
                    "Phase 2 (fetch_smiles) failed:\n%s",
                    traceback.format_exc(),
                )

    elapsed = time.time() - pipeline_start
    logger.info("=== Pipeline complete (%.1f s) ===", elapsed)

    # --- Final summary table ---
    _print_summary()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline orchestrator — runs all data ingestion and feature engineering stages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Stages (in order):
  1. FlavorDB2 scraper   → data/raw/ingredients.csv + data/raw/molecules.csv
  2. Recipe co-occurrence → data/raw/recipes.csv
  3. FooDB fuzzy join    → enriches data/raw/molecules.csv
  4. SMILES fetch        → data/raw/pubchem_cache.json

Examples:
  python run_pipeline.py                   # run all stages
  python run_pipeline.py --skip-scrape     # skip FlavorDB2 (already scraped)
  python run_pipeline.py --skip-foodb      # skip FooDB join (no FooDB data)
  python run_pipeline.py --skip-smiles     # skip SMILES fetch (cache already complete)
  python run_pipeline.py --force           # re-run all stages from scratch
""",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip FlavorDB2 scraping stage.",
    )
    parser.add_argument(
        "--skip-foodb",
        action="store_true",
        help="Skip FooDB CSV join stage.",
    )
    parser.add_argument(
        "--skip-recipes",
        action="store_true",
        help="Skip recipe co-occurrence stage.",
    )
    parser.add_argument(
        "--skip-smiles",
        action="store_true",
        help="Skip SMILES fetch stage (pubchem_cache.json already complete).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run all stages even if outputs already exist.",
    )

    _args = parser.parse_args()
    main(_args)
