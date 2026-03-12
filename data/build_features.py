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
MOLECULES_CSV = Path("data/raw/molecules.csv")
MOLECULES_PARQUET = Path("data/processed/molecules.parquet")
TANIMOTO_PARQUET = Path("data/processed/tanimoto_edges.parquet")

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


def encode_texture(category: str) -> list:
    """Return 5-dim one-hot texture vector for an ingredient category.

    Dims: [crispy, soft, creamy, chewy, crunchy].
    Falls back to 'soft' for unknown categories.
    """
    idx = TEXTURE_LOOKUP.get((category or "").lower().strip(), _TEXTURE_DEFAULT)
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


def build_cultural_context_vectors(recipes_df: pd.DataFrame) -> dict:
    """Build 10-dim cultural context count vectors per ingredient.

    Args:
        recipes_df: DataFrame with columns 'recipe_name' and 'ingredients'.
                    'ingredients' may be a comma-separated string or list.

    Returns:
        dict mapping ingredient_name -> list[int] of length 10.
        Counts how many recipes in each cuisine category feature the ingredient.
    """
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
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Build molecular features: RDKit descriptors, Morgan fingerprints, Tanimoto edges."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute even if output parquets already exist.",
    )
    args = parser.parse_args()
    build_molecule_df(force=args.force)


if __name__ == "__main__":
    main()
