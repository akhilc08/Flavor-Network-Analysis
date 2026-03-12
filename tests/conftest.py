"""
Shared pytest fixtures for Phase 4 model training tests.

Provides a tiny synthetic HeteroData graph for unit testing GNN models
without requiring the full pipeline to have run.
"""

import pytest
import torch
from torch_geometric.data import HeteroData


@pytest.fixture(scope="module")
def tiny_hetero_graph():
    """
    A tiny synthetic HeteroData graph for model unit tests.

    Nodes:
        ingredient: 10 nodes, 20 features each
        molecule:   50 nodes, 15 features each

    Edges:
        (ingredient, contains, molecule):                 30 directed edges
        (molecule, rev_contains, ingredient):             30 reverse edges
        (ingredient, co_occurs, ingredient):              20 edges, no self-loops
        (molecule, structurally_similar, molecule):       40 edges, no self-loops
    """
    torch.manual_seed(42)

    data = HeteroData()

    # Node features
    data["ingredient"].x = torch.randn(10, 20, dtype=torch.float32)
    data["molecule"].x = torch.randn(50, 15, dtype=torch.float32)

    # (ingredient, contains, molecule): 30 edges — ingredient indices in [0,9], molecule in [0,49]
    ing_idx = torch.randint(0, 10, (30,))
    mol_idx = torch.randint(0, 50, (30,))
    data["ingredient", "contains", "molecule"].edge_index = torch.stack([ing_idx, mol_idx], dim=0)

    # (molecule, rev_contains, ingredient): reverse of contains
    data["molecule", "rev_contains", "ingredient"].edge_index = torch.stack([mol_idx, ing_idx], dim=0)

    # (ingredient, co_occurs, ingredient): 20 edges, no self-loops
    # Generate until we have 20 pairs with src != dst
    co_src, co_dst = [], []
    rng_state = torch.get_rng_state()
    while len(co_src) < 20:
        s = torch.randint(0, 10, (1,)).item()
        d = torch.randint(0, 10, (1,)).item()
        if s != d:
            co_src.append(s)
            co_dst.append(d)
    data["ingredient", "co_occurs", "ingredient"].edge_index = torch.tensor(
        [co_src, co_dst], dtype=torch.long
    )

    # (molecule, structurally_similar, molecule): 40 edges, no self-loops
    sim_src, sim_dst = [], []
    while len(sim_src) < 40:
        s = torch.randint(0, 50, (1,)).item()
        d = torch.randint(0, 50, (1,)).item()
        if s != d:
            sim_src.append(s)
            sim_dst.append(d)
    data["molecule", "structurally_similar", "molecule"].edge_index = torch.tensor(
        [sim_src, sim_dst], dtype=torch.long
    )

    return data


@pytest.fixture(scope="module")
def tiny_link_labels():
    """
    Synthetic link-prediction labels for ingredient→ingredient edges.

    Returns a dict with:
        pos_edge_index: (2, 5) tensor — positive validation edges (ingredient→ingredient)
        neg_edge_index: (2, 5) tensor — negative validation edges
        edge_label:     (10,)  tensor — 5 ones (positive) then 5 zeros (negative)
    """
    torch.manual_seed(42)

    # Positive edges: 5 distinct src/dst pairs in [0, 9] with src != dst
    pos_pairs = []
    while len(pos_pairs) < 5:
        s = torch.randint(0, 10, (1,)).item()
        d = torch.randint(0, 10, (1,)).item()
        if s != d:
            pos_pairs.append((s, d))

    # Negative edges: 5 more pairs with src != dst
    neg_pairs = []
    seen = set(pos_pairs)
    while len(neg_pairs) < 5:
        s = torch.randint(0, 10, (1,)).item()
        d = torch.randint(0, 10, (1,)).item()
        if s != d and (s, d) not in seen:
            neg_pairs.append((s, d))
            seen.add((s, d))

    pos_src = torch.tensor([p[0] for p in pos_pairs], dtype=torch.long)
    pos_dst = torch.tensor([p[1] for p in pos_pairs], dtype=torch.long)
    neg_src = torch.tensor([p[0] for p in neg_pairs], dtype=torch.long)
    neg_dst = torch.tensor([p[1] for p in neg_pairs], dtype=torch.long)

    return {
        "pos_edge_index": torch.stack([pos_src, pos_dst], dim=0),
        "neg_edge_index": torch.stack([neg_src, neg_dst], dim=0),
        "edge_label": torch.cat([torch.ones(5), torch.zeros(5)]),
    }
