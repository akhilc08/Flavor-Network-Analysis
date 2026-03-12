"""
FlavorGAT: 3-layer heterogeneous Graph Attention Network for flavor-network embedding.

Architecture:
  - Per-node-type linear projections to hidden_channels (lazy init via PyG Linear)
  - 3 HeteroConv layers, each wrapping one GATConv per edge type
    - concat=True + heads=N means out_channels arg = hidden_channels // heads
    - add_self_loops=False on all layers (required for bipartite edge types)
  - BatchNorm1d + ReLU + dropout between every pair of GATConv layers
  - Final per-node-type projection to embed_dim (128-dim embedding space)

Exports:
  FlavorGAT
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import HeteroConv, GATConv, Linear

# Edge types present in graph/hetero_data.pt (produced by Phase 3)
_EDGE_TYPES = [
    ('ingredient', 'contains', 'molecule'),
    ('molecule', 'rev_contains', 'ingredient'),
    ('ingredient', 'co_occurs', 'ingredient'),
    ('molecule', 'structurally_similar', 'molecule'),
]

# Node types in the heterogeneous graph
_NODE_TYPES = ['ingredient', 'molecule']


def _build_hetero_conv(hidden_channels: int, heads: int, dropout: float) -> HeteroConv:
    """Build one HeteroConv layer wrapping a GATConv for each edge type.

    out_channels = hidden_channels // heads ensures that concat=True keeps the
    post-concatenation dimension equal to hidden_channels (avoids the "dim explosion"
    pitfall documented in 04-RESEARCH.md).
    """
    out_per_head = hidden_channels // heads
    return HeteroConv(
        {
            # Bipartite edges require in_channels=(-1, -1) tuple
            ('ingredient', 'contains', 'molecule'): GATConv(
                (-1, -1), out_per_head, heads=heads,
                concat=True, add_self_loops=False, dropout=dropout,
            ),
            ('molecule', 'rev_contains', 'ingredient'): GATConv(
                (-1, -1), out_per_head, heads=heads,
                concat=True, add_self_loops=False, dropout=dropout,
            ),
            # Homogeneous edges use scalar in_channels
            ('ingredient', 'co_occurs', 'ingredient'): GATConv(
                -1, out_per_head, heads=heads,
                concat=True, add_self_loops=False, dropout=dropout,
            ),
            ('molecule', 'structurally_similar', 'molecule'): GATConv(
                -1, out_per_head, heads=heads,
                concat=True, add_self_loops=False, dropout=dropout,
            ),
        },
        aggr='sum',
    )


class FlavorGAT(nn.Module):
    """Heterogeneous GAT that maps ingredient and molecule nodes to a shared embedding space.

    Args:
        hidden_channels: Width of all hidden node representations (default: 256).
        embed_dim: Dimensionality of the final output embeddings (default: 128).
        heads: Number of attention heads in each GATConv layer (default: 8).
        dropout: Dropout probability applied between GATConv layers (default: 0.3).
        num_layers: Number of HeteroConv message-passing layers (default: 3).
    """

    def __init__(
        self,
        hidden_channels: int = 256,
        embed_dim: int = 128,
        heads: int = 8,
        dropout: float = 0.3,
        num_layers: int = 3,
    ) -> None:
        super().__init__()

        self.num_layers = num_layers
        self.dropout_p = dropout
        # Also expose as self.dropout for compatibility with tests that check model.dropout
        self.dropout = dropout

        # 1. Per-node-type input projection to hidden_channels (lazy init)
        self.proj = nn.ModuleDict({
            node_type: Linear(-1, hidden_channels)
            for node_type in _NODE_TYPES
        })

        # 2. Stack of num_layers HeteroConv message-passing layers
        self.convs = nn.ModuleList([
            _build_hetero_conv(hidden_channels, heads, dropout)
            for _ in range(num_layers)
        ])

        # 3. BatchNorm1d per node type per layer: keys '{node_type}_{layer_idx}'
        self.bn = nn.ModuleDict({
            f'{node_type}_{i}': nn.BatchNorm1d(hidden_channels)
            for node_type in _NODE_TYPES
            for i in range(num_layers)
        })

        # 4. Final projection to embed_dim
        self.embed_proj = nn.ModuleDict({
            node_type: Linear(hidden_channels, embed_dim)
            for node_type in _NODE_TYPES
        })

    def forward(self, x_dict: dict, edge_index_dict: dict) -> dict:
        """Run the full forward pass and return node embeddings.

        Args:
            x_dict: Mapping from node type str -> feature tensor (N_type, F_type).
            edge_index_dict: Mapping from (src_type, rel, dst_type) -> edge_index (2, E).

        Returns:
            Dict mapping node type str -> embedding tensor (N_type, embed_dim).
        """
        # Step 1: Project each node type to hidden_channels
        x_dict = {
            node_type: self.proj[node_type](x).relu()
            for node_type, x in x_dict.items()
        }

        # Step 2: Apply num_layers rounds of message passing with BN + dropout
        for i in range(self.num_layers):
            prev_x_dict = x_dict  # keep reference for fallback (sparse mini-graph case)
            x_dict = self.convs[i](x_dict, edge_index_dict)

            # Apply BN + ReLU + dropout per node type
            new_x_dict = {}
            for node_type in _NODE_TYPES:
                # Fallback: if a node type is absent from conv output (e.g., disconnected
                # node type in a synthetic test graph), carry forward the previous embedding
                x = x_dict.get(node_type, prev_x_dict.get(node_type))
                if x is None:
                    continue
                x = self.bn[f'{node_type}_{i}'](x).relu()
                x = F.dropout(x, p=self.dropout_p, training=self.training)
                new_x_dict[node_type] = x
            x_dict = new_x_dict

        # Step 3: Final projection to embed_dim (no activation — raw embeddings for dot-product scoring)
        x_dict = {
            node_type: self.embed_proj[node_type](x)
            for node_type, x in x_dict.items()
            if node_type in self.embed_proj
        }

        return x_dict
