# Phase 4: Model Training - Research

**Researched:** 2026-03-11
**Domain:** PyTorch Geometric heterogeneous GAT, InfoNCE contrastive loss, MPS training, link-prediction AUC
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Training UX & Console Output**
- tqdm outer progress bar over epochs (1 bar showing epoch N/200)
- Per-epoch compact summary line: `Epoch 45/200 | AUC: 0.742↑ | Loss: 0.312 (mol=0.128, rec=0.115, nce=0.069) | LR: 8.3e-4`
- Arrow indicator (↑/↓/=) on AUC shows trend
- All 3 loss components (molecular, recipe, InfoNCE) logged separately — never merged
- CSV log written to `logs/training_metrics.csv`: one row per epoch with all loss components, AUC, lr
- Final summary printed at end: best AUC epoch, total time, checkpoint path

**Checkpoint & Resume Strategy**
- Save best checkpoint on AUC improvement: `model/checkpoints/best_model.pt`
- Periodic safety checkpoints every 50 epochs: `epoch_050.pt`, `epoch_100.pt`, `epoch_150.pt`, `epoch_200.pt`
- Checkpoint includes: model state dict, optimizer state dict, scheduler state dict, current epoch, best AUC
- CLI flag `--resume model/checkpoints/epoch_050.pt` to restart from checkpoint; cosine LR schedule restarted from saved epoch
- If `--resume` and `best_model.pt` both exist, resume preserves existing best AUC as comparison baseline

**Hyperparameter Configurability**
- All hyperparameters as named argparse flags with spec defaults
- Full flag list: `--epochs 200 --lr 1e-3 --hidden 256 --embed 128 --heads 8 --dropout 0.3 --alpha 0.4 --beta 0.4 --gamma 0.2 --tau 0.15 --mol-threshold 5 --recipe-threshold 10`
- `--help` output is portfolio-visible and shows all hyperparameters with defaults
- Argument values echoed to console at training start

**OOM & MPS Fallback**
- Auto-detect backend: MPS if `torch.backends.mps.is_available()`, else CPU
- Warning printed if falling back to CPU
- Before training: print memory estimate based on graph node/edge counts and hidden_dim
- OOM handling: catch `RuntimeError` containing "out of memory", call `torch.mps.empty_cache()`, print clear message with suggested fix, then exit cleanly
- Embedding export uses `@torch.no_grad()` and moves tensors to CPU before pkl write

### Claude's Discretion
- Exact learning rate scheduler implementation details (warm-up vs cold start with cosine)
- Internal batch construction for link prediction (negative sampling ratio)
- Whether to use `torch.compile()` for MPS acceleration
- Log file rotation / append vs overwrite behavior for repeated training runs

### Deferred Ideas (OUT OF SCOPE)
- None — user deferred all implementation decisions to Claude's discretion
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODEL-01 | GAT model with HeteroConv wrapper: 3 layers, 8 attention heads, 256 hidden dim, separate linear projections per node type to shared 128-dim embedding space | HeteroConv + GATConv(-1,-1) pattern; ModuleDict for per-type linear projections |
| MODEL-02 | GATConv layers use add_self_loops=False on all bipartite edge types | GATConv bipartite mode confirmed; self-loops undefined for bipartite, use learnable skip-connection instead |
| MODEL-03 | Batch normalization and dropout (0.3) applied between layers | Standard nn.BatchNorm1d per node type in dict; F.dropout in forward pass |
| MODEL-04 | Molecular loss: BCE link prediction on ingredient pairs sharing >5 flavor molecules (label=1) vs 0 shared (label=0) | Pre-computed edge label index from graph; BCEWithLogitsLoss with negative sampling |
| MODEL-05 | Recipe loss: BCE link prediction on ingredient pairs co-occurring in >10 recipes (label=1) | Same pattern as MODEL-04; separate edge_label_index from graph |
| MODEL-06 | InfoNCE contrastive loss with temperature τ starting at 0.1–0.2; gradient clipping (max_norm=1.0) applied unconditionally; InfoNCE logged separately | Custom InfoNCE implementation; torch.nn.utils.clip_grad_norm_ |
| MODEL-07 | Combined loss: α=0.4 × molecular_loss + β=0.4 × recipe_loss + γ=0.2 × contrastive_loss; α/β/γ tunable | Argparse flags --alpha --beta --gamma; weighted sum |
| MODEL-08 | Training runs 200 epochs, Adam optimizer lr=1e-3, cosine LR schedule, MPS backend; best checkpoint saved by validation AUC | CosineAnnealingLR(optimizer, T_max=epochs); sklearn.metrics.roc_auc_score for validation |
| MODEL-09 | Ingredient embeddings (128-dim dict) exported to model/embeddings/ingredient_embeddings.pkl after training | Extract ingredient node embeddings from final HeteroConv pass; save as {ingredient_id: np.array} dict via pickle |
</phase_requirements>

