"""Phase 2 feature engineering: RDKit descriptors, Morgan fingerprints,
Tanimoto similarity edges, multimodal ingredient features.

Run: conda run -n flavor-network python data/build_features.py
"""
import argparse
import json
import logging
import os
from pathlib import Path

import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors, AllChem, DataStructs
from rdkit.Chem import rdFingerprintGenerator
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("build_features")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # File handler — append to logs/pipeline.log
    fh = logging.FileHandler(LOG_DIR / "pipeline.log", mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logger.addHandler(fh)

    # Console handler — tqdm-compatible (writes to stderr)
    import sys
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(name)s %(levelname)s %(message)s"))
    logger.addHandler(ch)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_PATH = Path("data/raw/pubchem_cache.json")
INGREDIENTS_CSV = Path("data/raw/ingredients.csv")
MOLECULES_CSV = Path("data/raw/molecules.csv")
ALLRECIPES_CSV = Path("data/raw/recipes_allrecipes.csv")
RECIPES_CSV = Path("data/raw/recipes.csv")
MOLECULES_PARQUET = Path("data/processed/molecules.parquet")
TANIMOTO_PARQUET = Path("data/processed/tanimoto_edges.parquet")
INGREDIENTS_PARQUET = Path("data/processed/ingredients.parquet")
COOCCURRENCE_PARQUET = Path("data/processed/cooccurrence.parquet")

# Morgan fingerprint generator — created once at module load (radius=2, 1024 bits)
_MORGAN_GEN = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=1024)

# ---------------------------------------------------------------------------
# RDKit molecular feature computation
# ---------------------------------------------------------------------------


def compute_molecule_features(pubchem_id: int, smiles, common_name: str) -> dict:
    """Compute RDKit descriptors and Morgan fingerprint for one molecule.

    Returns a dict with pubchem_id, smiles, MW, logP, HBD, HBA,
    rotatable_bonds, TPSA, morgan_fp_bytes. All descriptor/fp columns are
    None when smiles is null/empty or when RDKit sanitization fails.

    morgan_fp_bytes stores the 1024-byte ASCII bit string produced by
    fp.ToBitString().encode().

    # Phase 3 decode: (np.frombuffer(fp_bytes, dtype=np.uint8) == ord('1')).astype(np.float32)
    """
    null_row = {
        "pubchem_id": pubchem_id,
        "smiles": smiles if smiles else None,
        "MW": None,
        "logP": None,
        "HBD": None,
        "HBA": None,
        "rotatable_bonds": None,
        "TPSA": None,
        "morgan_fp_bytes": None,
    }

    if not smiles:
        return null_row

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        logger.warning(
            "RDKit sanitization failure: pubchem_id=%d name=%s smiles=%s",
            pubchem_id,
            common_name,
            str(smiles)[:80],
        )
        return null_row

    # Use MorganGenerator (recommended API in RDKit 2025+); produces same
    # fingerprints as the legacy GetMorganFingerprintAsBitVect.
    fp = _MORGAN_GEN.GetFingerprint(mol)
    return {
        "pubchem_id": pubchem_id,
        "smiles": smiles,
        "MW": float(Descriptors.MolWt(mol)),
        "logP": float(Descriptors.MolLogP(mol)),
        "HBD": float(Descriptors.NumHDonors(mol)),
        "HBA": float(Descriptors.NumHAcceptors(mol)),
        "rotatable_bonds": float(Descriptors.NumRotatableBonds(mol)),
        "TPSA": float(Descriptors.TPSA(mol)),
        # 1024-byte ASCII bit string: b'010110...'
        "morgan_fp_bytes": fp.ToBitString().encode(),
    }


def compute_tanimoto_edges(
    fps_and_ids: list, threshold: float = 0.7
) -> list:
    """Compute all-pairs Tanimoto similarity; return edges above threshold.

    Args:
        fps_and_ids: list of (ExplicitBitVect, pubchem_id) tuples for
                     molecules with non-null fingerprints.
        threshold: similarity threshold (default 0.7).

    Returns:
        List of dicts: mol_a_pubchem_id, mol_b_pubchem_id, similarity.

    Performance: ~0.4s for 1788 molecules (no batching required).
    """
    fps = [fp for fp, _ in fps_and_ids]
    ids = [pid for _, pid in fps_and_ids]
    edges = []
    for i in range(len(fps)):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[i + 1:])
        for j, sim in enumerate(sims):
            if sim > threshold:
                edges.append(
                    {
                        "mol_a_pubchem_id": ids[i],
                        "mol_b_pubchem_id": ids[i + 1 + j],
                        "similarity": float(sim),
                    }
                )
    return edges


