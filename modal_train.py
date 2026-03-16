"""
modal_train.py — Run FlavorGAT training on Modal (GPU cloud).

Usage:
    modal run modal_train.py                      # default 200 epochs on A10G
    modal run modal_train.py --epochs 50          # quick smoke test
    modal run modal_train.py --gpu T4             # cheaper GPU

Outputs are written back to:
    model/checkpoints/best_model.pt
    model/embeddings/ingredient_embeddings.pkl
    logs/training_metrics.csv
"""

import argparse
import sys
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Parse flags before Modal sees sys.argv
# ---------------------------------------------------------------------------

_p = argparse.ArgumentParser(add_help=False)
_p.add_argument("--epochs", type=int, default=200)
_p.add_argument("--gpu", type=str, default="A10G")
_p.add_argument("--hidden", type=int, default=128)
_p.add_argument("--heads", type=int, default=4)
_p.add_argument("--alpha", type=float, default=0.4)
_p.add_argument("--beta", type=float, default=0.4)
_p.add_argument("--gamma", type=float, default=0.2)
_p.add_argument("--tau", type=float, default=0.15)
_p.add_argument("--mol-threshold", type=int, default=0)
_p.add_argument("--recipe-threshold", type=int, default=0)
_ARGS, _ = _p.parse_known_args()

# ---------------------------------------------------------------------------
# Image — bake in CUDA torch, PyG, and all local source
# ---------------------------------------------------------------------------

_TORCH = "2.6.0"
_CUDA  = "cu124"
_PYG_WHEEL = f"https://data.pyg.org/whl/torch-{_TORCH}+{_CUDA}.html"

image = (
    modal.Image.debian_slim(python_version="3.12")
    # 1. CUDA PyTorch
    .pip_install(
        f"torch=={_TORCH}",
        "torchvision",
        "torchaudio",
        extra_options=f"--index-url https://download.pytorch.org/whl/{_CUDA}",
    )
    # 2. PyTorch Geometric + C++ extensions
    .pip_install(
        "torch_geometric==2.7.*",
        "torch_scatter",
        "torch_sparse",
        "torch_cluster",
        extra_options=f"--find-links {_PYG_WHEEL}",
    )
    # 3. Other deps
    .pip_install("numpy", "pandas", "tqdm", "scikit-learn", "rdkit")
    # 4. Project source code
    .add_local_dir("model",  remote_path="/root/flavor-network/model")
    .add_local_dir("graph",  remote_path="/root/flavor-network/graph")
    .add_local_dir("logs",   remote_path="/root/flavor-network/logs")
)

app = modal.App("flavor-gat-training", image=image)

# ---------------------------------------------------------------------------
# Remote training function — returns output files as raw bytes
# ---------------------------------------------------------------------------

@app.function(
    gpu=_ARGS.gpu,
    timeout=7200,
)
def train_remote(
    epochs, hidden, heads, alpha, beta, gamma, tau, mol_threshold, recipe_threshold
):
    import os
    import sys
    import torch

    os.chdir("/root/flavor-network")
    sys.path.insert(0, "/root/flavor-network")

    assert torch.cuda.is_available(), "No CUDA GPU detected"
    print(f"[Modal] GPU: {torch.cuda.get_device_name(0)}")

    # Disable torch.compile — it pre-allocates ~17 GB of fragmented memory
    # on the first forward pass, leaving no room for activations.
    torch.compile = lambda model, *a, **kw: model

    # Reduce allocator fragmentation
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    # patch sys.argv for parse_args()
    sys.argv = [
        "train_gat.py",
        "--epochs", str(epochs),
        "--hidden", str(hidden),
        "--heads", str(heads),
        "--alpha", str(alpha),
        "--beta", str(beta),
        "--gamma", str(gamma),
        "--tau", str(tau),
        "--mol-threshold", str(mol_threshold),
        "--recipe-threshold", str(recipe_threshold),
    ]

    import model.train_gat as train_gat
    train_gat.main()

    # Return output files as bytes so we can write them locally
    outputs = {}
    for key, path in {
        "best_model.pt":             "model/checkpoints/best_model.pt",
        "ingredient_embeddings.pkl": "model/embeddings/ingredient_embeddings.pkl",
        "training_metrics.csv":      "logs/training_metrics.csv",
    }.items():
        if os.path.exists(path):
            with open(path, "rb") as f:
                outputs[key] = f.read()
            print(f"[Modal] Captured {path} ({len(outputs[key]) / 1e6:.1f} MB)")
        else:
            print(f"[Modal] WARNING: {path} not found after training")

    return outputs


# ---------------------------------------------------------------------------
# Local entrypoint
# ---------------------------------------------------------------------------

@app.local_entrypoint()
def main():
    print(f"Launching FlavorGAT on Modal ({_ARGS.gpu}, {_ARGS.epochs} epochs)...")

    outputs = train_remote.remote(
        epochs=_ARGS.epochs,
        hidden=_ARGS.hidden,
        heads=_ARGS.heads,
        alpha=_ARGS.alpha,
        beta=_ARGS.beta,
        gamma=_ARGS.gamma,
        tau=_ARGS.tau,
        mol_threshold=_ARGS.mol_threshold,
        recipe_threshold=_ARGS.recipe_threshold,
    )

    dest_map = {
        "best_model.pt":             "model/checkpoints/best_model.pt",
        "ingredient_embeddings.pkl": "model/embeddings/ingredient_embeddings.pkl",
        "training_metrics.csv":      "logs/training_metrics.csv",
    }

    for key, local_path in dest_map.items():
        if key in outputs:
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            Path(local_path).write_bytes(outputs[key])
            print(f"Saved → {local_path}")
        else:
            print(f"WARNING: {key} was not returned (check Modal logs)")

    print("\nDone.")
