"""
Loss functions for FlavorGAT training (Phase 4).

Exports:
    molecular_bce_loss  — BCE link-prediction loss on ingredient pairs sharing
                          flavor molecules (positive edges pre-filtered upstream)
    recipe_bce_loss     — BCE link-prediction loss on ingredient pairs co-occurring
                          in recipes (positive edges pre-filtered upstream)
    info_nce_loss       — InfoNCE contrastive loss with learnable temperature
    combined_loss       — Weighted sum: alpha*mol + beta*rec + gamma*nce
"""

import torch
import torch.nn.functional as F
from torch_geometric.utils import negative_sampling


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _bce_link_pred_loss(
    z_src: torch.Tensor,
    z_dst: torch.Tensor,
    pos_edge_index: torch.Tensor,
    num_nodes,
    device: str,
) -> torch.Tensor:
    """
    Shared BCE link-prediction implementation.

    Args:
        z_src: (N, D) source node embeddings
        z_dst: (M, D) destination node embeddings (same as z_src for homogeneous)
        pos_edge_index: (2, K) positive edge indices
        num_nodes: int or (int, int) for bipartite — passed to negative_sampling
        device: device string for label tensor creation

    Returns:
        Scalar BCE-with-logits loss tensor.
    """
    # Positive scores via dot product
    src_pos = z_src[pos_edge_index[0]]
    dst_pos = z_dst[pos_edge_index[1]]
    pos_scores = (src_pos * dst_pos).sum(dim=-1)  # (K,)

    # Negative sampling — equal number of negatives as positives
    # Pass pos_edge_index as edge_index so known edges are avoided
    neg_edge_index = negative_sampling(
        edge_index=pos_edge_index,
        num_nodes=num_nodes,
        num_neg_samples=pos_edge_index.size(1),
    ).long()

    src_neg = z_src[neg_edge_index[0]]
    dst_neg = z_dst[neg_edge_index[1]]
    neg_scores = (src_neg * dst_neg).sum(dim=-1)  # (K,)

    scores = torch.cat([pos_scores, neg_scores])
    labels = torch.cat([
        torch.ones(pos_scores.size(0)),
        torch.zeros(neg_scores.size(0)),
    ]).to(device)

    return F.binary_cross_entropy_with_logits(scores, labels)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def molecular_bce_loss(
    z_src: torch.Tensor,
    z_dst: torch.Tensor,
    pos_edge_index: torch.Tensor,
    num_nodes,
    device: str,
) -> torch.Tensor:
    """
    BCE link-prediction loss on ingredient pairs sharing >mol_threshold molecules.

    Positive edges (pos_edge_index) are pre-computed by the training script
    using the mol_threshold filter — this function only scores them.

    Args:
        z_src: (N, D) ingredient embeddings for source nodes
        z_dst: (M, D) ingredient embeddings for destination nodes
        pos_edge_index: (2, K) positive edge index tensor
        num_nodes: int or (int, int) — number of nodes for negative_sampling
        device: device string (e.g. 'cpu', 'mps')

    Returns:
        Scalar tensor — BCE loss value.
    """
    return _bce_link_pred_loss(z_src, z_dst, pos_edge_index, num_nodes, device)


def recipe_bce_loss(
    z_src: torch.Tensor,
    z_dst: torch.Tensor,
    pos_edge_index: torch.Tensor,
    num_nodes,
    device: str,
) -> torch.Tensor:
    """
    BCE link-prediction loss on ingredient pairs co-occurring in >recipe_threshold recipes.

    Semantically separate from molecular_bce_loss: the training script calls both
    and logs them independently. Internally uses the same _bce_link_pred_loss helper.

    Args:
        z_src: (N, D) ingredient embeddings for source nodes
        z_dst: (M, D) ingredient embeddings for destination nodes
        pos_edge_index: (2, K) positive edge index tensor
        num_nodes: int or (int, int) — number of nodes for negative_sampling
        device: device string (e.g. 'cpu', 'mps')

    Returns:
        Scalar tensor — BCE loss value.
    """
    return _bce_link_pred_loss(z_src, z_dst, pos_edge_index, num_nodes, device)


def info_nce_loss(
    z: torch.Tensor,
    pos_pairs: torch.Tensor,
    tau: float = 0.15,
) -> torch.Tensor:
    """
    InfoNCE contrastive loss on ingredient embeddings.

    L2-normalizes z INSIDE the function (returns a new tensor — does not
    mutate the input). Masks diagonal with -inf to exclude self-similarity.

    Args:
        z: (N, D) ingredient embeddings — NOT pre-normalized
        pos_pairs: (2, K) LongTensor; pos_pairs[0] = anchors, pos_pairs[1] = positives
        tau: temperature scalar (default 0.15)

    Returns:
        Scalar tensor — InfoNCE cross-entropy loss.
        Returns torch.tensor(0.0, requires_grad=True) when pos_pairs is empty.
    """
    if pos_pairs.size(1) == 0:
        return torch.tensor(0.0, requires_grad=True)

    # L2-normalize — F.normalize returns a new tensor, input z is not mutated
    z_norm = F.normalize(z, dim=-1)

    # Similarity matrix: (N, N) — cosine similarity scaled by temperature
    sim = torch.mm(z_norm, z_norm.T) / tau

    # Mask diagonal with -inf to exclude self-similarity
    mask = torch.eye(z_norm.size(0), dtype=torch.bool, device=z_norm.device)
    sim.masked_fill_(mask, float('-inf'))

    # Cross-entropy over positive pair targets
    labels = pos_pairs[1]
    loss = F.cross_entropy(sim[pos_pairs[0]], labels)

    return loss


def combined_loss(
    mol_loss: torch.Tensor,
    rec_loss: torch.Tensor,
    nce_loss: torch.Tensor,
    alpha: float,
    beta: float,
    gamma: float,
) -> torch.Tensor:
    """
    Weighted combination of the three loss components.

    Does NOT call .item() on any input — the gradient graph is kept intact
    for backpropagation. Logging of individual components is the caller's
    responsibility.

    Args:
        mol_loss: scalar tensor from molecular_bce_loss
        rec_loss: scalar tensor from recipe_bce_loss
        nce_loss: scalar tensor from info_nce_loss
        alpha: weight for molecular BCE loss
        beta: weight for recipe BCE loss
        gamma: weight for InfoNCE loss

    Returns:
        Scalar tensor — alpha * mol + beta * rec + gamma * nce.
    """
    return alpha * mol_loss + beta * rec_loss + gamma * nce_loss
