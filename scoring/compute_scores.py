"""
scoring/compute_scores.py — Standalone orchestration script for Phase 5 scoring.

Reads Phase 4 artifacts (ingredient_embeddings.pkl, hetero_data.pt) and writes
scoring/scored_pairs.pkl with all ingredient pair surprise scores.

Usage:
    python scoring/compute_scores.py
    python scoring/compute_scores.py --force

Importable as:
    from scoring.compute_scores import run_scoring
"""

from __future__ import annotations

import logging
import pickle
import sys
from pathlib import Path

import torch

from scoring.score import compute_all_pairs, save_scored_pairs

EMBEDDINGS_PATH = Path("model/embeddings/ingredient_embeddings.pkl")
GRAPH_PATH = Path("graph/hetero_data.pt")
SCORED_PAIRS_PATH = Path("scoring/scored_pairs.pkl")

# Handlers are set up here (entry-point module); scoring/score.py does NOT configure handlers.
Path("logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def run_scoring(force: bool = False) -> Path:
    """
    Compute all ingredient pair surprise scores and save to scoring/scored_pairs.pkl.

    Args:
        force: If True, recompute even if scored_pairs.pkl already exists.

    Returns:
        Path to scored_pairs.pkl.
    """
    # Skip-if-exists check
    if SCORED_PAIRS_PATH.exists() and not force:
        logger.info("scored_pairs.pkl exists — skipping. Pass force=True to recompute.")
        return SCORED_PAIRS_PATH

    # Validate Phase 4 inputs
    if not EMBEDDINGS_PATH.exists():
        logger.error("Missing %s — run Phase 4 first", EMBEDDINGS_PATH)
        sys.exit(1)
    if not GRAPH_PATH.exists():
        logger.error("Missing %s — run Phase 3 first", GRAPH_PATH)
        sys.exit(1)

    # Load embeddings: {ingredient_id: np.ndarray(128,)}
    logger.info("Loading ingredient embeddings from %s", EMBEDDINGS_PATH)
    with open(EMBEDDINGS_PATH, "rb") as f:
        embeddings = pickle.load(f)
    logger.info("Loaded %d ingredient embeddings", len(embeddings))

    # Load graph payload (saved as a dict with 5 named keys)
    logger.info("Loading graph from %s", GRAPH_PATH)
    payload = torch.load(GRAPH_PATH, map_location="cpu", weights_only=False)

    graph = payload["graph"]
    ingredient_id_to_idx = payload.get("ingredient_id_to_idx")
    molecule_id_to_idx = payload.get("molecule_id_to_idx")

    if ingredient_id_to_idx is not None:
        # Invert: graph_idx -> ingredient_id (same integer IDs as embeddings dict keys)
        idx_to_ingredient_id = {v: k for k, v in ingredient_id_to_idx.items()}
    else:
        # Fallback: use positional mapping from embeddings keys
        logger.warning(
            "ingredient_id_to_idx not found in graph payload — using positional fallback"
        )
        embedding_keys = list(embeddings.keys())
        idx_to_ingredient_id = {i: embedding_keys[i] for i in range(len(embedding_keys))}

    if molecule_id_to_idx is not None:
        idx_to_molecule_id = {v: k for k, v in molecule_id_to_idx.items()}
    else:
        logger.warning("molecule_id_to_idx not found in graph payload — using raw indices")
        idx_to_molecule_id = {}

    # Build co_occurrence dict: {(ingredient_id_a, ingredient_id_b): weight}
    logger.info("Building co-occurrence dict from graph edges")
    co_occurrence = {}
    try:
        co_ei = graph["ingredient", "co_occurs", "ingredient"].edge_index
        co_ea = graph["ingredient", "co_occurs", "ingredient"].edge_attr
        for i in range(co_ei.shape[1]):
            src_idx = co_ei[0, i].item()
            dst_idx = co_ei[1, i].item()
            weight = co_ea[i].item()
            src_id = idx_to_ingredient_id.get(src_idx, src_idx)
            dst_id = idx_to_ingredient_id.get(dst_idx, dst_idx)
            co_occurrence[(src_id, dst_id)] = weight
        logger.info("Built co_occurrence dict with %d entries", len(co_occurrence))
    except (KeyError, AttributeError) as exc:
        logger.warning("Could not extract co_occurs edges: %s — proceeding with empty dict", exc)

    # Build molecule_sets: {ingredient_id: set of molecule_ids}
    logger.info("Building molecule sets from contains edges")
    molecule_sets: dict = {}
    try:
        contains_ei = graph["ingredient", "contains", "molecule"].edge_index
        for i in range(contains_ei.shape[1]):
            ing_idx = contains_ei[0, i].item()
            mol_idx = contains_ei[1, i].item()
            ing_id = idx_to_ingredient_id.get(ing_idx, ing_idx)
            mol_id = idx_to_molecule_id.get(mol_idx, mol_idx)
            molecule_sets.setdefault(ing_id, set()).add(mol_id)
        logger.info("Built molecule_sets for %d ingredients", len(molecule_sets))
    except (KeyError, AttributeError) as exc:
        logger.warning("Could not extract contains edges: %s — proceeding with empty sets", exc)

    # Compute all pairs (vectorized)
    logger.info("Computing all ingredient pairs (vectorized)...")
    df = compute_all_pairs(embeddings, co_occurrence, molecule_sets)

    # Save atomically
    save_scored_pairs(df)

    # Summary table
    n_pairs = len(df)
    label_counts = df["label"].value_counts()
    logger.info("Scored %d pairs.", n_pairs)
    for label in ["Surprising", "Unexpected", "Classic"]:
        count = label_counts.get(label, 0)
        pct = 100 * count / n_pairs if n_pairs > 0 else 0
        logger.info("  %s: %d (%.1f%%)", label, count, pct)
    logger.info("Saved to %s", SCORED_PAIRS_PATH)

    return SCORED_PAIRS_PATH


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compute all ingredient pair scores")
    parser.add_argument("--force", action="store_true", help="Recompute even if file exists")
    args = parser.parse_args()
    run_scoring(force=args.force)
