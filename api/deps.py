"""Shared FastAPI dependencies — loaded once at container startup."""
from __future__ import annotations
import pickle
import pandas as pd
from pathlib import Path
from functools import lru_cache

DATA_DIR = Path("/data")  # Modal Volume mount point


@lru_cache(maxsize=1)
def load_all_data() -> dict:
    """Load all runtime artifacts into memory. Called once at startup."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    with open(DATA_DIR / "ingredient_embeddings.pkl", "rb") as f:
        embeddings = pickle.load(f)

    # Build ID -> lowercase name mapping from ingredients.parquet
    ingredients_df = pd.read_parquet(DATA_DIR / "ingredients.parquet")[["ingredient_id", "name"]]
    id_to_name: dict[int, str] = {
        int(row["ingredient_id"]): str(row["name"]).lower()
        for _, row in ingredients_df.iterrows()
    }

    scored_pairs = pd.read_pickle(DATA_DIR / "scored_pairs.pkl")
    if "label" in scored_pairs.columns:
        scored_pairs["label"] = scored_pairs["label"].astype(str)
    # Replace numeric IDs with string names
    scored_pairs["ingredient_a"] = scored_pairs["ingredient_a"].map(id_to_name)
    scored_pairs["ingredient_b"] = scored_pairs["ingredient_b"].map(id_to_name)
    scored_pairs = scored_pairs.dropna(subset=["ingredient_a", "ingredient_b"])

    # Build lookup: ingredient_name -> set of pubchem_ids (as strings)
    molecules_df = pd.read_parquet(DATA_DIR / "ingredient_molecule.parquet")
    mol_lookup: dict[str, set[str]] = {}
    for _, row in molecules_df.iterrows():
        ing_id = int(row["ingredient_id"])
        name = id_to_name.get(ing_id, "")
        if name:
            mol = str(int(row["pubchem_id"]))
            mol_lookup.setdefault(name, set()).add(mol)

    return {
        "embeddings": embeddings,
        "scored_pairs": scored_pairs,
        "mol_lookup": mol_lookup,
    }


def get_shared_molecules(a: str, b: str, mol_lookup: dict, limit: int = 5) -> list[str]:
    """Return up to `limit` molecule names shared between ingredient a and b."""
    mols_a = mol_lookup.get(a.lower(), set())
    mols_b = mol_lookup.get(b.lower(), set())
    return sorted(mols_a & mols_b)[:limit]
