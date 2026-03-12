"""
Phase 3 Graph Construction — builds graph/hetero_data.pt from data/processed/ parquets.

Usage:
    python graph/build_graph.py           # build graph; skip if output already exists
    python graph/build_graph.py --force   # rebuild even if output exists

Output:
    graph/hetero_data.pt   — torch dict with train/val/test HeteroData + index maps
    graph/index_maps.json  — human-readable sidecar for debugging
"""

import argparse
import json
import logging
import os
import sys
import time

import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

from rdkit import DataStructs
from rdkit.DataStructs import ConvertToNumpyArray
from sklearn.preprocessing import StandardScaler
from torch_geometric.data import HeteroData
from torch_geometric.transforms import RandomLinkSplit

# ---------------------------------------------------------------------------
# Logging setup (module-level)
# ---------------------------------------------------------------------------

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_PT = "graph/hetero_data.pt"
OUTPUT_JSON = "graph/index_maps.json"

# ---------------------------------------------------------------------------
# Morgan fingerprint helpers
# ---------------------------------------------------------------------------


def _probe_fp_format(fp_bytes) -> str:
    """Probe the serialization format of morgan_fp_bytes.

    Takes the first row's morgan_fp_bytes value, logs its type and length,
    and returns a format string used by _deserialize_fp.
    """
    logger.info(
        "# FP probe: type=%s len=%d first_bytes=%s",
        type(fp_bytes).__name__,
        len(fp_bytes) if fp_bytes is not None else -1,
        repr(fp_bytes[:8]) if fp_bytes is not None else "None",
    )

    if fp_bytes is None:
        logger.warning("FP probe: fp_bytes is None, defaulting to numpy_bytes")
        return "unknown"

    # Check if it's a 1024-byte ASCII bit string (b'0' and b'1' chars)
    if isinstance(fp_bytes, bytes) and len(fp_bytes) == 1024:
        unique_bytes = set(fp_bytes)
        ascii_0 = ord("0")
        ascii_1 = ord("1")
        if unique_bytes.issubset({ascii_0, ascii_1}):
            logger.info("# FP probe confirmed: 1024-byte ASCII bit string")
            return "ascii_bits"

    # Try ExplicitBitVect deserialization
    try:
        bv = DataStructs.ExplicitBitVect(fp_bytes)
        logger.info(
            "# FP probe confirmed: explicit_bitvect (nBits=%d)", bv.GetNumBits()
        )
        return "explicit_bitvect"
    except Exception:
        pass

    # Try base64
    try:
        import base64

        decoded = base64.b64decode(fp_bytes)
        DataStructs.ExplicitBitVect(decoded)
        logger.info("# FP probe confirmed: base64-encoded explicit_bitvect")
        return "base64"
    except Exception:
        pass

    logger.warning("# FP probe: could not determine format, using numpy_bytes fallback")
    return "numpy_bytes"


def _deserialize_fp(fp_bytes, fmt: str) -> "np.ndarray | None":
    """Deserialize morgan_fp_bytes to numpy array of shape [1024] float32."""
    if fp_bytes is None:
        return None
    try:
        if fmt == "ascii_bits":
            # 1024-byte ASCII string: b'0101...' — compare each byte to ord('1')
            arr = (np.frombuffer(fp_bytes, dtype=np.uint8) == ord("1")).astype(
                np.float32
            )
            return arr

        elif fmt == "explicit_bitvect":
            bv = DataStructs.ExplicitBitVect(fp_bytes)
            arr = np.zeros(1024, dtype=np.float32)
            ConvertToNumpyArray(bv, arr)
            return arr

        elif fmt == "base64":
            import base64

            decoded = base64.b64decode(fp_bytes)
            bv = DataStructs.ExplicitBitVect(decoded)
            arr = np.zeros(1024, dtype=np.float32)
            ConvertToNumpyArray(bv, arr)
            return arr

        elif fmt == "numpy_bytes":
            return np.frombuffer(fp_bytes, dtype=np.uint8).astype(np.float32)

        else:
            # Unknown format — attempt ascii_bits as most likely given codebase decisions
            arr = (np.frombuffer(fp_bytes, dtype=np.uint8) == ord("1")).astype(
                np.float32
            )
            return arr

    except Exception as e:
        logger.warning("Failed to deserialize fp for one molecule: %s", e)
        return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_parquets() -> "tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]":
    """Load all three processed parquet files.

    Returns:
        (ing_df, mol_df, cooc_df)

    Raises:
        FileNotFoundError: if any parquet is missing.
    """
    paths = {
        "ingredients": "data/processed/ingredients.parquet",
        "molecules": "data/processed/molecules.parquet",
        "cooccurrence": "data/processed/cooccurrence.parquet",
    }
    dfs = {}
    for name, path in paths.items():
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Missing {path} — run Phase 2 feature engineering first"
            )
        dfs[name] = pd.read_parquet(path)
        logger.info("Loaded %s: %d rows", path, len(dfs[name]))

    return dfs["ingredients"], dfs["molecules"], dfs["cooccurrence"]


