"""
FooDB fuzzy join — enriches molecules.csv with macronutrient data from FooDB.

Reads:
    data/raw/ingredients.csv   — FlavorDB2 ingredient names (lookup list)
    data/raw/molecules.csv     — FlavorDB2 deduplicated molecules
    data/raw/foodb/Food.csv    — FooDB food entities (requires manual download)
    data/raw/foodb/Compound.csv — FooDB compound data (requires manual download)

Writes:
    data/raw/molecules.csv     — enriched with FooDB columns:
                                 foodb_matched (bool), foodb_food_id (int or NaN),
                                 macronutrients_json (JSON string), moisture_content (float)

FooDB download:
    1. Visit https://foodb.ca/downloads
    2. Download the full database CSV (~952 MB tar.gz), CC BY-NC 4.0
    3. Extract to data/raw/foodb/

Run standalone:
    python data/join_foodb.py
    python data/join_foodb.py --force   # re-run even if foodb_matched column exists
"""

import argparse
import json
import logging
import os

import pandas as pd
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from rapidfuzz import process, fuzz

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
FOODB_DIR = "data/raw/foodb"
FOODB_JSON_DIR = "data/foodb_2020_04_07_json"
INGREDIENTS_CSV = "data/raw/ingredients.csv"
MOLECULES_CSV = "data/raw/molecules.csv"
FUZZY_THRESHOLD = 85


# ---------------------------------------------------------------------------
# Helper: load a FooDB NDJSON file into a DataFrame
# ---------------------------------------------------------------------------