# ---------------------------------------------------------------------------
# Multimodal encoding stubs (texture, temperature, cultural context, flavor)
# Plans 02-04 will expand these into full implementations.
# ---------------------------------------------------------------------------

# 5-dim texture: crispy / soft / creamy / chewy / crunchy
TEXTURE_DIMS = ["crispy", "soft", "creamy", "chewy", "crunchy"]

TEXTURE_LOOKUP = {
    "herb": 1,          # soft
    "spice": 0,         # crispy/dry
    "vegetable": 1,     # soft
    "fruit": 1,         # soft
    "nut": 3,           # chewy
    "seed": 3,          # chewy
    "grain": 3,         # chewy
    "dairy": 2,         # creamy
    "meat": 1,          # soft
    "seafood": 1,       # soft
    "oil": 2,           # creamy
    "sweetener": 3,     # chewy
    "beverage": 1,      # soft
    "condiment": 2,     # creamy
    "legume": 1,        # soft
    "mushroom": 1,      # soft
    "alcohol": 1,       # soft
}
_TEXTURE_DEFAULT = 1  # soft


def encode_texture(category: str, moisture_content=None) -> list:
    """Return 5-dim one-hot texture vector for an ingredient category.

    Dims: [crispy, soft, creamy, chewy, crunchy].
    Falls back to 'soft' for unknown categories.

    Args:
        category: FlavorDB2 ingredient category string.
        moisture_content: optional float. If < 10.0 (very dry), overrides to
            'crispy'. If > 80.0 (very moist), overrides to 'soft'.
    """
    idx = TEXTURE_LOOKUP.get((category or "").lower().strip(), _TEXTURE_DEFAULT)

    # Moisture content overrides
    if moisture_content is not None:
        try:
            mc = float(moisture_content)
            if mc < 10.0:
                idx = 0  # crispy
            elif mc > 80.0:
                idx = 1  # soft
        except (ValueError, TypeError):
            pass  # ignore unparseable moisture values

    vec = [0] * 5
    vec[idx] = 1
    return vec


# 4-dim temperature: raw / cold / warm / hot
TEMPERATURE_DIMS = ["raw", "cold", "warm", "hot"]

TEMPERATURE_LOOKUP = {
    "herb": 0,          # raw
    "spice": 2,         # warm
    "vegetable": 0,     # raw
    "fruit": 1,         # cold
    "nut": 0,           # raw
    "seed": 0,          # raw
    "grain": 3,         # hot (cooked)
    "dairy": 1,         # cold
    "meat": 3,          # hot (cooked)
    "seafood": 3,       # hot (cooked)
    "oil": 2,           # warm
    "sweetener": 2,     # warm
    "beverage": 1,      # cold
    "condiment": 2,     # warm
    "legume": 3,        # hot (cooked)
    "mushroom": 3,      # hot (cooked)
    "alcohol": 1,       # cold
}
_TEMPERATURE_DEFAULT = 2  # warm


def encode_temperature(category: str) -> list:
    """Return 4-dim one-hot temperature affinity vector for an ingredient category.

    Dims: [raw, cold, warm, hot].
    Falls back to 'warm' for unknown categories.
    """
    idx = TEMPERATURE_LOOKUP.get((category or "").lower().strip(), _TEMPERATURE_DEFAULT)
    vec = [0] * 4
    vec[idx] = 1
    return vec


# 10-dim cultural context
ALLRECIPES_CATEGORIES = [
    "Italian",
    "Asian",
    "Mexican",
    "French",
    "American",
    "Indian",
    "Mediterranean",
    "Middle Eastern",
    "Japanese",
    "Thai",
]
CATEGORY_INDEX = {cat: i for i, cat in enumerate(ALLRECIPES_CATEGORIES)}