# ---------------------------------------------------------------------------
# Index dictionaries
# ---------------------------------------------------------------------------


def _build_index_dicts(
    ing_df: pd.DataFrame, mol_df: pd.DataFrame
) -> "tuple[dict, dict, dict]":
    """Build three index dictionaries for node lookup.

    Returns:
        ingredient_id_to_idx: {ingredient_id (int) -> idx (int)}
        molecule_id_to_idx: {pubchem_id (int) -> idx (int)}
        name_to_ingredient_idx: {normalized_name (str) -> idx (int)}
    """
    ingredient_id_to_idx = {
        int(row["ingredient_id"]): idx
        for idx, row in ing_df.reset_index(drop=True).iterrows()
    }
    molecule_id_to_idx = {
        int(row["pubchem_id"]): idx
        for idx, row in mol_df.reset_index(drop=True).iterrows()
    }
    name_to_ingredient_idx = {
        str(row["name"]).lower().strip(): ingredient_id_to_idx[int(row["ingredient_id"])]
        for _, row in ing_df.iterrows()
        if int(row["ingredient_id"]) in ingredient_id_to_idx
    }

    logger.info(
        "Built index dicts: %d ingredients, %d molecules",
        len(ingredient_id_to_idx),
        len(molecule_id_to_idx),
    )
    return ingredient_id_to_idx, molecule_id_to_idx, name_to_ingredient_idx


# ---------------------------------------------------------------------------
# Node feature constructors
# ---------------------------------------------------------------------------