def load_ndjson(path: str) -> "pd.DataFrame":
    """Load a newline-delimited JSON file (one object per line) into a DataFrame."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Helper: locate FooDB data (CSV or JSON)
# ---------------------------------------------------------------------------

def find_foodb_files() -> tuple[str, str, str]:
    """Locate Food and Compound data files (CSV or NDJSON).

    Returns
    -------
    (food_path, compound_path, fmt) where fmt is "csv" or "json"

    Raises
    ------
    FileNotFoundError if neither CSV nor JSON source is available.
    """
    # Prefer JSON directory if present
    if os.path.isdir(FOODB_JSON_DIR):
        food_path = os.path.join(FOODB_JSON_DIR, "Food.json")
        compound_path = os.path.join(FOODB_JSON_DIR, "Compound.json")
        if os.path.exists(food_path) and os.path.exists(compound_path):
            logger.info("Using FooDB JSON directory: %s", FOODB_JSON_DIR)
            return food_path, compound_path, "json"

    # Fall back to CSV directory
    if os.path.isdir(FOODB_DIR):
        food_candidates = ["Food.csv", "foods.csv", "food.csv"]
        compound_candidates = ["Compound.csv", "compounds.csv", "compound.csv"]

        food_path = next(
            (os.path.join(FOODB_DIR, n) for n in food_candidates if os.path.exists(os.path.join(FOODB_DIR, n))),
            None,
        )
        compound_path = next(
            (os.path.join(FOODB_DIR, n) for n in compound_candidates if os.path.exists(os.path.join(FOODB_DIR, n))),
            None,
        )
        if food_path and compound_path:
            logger.info("Using FooDB CSV directory: %s", FOODB_DIR)
            return food_path, compound_path, "csv"

    raise FileNotFoundError(
        f"FooDB data not found. Expected either:\n"
        f"  JSON: {FOODB_JSON_DIR}/Food.json + Compound.json\n"
        f"  CSV:  {FOODB_DIR}/Food.csv + Compound.csv\n"
        "Download from https://foodb.ca/downloads (CC BY-NC 4.0)"
    )


# ---------------------------------------------------------------------------
# Core join function
# ---------------------------------------------------------------------------

def join_foodb(force: bool = False) -> None:
    """Enrich molecules.csv with FooDB macronutrient data via fuzzy name matching.

    Parameters
    ----------
    force:
        If True, re-run even if molecules.csv already has a 'foodb_matched' column.
    """
    # --- Idempotence check ---
    if not force and os.path.exists(MOLECULES_CSV):
        try:
            existing = pd.read_csv(MOLECULES_CSV)
            if "foodb_matched" in existing.columns:
                logger.info(
                    "[SKIP] molecules.csv already has 'foodb_matched' column. "
                    "Use --force to re-run."
                )
                return
        except Exception as exc:
            logger.warning("Could not read existing molecules.csv (%s) — continuing.", exc)

    # --- Check FooDB data exists; print instructions and return if not ---
    if not os.path.isdir(FOODB_DIR) and not os.path.isdir(FOODB_JSON_DIR):
        logger.warning(
            "FooDB data not found. Expected either:\n"
            "  JSON: %s/Food.json\n"
            "  CSV:  %s/Food.csv\n"
            "Molecules.csv will not be enriched until FooDB data is available.",
            FOODB_JSON_DIR,
            FOODB_DIR,
        )
        return

    # --- Load ingredients.csv (FlavorDB2 ingredient names) ---
    if not os.path.exists(INGREDIENTS_CSV):
        logger.error("ingredients.csv not found at %s. Run Plan 01-02 first.", INGREDIENTS_CSV)
        return

    ingredients_df = pd.read_csv(INGREDIENTS_CSV)
    # Ingredient names are in the 'name' column
    name_col = "name" if "name" in ingredients_df.columns else ingredients_df.columns[0]
    flavordb_names = ingredients_df[name_col].dropna().tolist()
    total_ingredients = len(flavordb_names)
    logger.info("Loaded %d FlavorDB2 ingredient names from %s", total_ingredients, INGREDIENTS_CSV)

    # --- Load FooDB files (CSV or JSON) ---
    try:
        food_path, compound_path, fmt = find_foodb_files()
    except FileNotFoundError as exc:
        logger.warning("%s\nSkipping FooDB join.", exc)
        return

    logger.info("Loading FooDB Food file: %s", food_path)
    foodb_foods = load_ndjson(food_path) if fmt == "json" else pd.read_csv(food_path, low_memory=False)
    logger.info("FooDB Food columns: %s", foodb_foods.columns.tolist())
    logger.info("FooDB Food shape: %s", foodb_foods.shape)

    logger.info("Loading FooDB Compound file: %s", compound_path)
    foodb_compounds = load_ndjson(compound_path) if fmt == "json" else pd.read_csv(compound_path, low_memory=False)
    logger.info("FooDB Compound columns: %s", foodb_compounds.columns.tolist())
    logger.info("FooDB Compound shape: %s", foodb_compounds.shape)

    # Detect the food name column (common names across FooDB releases)
    food_name_col = None
    for candidate in ["name", "Name", "food_name", "Food"]:
        if candidate in foodb_foods.columns:
            food_name_col = candidate
            break
    if food_name_col is None:
        logger.error(
            "Cannot find food name column in FooDB Food CSV. "
            "Columns found: %s",
            foodb_foods.columns.tolist(),
        )
        return

    # Detect food ID column
    food_id_col = None
    for candidate in ["id", "ID", "food_id", "foodb_id"]:
        if candidate in foodb_foods.columns:
            food_id_col = candidate
            break

    logger.info("Using food name column: '%s', food ID column: '%s'", food_name_col, food_id_col)

    # --- Fuzzy match: FooDB food names → FlavorDB2 ingredient names ---
    logger.info(
        "Fuzzy matching %d FooDB foods against %d FlavorDB2 ingredients (threshold=%d)...",
        len(foodb_foods),
        total_ingredients,
        FUZZY_THRESHOLD,
    )

    # matches: maps FlavorDB2 ingredient name → {foodb_food_id, score}
    matches: dict[str, dict] = {}

    with logging_redirect_tqdm():
        for _, row in tqdm(foodb_foods.iterrows(), total=len(foodb_foods), desc="FooDB fuzzy match"):
            foodb_name = row.get(food_name_col, "")
            if not foodb_name or not isinstance(foodb_name, str):
                continue

            result = process.extractOne(
                foodb_name,
                flavordb_names,
                scorer=fuzz.token_sort_ratio,
            )
            if result is None:
                continue

            matched_name, score, _ = result
            if score >= FUZZY_THRESHOLD:
                # Keep highest-scoring match if multiple FooDB foods match same ingredient
                if matched_name not in matches or score > matches[matched_name]["score"]:
                    food_id = int(row[food_id_col]) if food_id_col and pd.notna(row.get(food_id_col)) else None
                    matches[matched_name] = {
                        "foodb_food_id": food_id,
                        "score": score,
                    }

    matched_count = len(matches)
    logger.info(
        "FooDB join: %d/%d matched (%d%%)",
        matched_count,
        total_ingredients,
        int(matched_count / total_ingredients * 100) if total_ingredients > 0 else 0,
    )

    if matched_count < 300:
        logger.warning(
            "WARNING: FooDB join matched only %d/%d ingredients (threshold=%d). "
            "Expected >= 300.",
            matched_count,
            total_ingredients,
            FUZZY_THRESHOLD,
        )

    # --- Build macronutrient lookup from FooDB compounds ---
    # FooDB Compound table may contain nutrient data; detect columns gracefully
    nutrient_cols = {}
    for nutrient, candidates in {
        "carbohydrates": ["carbohydrates", "carbohydrate", "total_carbohydrate"],
        "protein": ["protein", "proteins", "total_protein"],
        "fat": ["fat", "fats", "total_fat", "lipids"],
        "fiber": ["fiber", "dietary_fiber", "total_fiber"],
    }.items():
        for candidate in candidates:
            if candidate in foodb_foods.columns:
                nutrient_cols[nutrient] = candidate
                break

    moisture_col = None
    for candidate in ["moisture_content", "moisture", "water_content", "water"]:
        if candidate in foodb_foods.columns:
            moisture_col = candidate
            break

    logger.info("Nutrient columns found: %s", nutrient_cols)
    logger.info("Moisture column found: %s", moisture_col)

    # Build food_id → nutrient/moisture map
    food_nutrients: dict[int, dict] = {}
    if food_id_col:
        for _, row in foodb_foods.iterrows():
            food_id = row.get(food_id_col)
            if pd.isna(food_id):
                continue
            food_id = int(food_id)
            nutrients = {}
            for nutrient, col in nutrient_cols.items():
                val = row.get(col)
                nutrients[nutrient] = float(val) if pd.notna(val) else None
            moisture = float(row[moisture_col]) if moisture_col and pd.notna(row.get(moisture_col)) else None
            food_nutrients[food_id] = {
                "macronutrients": nutrients,
                "moisture_content": moisture,
            }

    # --- Build pubchem_id → foodb_food_id lookup via ingredients.csv ---
    # ingredients.csv has a molecules_json column with pubchem_ids for each ingredient.
    # For each matched FlavorDB2 ingredient, mark its molecules as foodb_matched=True.
    if not os.path.exists(INGREDIENTS_CSV):
        logger.error("ingredients.csv not found at %s. Run Plan 01-02 first.", INGREDIENTS_CSV)
        return

    ingredients_df = pd.read_csv(INGREDIENTS_CSV)
    pubchem_to_foodb: dict[int, int | None] = {}

    for _, ing_row in ingredients_df.iterrows():
        ing_name = ing_row.get("name", "")
        if ing_name not in matches:
            continue
        food_id = matches[ing_name]["foodb_food_id"]
        mols_raw = ing_row.get("molecules_json", "")
        if not mols_raw or not isinstance(mols_raw, str):
            continue
        try:
            mols = json.loads(mols_raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for mol in mols:
            pid = mol.get("pubchem_id")
            if pid is not None:
                pubchem_to_foodb[int(pid)] = food_id

    logger.info("pubchem_ids with FooDB match: %d", len(pubchem_to_foodb))

    # --- Enrich molecules.csv ---
    if not os.path.exists(MOLECULES_CSV):
        logger.error("molecules.csv not found at %s. Run Plan 01-02 first.", MOLECULES_CSV)
        return

    molecules_df = pd.read_csv(MOLECULES_CSV)
    logger.info("Loaded molecules.csv: %s rows", len(molecules_df))

    foodb_matched_list = []
    foodb_food_id_list = []
    macronutrients_json_list = []
    moisture_content_list = []

    for _, mol_row in molecules_df.iterrows():
        pid = mol_row.get("pubchem_id")
        try:
            pid = int(pid) if pd.notna(pid) else None
        except (ValueError, TypeError):
            pid = None

        if pid is not None and pid in pubchem_to_foodb:
            food_id = pubchem_to_foodb[pid]
            nutrient_data = food_nutrients.get(food_id, {}) if food_id is not None else {}
            foodb_matched_list.append(True)
            foodb_food_id_list.append(food_id)
            macronutrients_json_list.append(json.dumps(nutrient_data.get("macronutrients", {})))
            moisture_content_list.append(nutrient_data.get("moisture_content"))
        else:
            foodb_matched_list.append(False)
            foodb_food_id_list.append(None)
            macronutrients_json_list.append(None)
            moisture_content_list.append(None)

    molecules_df["foodb_matched"] = foodb_matched_list
    molecules_df["foodb_food_id"] = foodb_food_id_list
    molecules_df["macronutrients_json"] = macronutrients_json_list
    molecules_df["moisture_content"] = moisture_content_list

    molecules_df.to_csv(MOLECULES_CSV, index=False)
    logger.info(
        "Wrote enriched molecules.csv: %d rows, columns: %s",
        len(molecules_df),
        molecules_df.columns.tolist(),
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich molecules.csv with FooDB macronutrient data via fuzzy name matching."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if molecules.csv already has foodb_matched column.",
    )
    args = parser.parse_args()
    join_foodb(force=args.force)


if __name__ == "__main__":
    main()