CATEGORY_KEYWORDS = {
    "Indian": [
        "indian", "tikka", "masala", "curry", "biryani", "naan",
        "paneer", "chai", "saag", "korma", "chapati", "mango lassi",
        "chana", "keema", "mulligatawny", "tandoori", "gujarati", "dal",
        "samosa", "palak", "aloo", "raita", "dosa", "idli",
    ],
    "Mexican": [
        "mexican", "tamale", "quesadilla", "fajita", "chiles",
        "empanada", "chipotle", "agua fresca", "flan", "barbacoa",
        "tacos", "enchilada", "taco", "burrito", "guacamole", "salsa",
        "tortilla", "mole",
    ],
    "Italian": [
        "italian", "rigatoni", "penne", "gelato", "tuscan", "piccata",
        "pepperoni", "bellini", "pasta", "risotto", "pizza", "lasagna",
        "gnocchi", "bruschetta", "tiramisu", "bolognese", "carbonara",
    ],
    "Asian": [
        "asian", "stir fry", "stir-fry", "fried rice", "spring roll",
        "dim sum", "wonton", "dumpling", "soy sauce", "hoisin",
        "sesame", "tofu", "bok choy", "bao",
    ],
    "French": [
        "french", "coq au vin", "ratatouille", "crepe", "croissant",
        "quiche", "baguette", "bisque", "bouillabaisse", "cassoulet",
        "nicoise", "provencal", "béarnaise", "beurre",
    ],
    "American": [
        "american", "bbq", "barbecue", "burger", "mac and cheese",
        "coleslaw", "cornbread", "biscuit gravy", "pot roast",
        "clam chowder", "thanksgiving", "meatloaf",
    ],
    "Mediterranean": [
        "mediterranean", "greek", "hummus", "falafel", "shawarma",
        "tzatziki", "pita", "tabbouleh", "moussaka", "baklava",
        "spanakopita", "dolma", "kebab", "souvlaki",
    ],
    "Middle Eastern": [
        "middle eastern", "persian", "lebanese", "turkish", "moroccan",
        "couscous", "tagine", "kofta", "harissa", "za'atar",
        "pomegranate", "tahini",
    ],
    "Japanese": [
        "japanese", "sushi", "ramen", "miso", "tempura", "udon",
        "soba", "teriyaki", "yakitori", "katsu", "onigiri", "dashi",
        "sake", "mirin", "wasabi",
    ],
    "Thai": [
        "thai", "pad thai", "green curry", "tom yum", "satay",
        "larb", "som tam", "massaman", "basil stir", "coconut milk curry",
    ],
}


def _classify_recipe_category(recipe_name: str) -> str | None:
    """Return cuisine category for a recipe name by keyword matching.

    Returns None if no keyword matches.
    """
    name_lower = recipe_name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return category
    return None


def build_cultural_context_vectors(recipes_source) -> dict:
    """Build 10-dim cultural context count vectors per ingredient.

    Args:
        recipes_source: either a Path to recipes_allrecipes.csv or a DataFrame
                        with columns 'recipe_name' and 'ingredients'.
                        'ingredients' may be a comma-separated string or list.

    Returns:
        dict mapping ingredient_name -> list[int] of length 10.
        Counts how many recipes in each cuisine category feature the ingredient.
    """
    if isinstance(recipes_source, (str, Path)):
        recipes_df = pd.read_csv(recipes_source)
        logger.info("Loaded %d AllRecipes recipes from %s", len(recipes_df), recipes_source)
    else:
        recipes_df = recipes_source
    ingredient_vectors: dict[str, list[int]] = {}
    unmatched = 0
    total = 0

    for _, row in recipes_df.iterrows():
        total += 1
        category = _classify_recipe_category(str(row.get("recipe_name", "")))
        if category is None:
            unmatched += 1
            continue

        cat_idx = CATEGORY_INDEX[category]
        ingredients_raw = row.get("ingredients", "")
        if isinstance(ingredients_raw, list):
            ingredients = [i.strip() for i in ingredients_raw if i.strip()]
        else:
            ingredients = [i.strip() for i in str(ingredients_raw).split(",") if i.strip()]

        for ingr in ingredients:
            if ingr not in ingredient_vectors:
                ingredient_vectors[ingr] = [0] * 10
            ingredient_vectors[ingr][cat_idx] += 1

    if total > 0 and unmatched / total > 0.1:
        logger.warning(
            "Cultural context: %d/%d recipes (%.0f%%) had no category match",
            unmatched,
            total,
            100 * unmatched / total,
        )
    else:
        logger.info(
            "Cultural context: %d/%d recipes unmatched (%.0f%%)",
            unmatched,
            total,
            100 * unmatched / total if total else 0,
        )

    return ingredient_vectors