---

## Summary

Phase 4 trains a 3-layer heterogeneous Graph Attention Network (GAT) on the `graph/hetero_data.pt` artifact produced by Phase 3. The model uses PyTorch Geometric's `HeteroConv` wrapper around `GATConv` layers to process three edge types simultaneously (ingredient→molecule "contains", ingredient→ingredient "co-occurs", molecule→molecule "structurally-similar"). Training uses dual BCE supervision (molecular matching + recipe co-occurrence) combined with an InfoNCE contrastive loss, optimized together as a weighted sum.

The key technical challenges in this phase are: (1) correctly configuring `GATConv` for bipartite edge types using `add_self_loops=False` and tuple `in_channels`, (2) constructing positive/negative edge batches per epoch for the two BCE objectives without data leakage from the Phase 3 split, (3) implementing InfoNCE at the correct temperature range (0.1–0.2, not the commonly cited 0.07 which is too tight for food-domain negatives with high molecular overlap), and (4) managing MPS memory to complete 200 epochs without OOM on an M2 with unified memory.

The AUC >= 0.70 gate requires careful validation: positive edges come from `val_data.edge_label_index` (from Phase 3's `RandomLinkSplit`), negative edges from on-the-fly `negative_sampling`, and scoring is done via dot-product on the 128-dim ingredient embeddings followed by `sklearn.metrics.roc_auc_score`.

**Primary recommendation:** Build the model class using `HeteroConv({edge_type: GATConv((-1,-1), hidden, heads=8, concat=True, add_self_loops=False)})` per layer, project all node types to 128-dim before dot-product scoring, and use `CosineAnnealingLR(optimizer, T_max=epochs)` with no warm-up (cold start is sufficient for 200 epochs).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| torch | 2.6.* | Tensor ops, autograd, MPS backend | Pinned in environment.yml |
| torch_geometric | 2.7.* | HeteroConv, GATConv, RandomLinkSplit, negative_sampling | Pinned in environment.yml |
| sklearn (scikit-learn) | latest via pip | roc_auc_score for validation AUC | Standard ML metrics library; no PyG equivalent |
| numpy | pinned | Embedding export to pkl, AUC input arrays | Interop layer between PyTorch tensors and sklearn |
| tqdm | 4.* | Outer epoch progress bar | Already used in Phase 1 (consistent pattern) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| argparse | stdlib | CLI flags for all hyperparameters | Always — required by spec |
| csv / pathlib | stdlib | Write logs/training_metrics.csv | Per-epoch logging |
| pickle | stdlib | Serialize ingredient_embeddings.pkl | Embedding export (MODEL-09) |
| torch.nn.utils | stdlib (torch) | clip_grad_norm_(max_norm=1.0) | Every backward pass unconditionally |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GATConv | GATv2Conv | GATv2 fixes static attention problem but is slower; GATConv sufficient for this graph size |
| CosineAnnealingLR | CosineAnnealingWarmRestarts | Warm restarts add hyperparameter (T_0); unnecessary complexity for single 200-epoch run |
| sklearn roc_auc_score | torchmetrics AUROC | torchmetrics requires an extra install; sklearn already available |
| Manual InfoNCE | `infonce` pip package | The package is trivially simple; implementing inline avoids a dependency and allows exact temperature control |

**Installation (no new installs needed):**
```bash
# All required packages already in environment.yml
# scikit-learn is a transitive dependency of several already-installed packages
# Verify: python -c "from sklearn.metrics import roc_auc_score; print('ok')"
```

---

## Architecture Patterns

### Recommended Project Structure

```
model/
├── train_gat.py          # main training script (argparse entry point)
├── gat_model.py          # FlavorGAT class definition
├── checkpoints/
│   ├── best_model.pt     # saved when val AUC improves
│   ├── epoch_050.pt      # periodic safety checkpoint
│   ├── epoch_100.pt
│   ├── epoch_150.pt
│   └── epoch_200.pt
└── embeddings/
    └── ingredient_embeddings.pkl   # exported after training
logs/
└── training_metrics.csv  # per-epoch: epoch,mol_loss,rec_loss,nce_loss,total_loss,val_auc,lr
```

### Pattern 1: HeteroConv + GATConv Layer Setup

**What:** Wrap one `GATConv` per edge type in `HeteroConv`; use `(-1, -1)` for lazy initialization; disable self-loops on all bipartite edge types.

**When to use:** Every message-passing layer in the 3-layer stack.

```python
# Source: https://pytorch-geometric.readthedocs.io/en/latest/notes/heterogeneous.html
from torch_geometric.nn import HeteroConv, GATConv

conv = HeteroConv({
    ('ingredient', 'contains', 'molecule'): GATConv(
        (-1, -1), hidden_channels // heads, heads=heads,
        concat=True, add_self_loops=False, dropout=dropout
    ),
    ('molecule', 'rev_contains', 'ingredient'): GATConv(
        (-1, -1), hidden_channels // heads, heads=heads,
        concat=True, add_self_loops=False, dropout=dropout
    ),
    ('ingredient', 'co_occurs', 'ingredient'): GATConv(
        -1, hidden_channels // heads, heads=heads,
        concat=True, add_self_loops=False, dropout=dropout
    ),
    ('molecule', 'structurally_similar', 'molecule'): GATConv(
        -1, hidden_channels // heads, heads=heads,
        concat=True, add_self_loops=False, dropout=dropout
    ),
}, aggr='sum')
```

**Note:** `concat=True` with `heads=8` expands output to `hidden_channels // heads * heads = hidden_channels`. Use `hidden_channels // heads` as `out_channels` argument so post-concat dim equals `hidden_channels`. With `hidden=256` and `heads=8`, that is `out_channels=32` per head, `256` total after concat.

### Pattern 2: Per-Node-Type Linear Projections

**What:** Project each node type from its raw feature dimension to `hidden_channels` before the first GATConv layer. Required because ingredient nodes and molecule nodes have different feature vector sizes.

```python
# Source: https://pytorch-geometric.readthedocs.io/en/latest/notes/heterogeneous.html
import torch.nn as nn
from torch_geometric.nn import Linear

self.proj = nn.ModuleDict({
    node_type: Linear(-1, hidden_channels)
    for node_type in ['ingredient', 'molecule']
})

# In forward():
x_dict = {
    node_type: self.proj[node_type](x).relu()
    for node_type, x in x_dict.items()
}
```

### Pattern 3: Between-Layer BN + Dropout

**What:** Apply `BatchNorm1d` and dropout after each `HeteroConv` layer, per node type.

```python
# BN dict — one per node type per layer
self.bn = nn.ModuleDict({
    f'{node_type}_{layer_idx}': nn.BatchNorm1d(hidden_channels)
    for node_type in ['ingredient', 'molecule']
    for layer_idx in range(num_layers)
})

# In forward():
x_dict = {
    node_type: F.dropout(
        self.bn[f'{node_type}_{layer_idx}'](x).relu(),
        p=dropout, training=self.training
    )
    for node_type, x in x_dict.items()
}
```

**Pitfall:** `BatchNorm1d` breaks if batch size is 1 (single node). In full-graph training (no mini-batching), this never occurs — safe.

### Pattern 4: Final Projection to 128-dim Embedding Space

**What:** After the 3 GATConv layers, project each node type to the shared 128-dim embedding space via a final `Linear` layer.

```python
self.embed_proj = nn.ModuleDict({
    node_type: Linear(hidden_channels, embed_dim)
    for node_type in ['ingredient', 'molecule']
})

# In forward():
out = {
    node_type: self.embed_proj[node_type](x)
    for node_type, x in x_dict.items()
}
# out['ingredient'] shape: (num_ingredients, 128)
# out['molecule'] shape: (num_molecules, 128)
```

### Pattern 5: BCE Link Prediction Loss

**What:** Score edge pairs via dot product of embeddings; apply `BCEWithLogitsLoss`.

```python
from torch_geometric.utils import negative_sampling

def link_pred_loss(z_src, z_dst, pos_edge_index, num_nodes, device):
    """z_src, z_dst: (N, 128) embeddings of source/dest node types."""
    # Positive scores
    src_pos = z_src[pos_edge_index[0]]
    dst_pos = z_dst[pos_edge_index[1]]
    pos_scores = (src_pos * dst_pos).sum(dim=-1)  # (num_pos_edges,)

    # Negative sampling — same number as positive edges
    neg_edge_index = negative_sampling(
        edge_index=pos_edge_index,
        num_nodes=num_nodes,
        num_neg_samples=pos_edge_index.size(1),
    )
    src_neg = z_src[neg_edge_index[0]]
    dst_neg = z_dst[neg_edge_index[1]]
    neg_scores = (src_neg * dst_neg).sum(dim=-1)

    scores = torch.cat([pos_scores, neg_scores])
    labels = torch.cat([
        torch.ones(pos_scores.size(0)),
        torch.zeros(neg_scores.size(0)),
    ]).to(device)
    return F.binary_cross_entropy_with_logits(scores, labels)
```

**Note:** For bipartite edge types (ingredient→molecule), pass `num_nodes=(num_ingredients, num_molecules)` to `negative_sampling` — it interprets the tuple as bipartite dimensions.

### Pattern 6: InfoNCE Contrastive Loss

**What:** Maximize similarity between paired ingredient embeddings (positive pairs from molecular/recipe supervision) while pushing apart negatives in the batch.

```python
def info_nce_loss(z: torch.Tensor, pos_pairs: torch.Tensor, tau: float) -> torch.Tensor:
    """
    z: (N, 128) ingredient embeddings (L2-normalized before this call)
    pos_pairs: (2, K) index pairs of positive matches within the batch
    tau: temperature (use 0.15 per spec default)
    """
    # Normalize
    z = F.normalize(z, dim=-1)
    # Similarity matrix: (N, N)
    sim = torch.mm(z, z.T) / tau
    # Mask diagonal (self-similarity)
    mask = torch.eye(z.size(0), dtype=torch.bool, device=z.device)
    sim.masked_fill_(mask, float('-inf'))
    # Positive indices
    labels = pos_pairs[1]  # target indices for each anchor
    loss = F.cross_entropy(sim[pos_pairs[0]], labels)
    return loss
```

**Temperature note:** The spec sets `--tau 0.15` as the default (not 0.07). The food domain has high molecular overlap among negatives, so a looser temperature avoids over-penalizing false negatives.

### Pattern 7: Validation AUC

**What:** Evaluate on held-out edges from Phase 3's split; use sklearn `roc_auc_score`.

```python
from sklearn.metrics import roc_auc_score
import torch

@torch.no_grad()
def evaluate(model, data, val_edge_index, val_edge_label, device):
    model.eval()
    z_dict = model(data.x_dict, data.edge_index_dict)
    z_ing = z_dict['ingredient']

    src = z_ing[val_edge_index[0]]
    dst = z_ing[val_edge_index[1]]
    scores = (src * dst).sum(dim=-1).sigmoid().cpu().numpy()
    labels = val_edge_label.cpu().numpy()
    return roc_auc_score(labels, scores)
```

**Note:** `val_edge_index` and `val_edge_label` come directly from `val_data[('ingredient', 'co_occurs', 'ingredient')].edge_label_index` and `.edge_label` produced by Phase 3's `RandomLinkSplit`. The model's message-passing graph uses `train_data.edge_index_dict` (leakage-free because val/test edges were removed by Phase 3).

### Pattern 8: Cosine LR Schedule + Resume

```python
optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
    optimizer, T_max=args.epochs, eta_min=1e-6
)

# Resume: step scheduler to the saved epoch before training resumes
if args.resume:
    ckpt = torch.load(args.resume, map_location=device)
    model.load_state_dict(ckpt['model_state_dict'])
    optimizer.load_state_dict(ckpt['optimizer_state_dict'])
    scheduler.load_state_dict(ckpt['scheduler_state_dict'])
    start_epoch = ckpt['epoch'] + 1
    best_auc = ckpt.get('best_auc', 0.0)
```

### Pattern 9: Gradient Clipping (Unconditional)

```python
# After loss.backward(), before optimizer.step()
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
optimizer.step()
```

### Anti-Patterns to Avoid

- **Merging loss components:** Never `loss = alpha*mol + beta*rec + gamma*nce` and then log only `loss`. Always log mol, rec, nce separately first.
- **Self-loops on bipartite edges:** `GATConv` with `add_self_loops=True` (default) will crash on bipartite edge types where source and destination node counts differ. Always pass `add_self_loops=False`.
- **Integer `in_channels` on inter-type edges:** For edges connecting two different node types (ingredient→molecule), use `in_channels=(-1, -1)` not `-1`, so PyG knows to expect distinct source/dest feature dims.
- **Moving entire graph to MPS before embedding export:** For the final embedding export, call `model.cpu()` then forward-pass on CPU, then `model.to(device)` if more training is needed. This avoids a double-memory spike that causes OOM.
- **Mixing val edge leakage:** The `data.edge_index_dict` used for message passing during validation MUST be the training split's edge_index (not the full graph). Evaluating the model forward pass with val edges included in the message graph leaks information and inflates AUC.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Heterogeneous message passing dispatch | Custom for-loop over edge types | `HeteroConv` | Handles aggregation across multi-relation contributions automatically |
| Edge split with leakage prevention | Manual index filtering | `RandomLinkSplit` (Phase 3 artifact) | Zero-leakage guarantee is subtle; already done in Phase 3 |
| Negative edge sampling | Custom random index generator | `torch_geometric.utils.negative_sampling` | Handles bipartite num_nodes tuple; avoids sampling existing edges |
| AUC computation | Manual trapezoid integration | `sklearn.metrics.roc_auc_score` | Battle-tested; handles ties, edge cases |
| Gradient norm monitoring | Manual `torch.norm(p.grad)` loop | `torch.nn.utils.clip_grad_norm_` (returns norm before clipping) | Also clips in-place; use the return value to log gradient health |

**Key insight:** The heterogeneous graph machinery in PyG handles the complexity of dispatching messages correctly across node types. Hand-rolling this would require replicating PyG's internal `x_dict` / `edge_index_dict` dispatch logic, which has subtle aggregation behavior when multiple edge types target the same destination node type.

---

## Common Pitfalls

### Pitfall 1: GATConv Dimension Mismatch with concat=True

**What goes wrong:** Using `GATConv(-1, hidden, heads=8, concat=True)` produces output of dim `hidden * 8`, not `hidden`. If the next layer expects `hidden` channels, PyG's lazy initialization will silently use the wrong shape on first forward pass and crash on second.

**Why it happens:** `concat=True` (default) concatenates all head outputs. The output dimension is `out_channels * heads`.

**How to avoid:** Set `out_channels = hidden // heads` so that `out_channels * heads = hidden`. With `hidden=256, heads=8`: use `GATConv((-1,-1), 32, heads=8, concat=True)` → output is `256`.

**Warning signs:** `RuntimeError: mat1 and mat2 shapes cannot be multiplied` on the second GATConv layer or the final linear projection.

### Pitfall 2: `add_self_loops=True` on Bipartite Ingredient→Molecule Edges

**What goes wrong:** Crash during forward pass with a shape mismatch because self-loops are added to a bipartite graph where `num_src_nodes != num_dst_nodes`.

**Why it happens:** `GATConv` defaults to `add_self_loops=True`. For bipartite graphs, there is no well-defined notion of a self-loop.

**How to avoid:** Always pass `add_self_loops=False` for any edge type where source and destination node types differ.

**Warning signs:** `IndexError` or shape assertion error in the first forward pass during training.

### Pitfall 3: Negative Sampling Collides with Positive Edges

**What goes wrong:** `negative_sampling` with default settings may sample edges that already exist in the graph (false negatives). For a dense ingredient-ingredient co-occurrence graph, this inflates BCE loss.

**Why it happens:** PyG's `negative_sampling` uses rejection sampling but does not guarantee zero collision for dense graphs.

**How to avoid:** Pass the training `edge_index` as the `edge_index` argument to `negative_sampling` so it knows which edges already exist and avoids them. With a negative sampling ratio of 1.0 (equal positives and negatives), collision rate is low.

**Warning signs:** Validation AUC plateaus below 0.65 despite low training loss.

### Pitfall 4: Full-Graph Forward Pass Causes MPS OOM on Gradient Accumulation

**What goes wrong:** On large graphs (>500 ingredient nodes, >2000 molecule nodes), holding all intermediate activations for backprop at once exceeds MPS memory budget.

**Why it happens:** Full-graph training keeps all node embeddings in MPS memory simultaneously across all layers. With 8 attention heads and 256 hidden dim, the activation tensors scale with `num_nodes * hidden * heads`.

**How to avoid:** Call `torch.mps.empty_cache()` at the start of each epoch. If OOM persists, reduce `--hidden 128` or `--heads 4`. The memory estimate printed at training start (based on node counts) gives early warning.

**Warning signs:** `RuntimeError: MPS backend out of memory` after the first few epochs once the LR scheduler has lowered gradients to a stable range.

### Pitfall 5: InfoNCE Requires L2-Normalized Embeddings

**What goes wrong:** InfoNCE loss blows up (NaN or Inf) if embeddings are not L2-normalized before computing the similarity matrix. Without normalization, cosine similarity computed as dot product is unbounded.

**Why it happens:** The InfoNCE formulation assumes `||z|| = 1` for the similarity to be interpretable as cosine similarity. Unnormalized embeddings produce logits that exceed float32 range after division by small τ.

**How to avoid:** Call `F.normalize(z, dim=-1)` before the similarity matrix computation in the InfoNCE function. Do NOT normalize in the main model forward (embeddings exported to pkl should be raw, not normalized — scoring in Phase 5 uses raw dot products).

**Warning signs:** `nan` in loss after epoch 1–3; `nan` in AUC output.

### Pitfall 6: BatchNorm on Single-Node Types After Message Passing

**What goes wrong:** If a message-passing step produces a node type with only 1 node in the batch (e.g., a disconnected node type), `BatchNorm1d` divides by zero variance and produces NaN.

**Why it happens:** `BatchNorm1d` requires at least 2 samples in a batch to compute meaningful statistics. In full-graph training this does not occur (all nodes present), but guard against it if mini-batching is added later.

**How to avoid:** Use full-graph training (no mini-batching), which is the correct approach for this graph size. If mini-batching is needed later, switch to `LayerNorm` instead.

### Pitfall 7: Cosine Scheduler State Not Saved in Checkpoint

**What goes wrong:** Resume from checkpoint restores model and optimizer weights correctly but the LR jumps back to the initial value because the scheduler state was not saved.

**Why it happens:** `torch.save({'model_state_dict': ..., 'optimizer_state_dict': ...})` without `'scheduler_state_dict'`. The cosine schedule's internal `last_epoch` counter is lost.

**How to avoid:** Always include `'scheduler_state_dict': scheduler.state_dict()` in the checkpoint dict.

---

## Code Examples

### Full Training Script Skeleton

```python
# Source: derived from PyG docs + project patterns
import argparse, csv, pickle, time
from pathlib import Path
import torch, torch.nn.functional as F
from torch_geometric.nn import HeteroConv, GATConv, Linear
from sklearn.metrics import roc_auc_score
from tqdm import tqdm

def parse_args():
    p = argparse.ArgumentParser(description="Train FlavorGAT")
    p.add_argument('--epochs', type=int, default=200)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--hidden', type=int, default=256)
    p.add_argument('--embed', type=int, default=128)
    p.add_argument('--heads', type=int, default=8)
    p.add_argument('--dropout', type=float, default=0.3)
    p.add_argument('--alpha', type=float, default=0.4)
    p.add_argument('--beta', type=float, default=0.4)
    p.add_argument('--gamma', type=float, default=0.2)
    p.add_argument('--tau', type=float, default=0.15)
    p.add_argument('--mol-threshold', type=int, default=5)
    p.add_argument('--recipe-threshold', type=int, default=10)
    p.add_argument('--resume', type=str, default=None)
    return p.parse_args()

# Device detection
def get_device():
    if torch.backends.mps.is_available():
        return torch.device('mps')
    print("[WARNING] MPS not available — training on CPU (expect ~5x slower)")
    return torch.device('cpu')

# Per-epoch summary line example:
# Epoch 045/200 | AUC: 0.742↑ | Loss: 0.312 (mol=0.128, rec=0.115, nce=0.069) | LR: 8.3e-4
```

### Memory Estimate Before Training

```python
def estimate_memory_mb(num_ingredients, num_molecules, hidden_dim, heads):
    """Rough estimate of activation memory in MB for one forward pass."""
    # Node embeddings across 3 layers
    node_mem = (num_ingredients + num_molecules) * hidden_dim * 4 * 3  # float32, 3 layers
    # Attention weights: heads * num_edges * 4 bytes
    edge_mem = (num_ingredients * 10) * heads * 4  # estimate ~10 edges/node
    total_bytes = node_mem + edge_mem
    return total_bytes / (1024 ** 2)

# Print at training start:
est = estimate_memory_mb(num_ingredients, num_molecules, args.hidden, args.heads)
print(f"[INFO] Estimated activation memory: ~{est:.0f} MB (MPS unified pool)")
```

### OOM Handler

```python
try:
    train_one_epoch(...)
except RuntimeError as e:
    if "out of memory" in str(e).lower():
        if device.type == 'mps':
            torch.mps.empty_cache()
        print(
            f"[OOM] Training crashed at epoch {epoch}.\n"
            f"  Suggestions:\n"
            f"    --hidden 128  (currently {args.hidden})\n"
            f"    --heads 4     (currently {args.heads})\n"
        )
        sys.exit(1)
    raise
```

### Embedding Export

```python
@torch.no_grad()
def export_embeddings(model, data, ingredient_id_to_idx, embed_path, device):
    model.eval()
    # Move tensors to CPU to minimize peak memory
    data_cpu = data.to('cpu')
    model_cpu = model.to('cpu')
    z_dict = model_cpu(data_cpu.x_dict, data_cpu.edge_index_dict)
    z_ing = z_dict['ingredient'].numpy()  # (num_ingredients, 128)

    idx_to_id = {v: k for k, v in ingredient_id_to_idx.items()}
    embeddings = {idx_to_id[i]: z_ing[i] for i in range(len(z_ing))}

    Path(embed_path).parent.mkdir(parents=True, exist_ok=True)
    with open(embed_path, 'wb') as f:
        pickle.dump(embeddings, f)
    print(f"[INFO] Exported {len(embeddings)} embeddings to {embed_path}")
    model.to(device)  # restore device for any further use
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GATConv homogeneous only | HeteroConv wrapping GATConv | PyG 2.0+ | Multi-relational graphs without separate implementations per edge type |
| Manual heterogeneous dispatch | `to_hetero()` or explicit `HeteroConv` | PyG 2.0 | Two valid approaches; explicit HeteroConv is more transparent for custom architectures |
| Fixed-dim `in_channels=int` | Lazy init with `in_channels=-1` | PyG 2.x | Automatically infers input dims on first forward; removes manual dim tracking |
| `torch.no_grad()` decorator only | `@torch.no_grad()` + `.cpu()` before export | Best practice 2023+ | Avoids MPS peak-memory double spike on large embedding export |

**Deprecated/outdated:**
- `add_self_loops=True` (default) on bipartite edges: crashes on heterogeneous graphs — always override to `False`
- InfoNCE temperature τ=0.07 (SimCLR default): too tight for food domain where many negatives share flavor compounds; use 0.10–0.20

---

## Open Questions

1. **Does `torch.compile()` help on MPS with PyG HeteroConv?**
   - What we know: `torch.compile` on MPS falls back to CPU for unsupported ops or runs as unfused Metal kernels (2025 state)
   - What's unclear: Whether PyG's scatter operations in HeteroConv are compilable on MPS 2.6
   - Recommendation: Attempt `model = torch.compile(model)` after model initialization; if forward pass raises `RuntimeError` or shows no speedup, disable it (this is in Claude's discretion per CONTEXT.md)

2. **Positive pair construction for InfoNCE**
   - What we know: InfoNCE needs explicit positive pairs, not just random in-batch pairs
   - What's unclear: Whether to use the same positive edges as the BCE objectives, or construct augmented views (random node feature masking)
   - Recommendation: Use the molecular BCE positive edges as InfoNCE positives (ingredient pairs sharing >5 molecules are semantically similar). This aligns the contrastive objective with the molecular supervision signal.

3. **CSV log overwrite vs append on re-run**
   - What we know: CONTEXT.md flags this as Claude's discretion
   - Recommendation: Overwrite (not append) — a re-run from scratch should produce a clean training log. For resume runs, append from the resume epoch. Implement by opening the file in `'w'` mode at training start unless `--resume` is active, in which case open in `'a'` mode.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.* |
| Config file | none (no pytest.ini — uses default discovery) |
| Quick run command | `pytest tests/test_model_training.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODEL-01 | FlavorGAT forward pass produces correct output shape (N_ingredients, 128) | unit | `pytest tests/test_model_training.py::test_gat_output_shape -x` | ❌ Wave 0 |
| MODEL-02 | GATConv layers have add_self_loops=False | unit | `pytest tests/test_model_training.py::test_no_self_loops -x` | ❌ Wave 0 |
| MODEL-03 | BatchNorm and dropout are present in model architecture | unit | `pytest tests/test_model_training.py::test_bn_dropout_present -x` | ❌ Wave 0 |
| MODEL-04 | Molecular BCE loss computes without error on valid input | unit | `pytest tests/test_model_training.py::test_molecular_loss -x` | ❌ Wave 0 |
| MODEL-05 | Recipe BCE loss computes without error on valid input | unit | `pytest tests/test_model_training.py::test_recipe_loss -x` | ❌ Wave 0 |
| MODEL-06 | InfoNCE loss returns scalar, logged separately from combined loss | unit | `pytest tests/test_model_training.py::test_infonce_loss -x` | ❌ Wave 0 |
| MODEL-07 | Combined loss = alpha*mol + beta*rec + gamma*nce within tolerance | unit | `pytest tests/test_model_training.py::test_combined_loss_formula -x` | ❌ Wave 0 |
| MODEL-08 | Checkpoint saved when AUC improves; not saved when AUC declines | unit | `pytest tests/test_model_training.py::test_checkpoint_save_on_improvement -x` | ❌ Wave 0 |
| MODEL-09 | ingredient_embeddings.pkl contains correct keys and 128-dim vectors | integration | `pytest tests/test_model_training.py::test_embedding_export -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_model_training.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_model_training.py` — covers MODEL-01 through MODEL-09 with synthetic mini-graph fixtures
- [ ] Shared fixture: small `HeteroData` object (10 ingredient nodes, 50 molecule nodes, all 3 edge types) to avoid loading the real `graph/hetero_data.pt` in unit tests

*(All test infrastructure gaps are in a single new file; pytest framework is already installed)*

---

## Sources

### Primary (HIGH confidence)

- [PyG HeteroConv docs](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.conv.HeteroConv.html) — HeteroConv API, aggr parameter, ModuleDict pattern
- [PyG GATConv docs](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.conv.GATConv.html) — in_channels tuple, add_self_loops, heads/concat behavior
- [PyG Heterogeneous Graph Learning docs](https://pytorch-geometric.readthedocs.io/en/latest/notes/heterogeneous.html) — per-node-type linear projections, HeteroConv + GATConv pattern
- [PyG RandomLinkSplit docs](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.transforms.RandomLinkSplit.html) — edge_types, rev_edge_types, disjoint_train_ratio
- [PyTorch CosineAnnealingLR docs](https://docs.pytorch.org/docs/stable/generated/torch.optim.lr_scheduler.CosineAnnealingLR.html) — T_max parameter, eta_min
- [sklearn roc_auc_score docs](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html) — binary classification AUC

### Secondary (MEDIUM confidence)

- [PyTorch MPS backend notes](https://docs.pytorch.org/docs/stable/notes/mps.html) — `torch.mps.empty_cache()` availability confirmed
- [Apple MPS PyTorch blog](https://pytorch.org/blog/introducing-accelerated-pytorch-training-on-mac/) — unified memory architecture, MPS availability check
- [PyG negative_sampling docs](https://pytorch-geometric.readthedocs.io/en/latest/modules/utils.html) — bipartite num_nodes tuple support

### Tertiary (LOW confidence)

- torch.compile on MPS performance (WebSearch 2025) — confirms complex fusions fall back to CPU; recommend testing at runtime

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries pinned in environment.yml, APIs verified in official docs
- Architecture: HIGH — HeteroConv + GATConv patterns confirmed in PyG docs; bipartite rules verified
- InfoNCE implementation: HIGH — standard formulation verified; temperature choice MEDIUM (project-specific reasoning)
- MPS OOM handling: MEDIUM — `torch.mps.empty_cache()` confirmed; exact memory thresholds depend on runtime graph size
- Pitfalls: HIGH — all pitfalls verified against official PyG docs or PyTorch docs

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (PyG 2.7 API is stable; MPS support actively improving but no breaking changes expected)