def _build_ingredient_features(
    ing_df: pd.DataFrame,
    mol_df: pd.DataFrame,
    ingredient_id_to_idx: dict,
    molecule_id_to_idx: dict,
    fp_fmt: str,
) -> torch.Tensor:
    """Build ingredient node feature matrix.

    Columns used (by prefix):
        texture_, temperature_, cultural_context_, flavor_profile_

    Mean-pools Morgan fingerprints of each ingredient's molecules and
    concatenates them with the multimodal feature columns.

    Returns:
        Tensor of shape [N_ingredients, D], dtype float32.
    """
    n = len(ing_df)

    # Step 1: Identify multimodal columns by prefix
    feature_prefixes = ("texture_", "temperature_", "cultural_context_", "flavor_profile_")
    feature_cols = [c for c in ing_df.columns if c.startswith(feature_prefixes)]

    if not feature_cols:
        logger.warning(
            "No multimodal feature columns found with prefixes %s; "
            "using [N, 1] zero placeholder",
            feature_prefixes,
        )
        multimodal = np.zeros((n, 1), dtype=np.float32)
    else:
        logger.info("Using %d multimodal feature columns", len(feature_cols))
        multimodal = ing_df[feature_cols].fillna(0.0).values.astype(np.float32)

    # Step 2: Build ingredient -> molecule mapping
    # Try ingredients.parquet molecule_ids column first; fall back to raw CSV
    fp_dim = 1024
    ing_mol_map: dict[int, list[int]] = {}  # ingredient_idx -> list of molecule_idxs

    if "molecule_ids" in ing_df.columns:
        logger.info(
            "Deriving ingredient->molecule map from ingredients.parquet 'molecule_ids' column"
        )
        for idx, row in ing_df.reset_index(drop=True).iterrows():
            mol_ids = row.get("molecule_ids", []) or []
            ing_mol_map[idx] = [
                molecule_id_to_idx[int(mid)]
                for mid in mol_ids
                if int(mid) in molecule_id_to_idx
            ]
    else:
        raw_path = "data/raw/ingredients.csv"
        if os.path.exists(raw_path):
            logger.info(
                "molecule_ids not in ingredients.parquet; "
                "deriving ingredient->molecule map from %s",
                raw_path,
            )
            raw_ing = pd.read_csv(raw_path)
            raw_map: dict[int, list[int]] = {}
            for _, row in raw_ing.iterrows():
                ing_id = int(row["ingredient_id"])
                try:
                    mols = json.loads(row["molecules_json"]) if pd.notna(row.get("molecules_json")) else []
                except (json.JSONDecodeError, TypeError):
                    mols = []
                raw_map[ing_id] = [
                    int(m["pubchem_id"]) for m in mols if "pubchem_id" in m
                ]
            # Map from ingredient_idx
            for idx, row in ing_df.reset_index(drop=True).iterrows():
                ing_id = int(row["ingredient_id"])
                pubchem_ids = raw_map.get(ing_id, [])
                ing_mol_map[idx] = [
                    molecule_id_to_idx[pid]
                    for pid in pubchem_ids
                    if pid in molecule_id_to_idx
                ]
        else:
            logger.warning(
                "molecule_ids column missing and %s not found; "
                "ingredient->molecule map will be empty (zero mean-pooled fps)",
                raw_path,
            )

    # Pre-deserialize all molecule fps
    mol_fps: dict[int, "np.ndarray | None"] = {}
    for mol_idx, row in mol_df.reset_index(drop=True).iterrows():
        fp_bytes = row.get("morgan_fp_bytes")
        mol_fps[mol_idx] = _deserialize_fp(fp_bytes, fp_fmt)

    # Step 3: Mean-pool fps per ingredient
    mean_fps = np.zeros((n, fp_dim), dtype=np.float32)
    for ing_idx in range(n):
        mol_idxs = ing_mol_map.get(ing_idx, [])
        valid_fps = [
            mol_fps[midx] for midx in mol_idxs
            if midx in mol_fps and mol_fps[midx] is not None
        ]
        if valid_fps:
            mean_fps[ing_idx] = np.mean(valid_fps, axis=0).astype(np.float32)
        # else: zero (already initialized)

    # Step 4: Concat multimodal + mean_fp
    combined = np.concatenate([multimodal, mean_fps], axis=1).astype(np.float32)
    tensor = torch.from_numpy(combined)

    logger.info("Ingredient feature matrix: shape %s", tuple(tensor.shape))
    return tensor


def _build_molecule_features(mol_df: pd.DataFrame, fp_fmt: str) -> torch.Tensor:
    """Build molecule node feature matrix.

    Combines scaled physico-chemical descriptors with Morgan fingerprint bits.

    Returns:
        Tensor of shape [N_molecules, len(descriptor_cols) + 1024], dtype float32.
    """
    n = len(mol_df)

    # Descriptor columns — only use those actually present
    all_descriptor_cols = ["MW", "logP", "HBD", "HBA", "rotatable_bonds", "TPSA"]
    descriptor_cols = [c for c in all_descriptor_cols if c in mol_df.columns]
    missing_desc = [c for c in all_descriptor_cols if c not in mol_df.columns]
    if missing_desc:
        logger.warning("Descriptor columns missing from molecules.parquet: %s", missing_desc)
    logger.info("Using %d descriptor columns: %s", len(descriptor_cols), descriptor_cols)

    # Fill NaN and scale descriptors
    desc_matrix = mol_df[descriptor_cols].fillna(0.0).values.astype(np.float32)
    if len(descriptor_cols) > 0:
        scaler = StandardScaler()
        desc_scaled = scaler.fit_transform(desc_matrix).astype(np.float32)
    else:
        desc_scaled = np.zeros((n, 0), dtype=np.float32)

    # Deserialize Morgan fingerprints
    fp_matrix = np.zeros((n, 1024), dtype=np.float32)
    n_failed = 0
    for mol_idx, row in mol_df.reset_index(drop=True).iterrows():
        fp_bytes = row.get("morgan_fp_bytes")
        arr = _deserialize_fp(fp_bytes, fp_fmt)
        if arr is not None:
            if len(arr) == 1024:
                fp_matrix[mol_idx] = arr
            else:
                logger.warning(
                    "Molecule idx %d: fp length %d != 1024; using zeros", mol_idx, len(arr)
                )
                n_failed += 1
        else:
            n_failed += 1

    if n_failed > 0:
        logger.warning(
            "%d / %d molecules failed fp deserialization (using zeros)", n_failed, n
        )

    # Concatenate descriptors + fp
    combined = np.concatenate([desc_scaled, fp_matrix], axis=1).astype(np.float32)
    tensor = torch.from_numpy(combined)

    logger.info("Molecule feature matrix: shape %s", tuple(tensor.shape))
    return tensor