# ---------------------------------------------------------------------------
# Flavor profile vocabulary and encoding
# ---------------------------------------------------------------------------


def build_flavor_vocab(mol_df: pd.DataFrame) -> dict:
    """Build sorted flavor profile vocabulary from molecules DataFrame.

    Args:
        mol_df: DataFrame with 'flavor_profile' column (@ -delimited tags).

    Returns:
        dict mapping token -> index (deterministic: sorted alphabetically).
    """
    all_tags: set[str] = set()
    for fp_str in mol_df["flavor_profile"].dropna():
        for tag in str(fp_str).split("@"):
            tag = tag.strip()
            if tag:
                all_tags.add(tag)
    vocab = sorted(all_tags)
    return {tag: i for i, tag in enumerate(vocab)}


def encode_flavor_profile(flavor_profile_str, vocab_index: dict) -> list:
    """Encode a flavor profile string as a multi-hot vector.

    Args:
        flavor_profile_str: @-delimited tag string, or None/empty.
        vocab_index: dict mapping token -> index (from build_flavor_vocab).

    Returns:
        list[int] of length len(vocab_index).
    """
    vec = [0] * len(vocab_index)
    if not flavor_profile_str:
        return vec
    for tag in str(flavor_profile_str).split("@"):
        tag = tag.strip()
        if tag in vocab_index:
            vec[vocab_index[tag]] = 1
    return vec


# ---------------------------------------------------------------------------
# Main pipeline function
# ---------------------------------------------------------------------------


def build_molecule_df(force: bool = False) -> pd.DataFrame:
    """Compute RDKit features for all molecules; write molecules.parquet and
    tanimoto_edges.parquet.

    Args:
        force: if True, recompute even if output files already exist.

    Returns:
        molecules DataFrame.
    """
    # Skip-if-exists
    if MOLECULES_PARQUET.exists() and TANIMOTO_PARQUET.exists() and not force:
        logger.info("[SKIP] molecules.parquet and tanimoto_edges.parquet already exist")
        return pd.read_parquet(MOLECULES_PARQUET)

    # Load molecules
    molecules_df = pd.read_csv(MOLECULES_CSV)
    logger.info("Loaded %d molecules from %s", len(molecules_df), MOLECULES_CSV)

    # Gate check: verify cache covers all pubchem_ids
    with open(CACHE_PATH) as f:
        cache = json.load(f)

    expected_keys = set(str(int(pid)) for pid in molecules_df["pubchem_id"].dropna())
    cache_keys = set(cache.keys())
    missing_keys = expected_keys - cache_keys
    if missing_keys:
        raise ValueError(
            f"pubchem_cache.json is missing {len(missing_keys)} entries. "
            f"Run fetch_smiles.py first. Missing sample: {list(missing_keys)[:10]}"
        )
    logger.info(
        "Gate check passed: %d pubchem_ids all present in cache (%d null entries)",
        len(expected_keys),
        sum(1 for v in cache.values() if v is None),
    )

    # Compute features for each molecule
    rows = []
    null_smiles_count = 0
    null_sanitization_count = 0

    for _, mol_row in tqdm(
        molecules_df.iterrows(),
        total=len(molecules_df),
        desc="RDKit features",
    ):
        pubchem_id = int(mol_row["pubchem_id"])
        common_name = str(mol_row.get("common_name", ""))
        smiles = cache.get(str(pubchem_id))

        if not smiles:
            null_smiles_count += 1

        row = compute_molecule_features(pubchem_id, smiles, common_name)
        rows.append(row)

        # Track sanitization failures (smiles provided but mol is None)
        if smiles and row["morgan_fp_bytes"] is None:
            null_sanitization_count += 1

    mol_features_df = pd.DataFrame(rows)

    # Build fps_and_ids from rows with non-null morgan_fp_bytes
    # Reconstruct ExplicitBitVect from stored bytes for Tanimoto computation
    # morgan_fp_bytes is ASCII bit string bytes (e.g., b'010110...')
    fps_and_ids = []
    for r in rows:
        if r["morgan_fp_bytes"] is not None:
            fp = DataStructs.CreateFromBitString(r["morgan_fp_bytes"].decode())
            fps_and_ids.append((fp, r["pubchem_id"]))

    logger.info("Computing Tanimoto edges for %d molecules with fingerprints...", len(fps_and_ids))
    edges = compute_tanimoto_edges(fps_and_ids)

    # Ensure output directory exists
    MOLECULES_PARQUET.parent.mkdir(parents=True, exist_ok=True)

    # Write parquet outputs
    mol_features_df.to_parquet(MOLECULES_PARQUET, index=False, engine="pyarrow")
    pd.DataFrame(edges).to_parquet(TANIMOTO_PARQUET, index=False, engine="pyarrow")

    logger.info(
        "Summary: total_molecules=%d, with_descriptors=%d, null_smiles=%d, "
        "null_sanitization=%d, tanimoto_edges=%d",
        len(rows),
        sum(1 for r in rows if r["morgan_fp_bytes"] is not None),
        null_smiles_count,
        null_sanitization_count,
        len(edges),
    )
    logger.info("Wrote %s (%d rows)", MOLECULES_PARQUET, len(mol_features_df))
    logger.info("Wrote %s (%d rows)", TANIMOTO_PARQUET, len(edges))

    return mol_features_df


