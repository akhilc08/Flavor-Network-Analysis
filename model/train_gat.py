"""
train_gat.py — Full training script for FlavorGAT.

Wires FlavorGAT and loss functions into a complete training loop with:
  - argparse configurability (12 hyperparameter flags)
  - checkpoint management (best + periodic every 50 epochs)
  - CSV logging (per-epoch metrics)
  - ingredient embedding export

Usage:
    python model/train_gat.py --help
    python model/train_gat.py --epochs 200 --lr 1e-3

Exports (importable by tests):
    export_embeddings
    save_checkpoint
    save_checkpoint_if_improved
"""

import argparse
import csv
import pickle
import sys
import time
from pathlib import Path

# Allow `python model/train_gat.py` invocation from project root without
# needing PYTHONPATH — insert project root into sys.path if not already present.
_PROJECT_ROOT = str(Path(__file__).parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import torch
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score
from tqdm import tqdm

from model.gat_model import FlavorGAT
from model.losses import molecular_bce_loss, recipe_bce_loss, info_nce_loss, combined_loss


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse all training hyperparameters. Names are locked decisions."""
    parser = argparse.ArgumentParser(
        description="Train FlavorGAT heterogeneous graph attention network for ingredient pairing"
    )
    parser.add_argument("--epochs", type=int, default=200, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=1e-3, help="Initial learning rate")
    parser.add_argument("--hidden", type=int, default=256, help="Hidden channels in GATConv layers")
    parser.add_argument("--embed", type=int, default=128, help="Embedding dimension for output")
    parser.add_argument("--heads", type=int, default=8, help="Number of attention heads")
    parser.add_argument("--dropout", type=float, default=0.3, help="Dropout probability")
    parser.add_argument("--alpha", type=float, default=0.4, help="Weight for molecular BCE loss")
    parser.add_argument("--beta", type=float, default=0.4, help="Weight for recipe BCE loss")
    parser.add_argument("--gamma", type=float, default=0.2, help="Weight for InfoNCE loss")
    parser.add_argument("--tau", type=float, default=0.15, help="InfoNCE temperature")
    parser.add_argument("--mol-threshold", type=int, default=5, dest="mol_threshold",
                        help="Min shared molecules to count as a positive molecular edge")
    parser.add_argument("--recipe-threshold", type=int, default=10, dest="recipe_threshold",
                        help="Min recipe co-occurrences to count as a positive recipe edge")
    parser.add_argument("--resume", type=str, default=None,
                        help="Path to checkpoint .pt file to resume training from")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------

def get_device() -> torch.device:
    """Return CUDA > MPS > CPU, with a warning if falling back to CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    print("[WARNING] No GPU found — training on CPU (expect ~5x slower)")
    return torch.device("cpu")


# ---------------------------------------------------------------------------
# Memory estimate
# ---------------------------------------------------------------------------

def estimate_memory_mb(
    num_ingredients: int,
    num_molecules: int,
    hidden_dim: int,
    heads: int,
) -> float:
    """Rough forward-pass memory estimate in MB.

    Accounts for node features + intermediate activations per layer.
    """
    bytes_per_float = 4
    # Node hidden states: 3 layers × (N_ing + N_mol) × hidden_dim
    node_bytes = 3 * (num_ingredients + num_molecules) * hidden_dim * bytes_per_float
    # Attention coefficients: rough upper bound
    attn_bytes = heads * (num_ingredients + num_molecules) * hidden_dim * bytes_per_float
    total_mb = (node_bytes + attn_bytes) / (1024 ** 2)
    return total_mb


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------

def load_graph(graph_path: str = "graph/hetero_data.pt"):
    """Load the heterogeneous graph artifact produced by Phase 3.

    Handles both dict-style and attribute-style access to the loaded payload.
    Exits cleanly if the file is missing.

    Returns:
        (train_data, val_data, ingredient_id_to_idx, molecule_id_to_idx)
    """
    path = Path(graph_path)
    if not path.exists():
        print(
            f"[ERROR] Graph artifact not found: {graph_path}\n"
            "  Run `python run_pipeline.py` (Stages 1-4) to produce graph/hetero_data.pt."
        )
        sys.exit(1)

    payload = torch.load(graph_path, weights_only=False)

    # Support both dict-style and attribute-style access
    def _get(obj, key):
        if isinstance(obj, dict):
            return obj[key]
        return getattr(obj, key)

    train_data = _get(payload, "graph")
    val_data = _get(payload, "val_data")
    ingredient_id_to_idx = _get(payload, "ingredient_id_to_idx")
    molecule_id_to_idx = _get(payload, "molecule_id_to_idx")

    return train_data, val_data, ingredient_id_to_idx, molecule_id_to_idx


# ---------------------------------------------------------------------------
# Positive edge index builder
# ---------------------------------------------------------------------------

def build_pos_edge_index(
    data,
    edge_type: tuple,
    threshold: int,
    threshold_attr: str = "edge_attr",
) -> torch.Tensor:
    """Extract positive edge indices from training data based on a threshold.

    If edge_attr is present, returns edges where edge_attr > threshold.
    Falls back to returning ALL edges in the edge type if edge_attr is absent.

    Args:
        data: HeteroData training graph
        edge_type: (src_type, relation, dst_type) tuple
        threshold: minimum attribute value to count as positive
        threshold_attr: attribute name to filter on (usually 'edge_attr')

    Returns:
        (2, K) LongTensor of positive edge indices
    """
    edge_store = data[edge_type]
    edge_index = edge_store.edge_index

    if hasattr(edge_store, threshold_attr):
        attr = getattr(edge_store, threshold_attr)
        # edge_attr may be 2-D (E, 1) or 1-D (E,)
        if attr.dim() == 2:
            attr = attr.squeeze(1)
        mask = attr > threshold
        return edge_index[:, mask]
    else:
        print(
            f"[WARNING] No '{threshold_attr}' on {edge_type} — using all edges as positives"
        )
        return edge_index


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

@torch.no_grad()
def evaluate(model, train_data, val_data, device) -> float:
    """Compute validation AUC using sklearn.roc_auc_score.

    Uses train_data.edge_index_dict for message passing (leakage-free).
    Gets val edge_label_index and edge_label from val_data['ingredient','co_occurs','ingredient'].

    Returns:
        float AUC (0.5 if labels are all one class)
    """
    model.eval()

    # Forward pass uses train graph structure (no val edges in message passing)
    train_data_dev = train_data.to(device)
    z_dict = model(train_data_dev.x_dict, train_data_dev.edge_index_dict)
    z_ing = z_dict["ingredient"]

    # Validation edges: edge_label_index and edge_label from val_data
    val_co = val_data[("ingredient", "co_occurs", "ingredient")]
    edge_label_index = val_co.edge_label_index.to(device)
    edge_label = val_co.edge_label

    # Score each validation edge via dot product
    src_emb = z_ing[edge_label_index[0]]
    dst_emb = z_ing[edge_label_index[1]]
    scores = (src_emb * dst_emb).sum(dim=-1).cpu().numpy()
    labels = edge_label.cpu().numpy()

    # Guard against degenerate single-class label case
    if labels.min() == labels.max():
        return 0.5

    return float(roc_auc_score(labels, scores))


# ---------------------------------------------------------------------------
# Embedding export
# ---------------------------------------------------------------------------

@torch.no_grad()
def export_embeddings(
    model,
    data,
    ingredient_id_to_idx: dict,
    embed_path,
    device,
) -> None:
    """Export ingredient embeddings to a pickle file (CPU-first to avoid OOM).

    Args:
        model: trained FlavorGAT
        data: HeteroData (train graph — full node features present)
        ingredient_id_to_idx: dict mapping ingredient ID string -> integer index
        embed_path: output path (str or Path)
        device: current training device (model will be temporarily moved to CPU)
    """
    model.eval()
    data_cpu = data.to("cpu")
    model_cpu = model.to("cpu")
    z_dict = model_cpu(data_cpu.x_dict, data_cpu.edge_index_dict)
    z_ing = z_dict["ingredient"].numpy()

    idx_to_id = {v: k for k, v in ingredient_id_to_idx.items()}
    embeddings = {idx_to_id[i]: z_ing[i] for i in range(len(z_ing))}

    Path(embed_path).parent.mkdir(parents=True, exist_ok=True)
    with open(embed_path, "wb") as f:
        pickle.dump(embeddings, f)

    # Move model back to original device
    model.to(device)


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def save_checkpoint(state_dict: dict, path) -> None:
    """Save a checkpoint dict to path. Creates parent directories as needed."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(state_dict, path)


def save_checkpoint_if_improved(
    state_dict: dict,
    current_auc: float,
    best_auc: float,
    path,
) -> bool:
    """Save checkpoint only when current_auc > best_auc.

    Args:
        state_dict: checkpoint dict to save
        current_auc: newly computed validation AUC
        best_auc: best AUC seen so far
        path: output path for the checkpoint

    Returns:
        True if checkpoint was saved, False otherwise.
    """
    if current_auc > best_auc:
        save_checkpoint(state_dict, path)
        return True
    return False


# ---------------------------------------------------------------------------
# Main training loop
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point: parse args, load graph, train FlavorGAT end-to-end."""
    args = parse_args()
    start_time = time.time()

    # Echo all hyperparameters
    print("=" * 60)
    print("FlavorGAT Training Configuration")
    print("=" * 60)
    for key, val in vars(args).items():
        print(f"  {key:20s}: {val}")
    print("=" * 60)

    device = get_device()
    print(f"[INFO] Device: {device}")

    # Load graph artifact
    train_data, val_data, ingredient_id_to_idx, molecule_id_to_idx = load_graph(
        "graph/hetero_data.pt"
    )

    num_ingredients = train_data["ingredient"].x.size(0)
    num_molecules = train_data["molecule"].x.size(0)
    mem_mb = estimate_memory_mb(num_ingredients, num_molecules, args.hidden, args.heads)
    print(f"[INFO] Estimated forward-pass memory: {mem_mb:.1f} MB")
    print(f"[INFO] Graph: {num_ingredients} ingredients, {num_molecules} molecules")

    # Precompute positive edge indices
    edge_type = ("ingredient", "co_occurs", "ingredient")
    mol_pos_edges = build_pos_edge_index(
        train_data, edge_type, args.mol_threshold
    ).to(device)
    rec_pos_edges = build_pos_edge_index(
        train_data, edge_type, args.recipe_threshold
    ).to(device)

    # Build InfoNCE positive pairs from mol_pos_edges (same as mol_pos_edges)
    nce_pos_pairs = mol_pos_edges  # shape (2, K)

    # Instantiate model
    model = FlavorGAT(
        hidden_channels=args.hidden,
        embed_dim=args.embed,
        heads=args.heads,
        dropout=args.dropout,
    ).to(device)

    # Optionally attempt torch.compile
    try:
        model = torch.compile(model)
        print("[INFO] torch.compile enabled")
    except RuntimeError:
        print("[INFO] torch.compile disabled (unsupported on this backend)")

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=1e-6
    )

    start_epoch = 0
    best_auc = 0.0
    best_epoch = 0

    # Resume from checkpoint if requested
    if args.resume is not None:
        ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        start_epoch = ckpt["epoch"] + 1
        best_auc = ckpt["best_auc"]
        print(f"[INFO] Resumed from {args.resume} at epoch {ckpt['epoch']}, best AUC {best_auc:.4f}")

    # Create output directories
    Path("model/checkpoints").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)

    # Open CSV log
    csv_mode = "a" if args.resume is not None else "w"
    csv_path = Path("logs/training_metrics.csv")
    csv_file = open(csv_path, csv_mode, newline="")
    csv_fields = ["epoch", "mol_loss", "rec_loss", "nce_loss", "total_loss", "val_auc", "lr"]
    writer = csv.DictWriter(csv_file, fieldnames=csv_fields)
    if csv_mode == "w":
        writer.writeheader()

    # Move training data to device
    train_data = train_data.to(device)

    # Training loop
    pbar = tqdm(range(start_epoch, args.epochs), desc="Training", unit="epoch")
    for epoch in pbar:
        try:
            model.train()

            z_dict = model(train_data.x_dict, train_data.edge_index_dict)
            z_ing = z_dict["ingredient"]

            mol_loss = molecular_bce_loss(
                z_ing, z_ing, mol_pos_edges, num_nodes=num_ingredients, device=str(device)
            )
            rec_loss = recipe_bce_loss(
                z_ing, z_ing, rec_pos_edges, num_nodes=num_ingredients, device=str(device)
            )
            nce_loss = info_nce_loss(z_ing, nce_pos_pairs, tau=args.tau)
            loss = combined_loss(mol_loss, rec_loss, nce_loss, args.alpha, args.beta, args.gamma)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            val_auc = evaluate(model, train_data, val_data, device)
            current_lr = scheduler.get_last_lr()[0]

            # AUC trend arrow
            if val_auc > best_auc:
                arrow = "↑"
            elif val_auc < best_auc - 0.001:
                arrow = "↓"
            else:
                arrow = "="

            # Per-epoch console log (locked format)
            epoch_str = f"{epoch+1:03d}/{args.epochs}"
            print(
                f"Epoch {epoch_str} | "
                f"AUC: {val_auc:.3f}{arrow} | "
                f"Loss: {loss.item():.3f} "
                f"(mol={mol_loss.item():.3f}, rec={rec_loss.item():.3f}, nce={nce_loss.item():.3f}) | "
                f"LR: {current_lr:.2e}",
                flush=True,
            )

            # CSV row
            writer.writerow({
                "epoch": epoch + 1,
                "mol_loss": mol_loss.item(),
                "rec_loss": rec_loss.item(),
                "nce_loss": nce_loss.item(),
                "total_loss": loss.item(),
                "val_auc": val_auc,
                "lr": current_lr,
            })
            csv_file.flush()

            # Best checkpoint
            ckpt_state = {
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "epoch": epoch,
                "best_auc": best_auc,
            }
            if val_auc > best_auc:
                best_auc = val_auc
                best_epoch = epoch + 1
                save_checkpoint(ckpt_state, "model/checkpoints/best_model.pt")

            # Periodic checkpoint every 50 epochs
            if (epoch + 1) % 50 == 0:
                save_checkpoint(ckpt_state, f"model/checkpoints/epoch_{epoch+1:03d}.pt")

        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                if device.type == "mps":
                    torch.mps.empty_cache()
                print(
                    f"[OOM] Training crashed at epoch {epoch}.\n"
                    "  Try: --hidden 128 or --heads 4"
                )
                sys.exit(1)
            raise

    csv_file.close()

    elapsed = time.time() - start_time
    print(
        f"Training complete | Best AUC: {best_auc:.4f} @ epoch {best_epoch} | "
        f"Time: {elapsed:.1f}s | Checkpoint: model/checkpoints/best_model.pt"
    )

    # Export embeddings (CPU-first to avoid MPS double-spike OOM)
    export_embeddings(
        model,
        train_data,
        ingredient_id_to_idx,
        "model/embeddings/ingredient_embeddings.pkl",
        device,
    )
    print("[INFO] Embeddings exported to model/embeddings/ingredient_embeddings.pkl")


if __name__ == "__main__":
    main()
