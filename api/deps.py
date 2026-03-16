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

    with open(DATA_DIR / "scored_pairs.pkl", "rb") as f:
        scored_pairs = pickle.load(f)

    molecules_df = pd.read_parquet(DATA_DIR / "ingredient_molecule.parquet")
    # Build lookup: ingredient_name -> set of molecule names
    mol_lookup: dict[str, set[str]] = {}
    for _, row in molecules_df.iterrows():
        name = str(row.get("ingredient", row.get("name", ""))).lower()
        mol = str(row.get("molecule", row.get("molecule_name", "")))
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