# ---------------------------------------------------------------------------
# Validation gate
# ---------------------------------------------------------------------------


def run_validation_gate(data: HeteroData) -> None:
    """Check node/edge thresholds. Raises ValueError with diagnostics if not met."""
    checks = []
    passed = True

    n_ing = data["ingredient"].num_nodes if "ingredient" in data.node_types else 0
    n_mol = data["molecule"].num_nodes if "molecule" in data.node_types else 0

    def check(label, actual, threshold):
        ok = actual >= threshold
        symbol = "\u2713" if ok else "\u2717"
        if ok:
            checks.append(f"  {symbol} {label}: {actual:,} found (>={threshold:,})")
        else:
            checks.append(
                f"  {symbol} {label}: {actual:,} found, {threshold:,} required"
            )
        return ok

    passed &= check("Ingredient nodes", n_ing, 500)
    passed &= check("Molecule nodes", n_mol, 2000)

    required_edge_types = [
        ("ingredient", "contains", "molecule"),
        ("ingredient", "co_occurs", "ingredient"),
        ("molecule", "structurally_similar", "molecule"),
    ]
    for et in required_edge_types:
        present = et in data.edge_types
        symbol = "\u2713" if present else "\u2717"
        label = f"Edge type {et[1]!r}"
        if present:
            n_edges = (
                data[et].num_edges
                if hasattr(data[et], "num_edges")
                else data[et].edge_index.shape[1]
            )
            checks.append(f"  {symbol} {label}: present ({n_edges:,} edges)")
        else:
            checks.append(f"  {symbol} {label}: MISSING")
        passed &= present

    print("\n=== Graph Validation Gate ===")
    for line in checks:
        print(line)

    if not passed:
        print(
            "\nRemediation: Run Phase 2 feature engineering and verify "
            "data/processed/ parquet files exist"
        )
        raise ValueError(
            "Graph validation gate failed \u2014 see diagnostics above. Graph not saved."
        )

    print("  All checks passed.")
    print("=============================\n")


# ---------------------------------------------------------------------------
# Main build function (skeleton — edges added in Plan 03-03)
# ---------------------------------------------------------------------------


def build_graph(force: bool = False) -> None:
    """Build the heterogeneous graph from processed parquets.

    Args:
        force: If True, rebuild even if OUTPUT_PT already exists.
    """
    if not force and os.path.exists(OUTPUT_PT):
        logger.info(
            "[SKIP] %s already exists. Pass --force to rebuild.", OUTPUT_PT
        )
        return

    t0 = time.time()
    logger.info("=== Phase 3: Graph Construction ===")

    # --- Load inputs ---
    ing_df, mol_df, cooc_df = _load_parquets()

    # --- Probe fp format ---
    fp_fmt = _probe_fp_format(mol_df["morgan_fp_bytes"].iloc[0])
    logger.info("Morgan fp format: %s", fp_fmt)

    # --- Build index dicts ---
    ingredient_id_to_idx, molecule_id_to_idx, name_to_ingredient_idx = (
        _build_index_dicts(ing_df, mol_df)
    )

    # --- Build node features ---
    ingredient_feat = _build_ingredient_features(
        ing_df, mol_df, ingredient_id_to_idx, molecule_id_to_idx, fp_fmt
    )
    molecule_feat = _build_molecule_features(mol_df, fp_fmt)

    # --- Build edges (Plan 03-03 will add these) ---
    # TODO: contains edges
    # TODO: co_occurs edges
    # TODO: structural edges

    # --- Assemble HeteroData (Plan 03-04 will complete this) ---
    # TODO: assemble, validate, split, save

    logger.info("=== Graph Construction complete (%.1f s) ===", time.time() - t0)


def main():
    parser = argparse.ArgumentParser(
        description="Build Phase 3 heterogeneous graph."
    )
    parser.add_argument(
        "--force", action="store_true", help="Rebuild even if output exists."
    )
    args = parser.parse_args()
    build_graph(force=args.force)


if __name__ == "__main__":
    main()