# ---------------------------------------------------------------------------
# Integration: build all ingredient features and write parquets
# ---------------------------------------------------------------------------

# Texture/temperature column name lists for expansion
_TEXTURE_COLS = ["texture_crispy", "texture_soft", "texture_creamy", "texture_chewy", "texture_crunchy"]
_TEMPERATURE_COLS = ["temperature_raw", "temperature_cold", "temperature_warm", "temperature_hot"]
_CULTURAL_COLS = [f"cultural_context_{c.replace(' ', '')}" for c in ALLRECIPES_CATEGORIES]


def build_features(force: bool = False) -> None:
    """Build all multimodal ingredient features and write parquets.

    Outputs:
        data/processed/ingredients.parquet  — one row per ingredient
        data/processed/cooccurrence.parquet — ingredient pair counts from recipes.csv

    Molecules and Tanimoto parquets are written by build_molecule_df() which
    is called as a sub-step if those files are missing.

    Args:
        force: if True, recompute even if all output files already exist.
    """
    all_parquets = [INGREDIENTS_PARQUET, COOCCURRENCE_PARQUET, MOLECULES_PARQUET, TANIMOTO_PARQUET]
    if all(p.exists() for p in all_parquets) and not force:
        logger.info("[SKIP] build_features — all parquets present")
        return

    # Ensure processed directory exists
    INGREDIENTS_PARQUET.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Ensure molecules.parquet and tanimoto_edges.parquet exist
    if not MOLECULES_PARQUET.exists() or not TANIMOTO_PARQUET.exists() or force:
        build_molecule_df(force=force)

    # Step 2: Build flavor vocabulary from molecules.csv
    mol_df = pd.read_csv(MOLECULES_CSV)
    vocab_index = build_flavor_vocab(mol_df)
    vocab_size = len(vocab_index)
    logger.info("Flavor vocabulary: %d unique tags", vocab_size)

    # Build pubchem_id -> flavor_profile lookup for efficient molecule joining
    # molecules.csv may have multiple rows with the same pubchem_id after FooDB enrichment
    pid_to_flavor: dict[int, str] = {}
    for _, mrow in mol_df.iterrows():
        pid = int(mrow["pubchem_id"])
        fp_str = str(mrow.get("flavor_profile", "")) if pd.notna(mrow.get("flavor_profile")) else ""
        if pid not in pid_to_flavor:
            pid_to_flavor[pid] = fp_str
        elif fp_str:
            # Union: merge flavor profiles for the same pubchem_id
            existing = set(pid_to_flavor[pid].split("@")) - {""}
            new_tags = set(fp_str.split("@")) - {""}
            pid_to_flavor[pid] = "@".join(sorted(existing | new_tags))

    # Step 3: Build cultural context vectors from AllRecipes
    if ALLRECIPES_CSV.exists():
        cultural_vecs = build_cultural_context_vectors(ALLRECIPES_CSV)
    else:
        logger.warning("AllRecipes CSV not found at %s — cultural context will be all zeros", ALLRECIPES_CSV)
        cultural_vecs = {}

    # Step 4: Load ingredients.csv and build feature rows
    if not INGREDIENTS_CSV.exists():
        raise FileNotFoundError(
            f"ingredients.csv not found at {INGREDIENTS_CSV}. "
            "Run: conda run -n flavor-network python data/scrape_flavordb.py"
        )

    ing_df = pd.read_csv(INGREDIENTS_CSV)
    logger.info("Loaded %d ingredients from %s", len(ing_df), INGREDIENTS_CSV)

    rows = []
    for _, ing_row in tqdm(ing_df.iterrows(), total=len(ing_df), desc="Building ingredient features"):
        ingredient_id = int(ing_row["ingredient_id"])
        name = str(ing_row["name"])
        category = str(ing_row.get("category", "")).strip()

        # Moisture content from FooDB enrichment (may be in molecules.csv not ingredients.csv)
        moisture = ing_row.get("moisture_content", None)
        if pd.isna(moisture) if moisture is not None else True:
            moisture = None

        # Texture and temperature encoding
        texture_vec = encode_texture(category, moisture)
        temperature_vec = encode_temperature(category)

        # Cultural context: binarize count vector to 0/1
        raw_cultural = cultural_vecs.get(name.lower(), [0] * 10)
        cultural_vec = [min(1, v) for v in raw_cultural]

        # Flavor profile: union tags across all molecules for this ingredient
        molecules_json_str = ing_row.get("molecules_json", "[]")
        try:
            molecule_list = json.loads(molecules_json_str) if molecules_json_str else []
        except (json.JSONDecodeError, TypeError):
            molecule_list = []

        # Build unified flavor profile string from all molecules
        all_tags: set[str] = set()
        for mol_entry in molecule_list:
            pid = mol_entry.get("pubchem_id") if isinstance(mol_entry, dict) else None
            if pid is not None:
                fp_str = pid_to_flavor.get(int(pid), "")
                for tag in fp_str.split("@"):
                    tag = tag.strip()
                    if tag:
                        all_tags.add(tag)
            # Also check inline flavor_profile in the molecule entry
            if isinstance(mol_entry, dict):
                fp_inline = str(mol_entry.get("flavor_profile", ""))
                for tag in fp_inline.split("@"):
                    tag = tag.strip()
                    if tag:
                        all_tags.add(tag)

        combined_fp_str = "@".join(sorted(all_tags))
        flavor_vec = encode_flavor_profile(combined_fp_str, vocab_index)

        # Build row dict
        row = {"ingredient_id": ingredient_id, "name": name, "category": category}
        for col, val in zip(_TEXTURE_COLS, texture_vec):
            row[col] = val
        for col, val in zip(_TEMPERATURE_COLS, temperature_vec):
            row[col] = val
        for col, val in zip(_CULTURAL_COLS, cultural_vec):
            row[col] = val
        for i, val in enumerate(flavor_vec):
            row[f"flavor_profile_{i}"] = val

        rows.append(row)

    ingredients_out_df = pd.DataFrame(rows)
    ingredients_out_df.to_parquet(INGREDIENTS_PARQUET, index=False, engine="pyarrow")
    logger.info("Wrote %s (%d rows, %d columns)", INGREDIENTS_PARQUET, len(ingredients_out_df), len(ingredients_out_df.columns))

    # Step 5: Carry cooccurrence from recipes.csv
    if RECIPES_CSV.exists():
        logger.info("Loading recipes.csv for cooccurrence (may be large)...")
        chunks = []
        for chunk in pd.read_csv(RECIPES_CSV, chunksize=100_000):
            chunks.append(chunk)
        cooccurrence_df = pd.concat(chunks, ignore_index=True)
        cooccurrence_df.to_parquet(COOCCURRENCE_PARQUET, index=False, engine="pyarrow")
        logger.info("Wrote %s (%d rows)", COOCCURRENCE_PARQUET, len(cooccurrence_df))
    else:
        logger.warning(
            "recipes.csv not found at %s — cooccurrence.parquet NOT written. "
            "Run: conda run -n flavor-network python run_pipeline.py --skip-scrape --skip-foodb --skip-smiles",
            RECIPES_CSV,
        )

    # Log summary
    cultural_matched = sum(1 for v in cultural_vecs.values() if any(x > 0 for x in v))
    logger.info(
        "build_features summary: ingredients=%d, flavor_vocab_size=%d, "
        "cultural_context_matched=%d, cooccurrence_written=%s",
        len(rows),
        vocab_size,
        cultural_matched,
        COOCCURRENCE_PARQUET.exists(),
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Build molecular features: RDKit descriptors, Morgan fingerprints, Tanimoto edges, ingredient features."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute even if output parquets already exist.",
    )
    args = parser.parse_args()
    build_features(force=args.force)


if __name__ == "__main__":
    main()
