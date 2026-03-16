"""
modal_score.py — Run compute_scores.py on Modal, download scored_pairs.pkl.

Usage:
    modal run modal_score.py          # recompute all pair scores
    modal run modal_score.py --force  # recompute even if pkl already exists

Output written back to:
    scoring/scored_pairs.pkl
"""

import sys
from pathlib import Path

import modal

_TORCH = "2.6.0"
_CUDA  = "cu124"
_PYG_WHEEL = f"https://data.pyg.org/whl/torch-{_TORCH}+{_CUDA}.html"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        f"torch=={_TORCH}",
        "torchvision",
        "torchaudio",
        extra_options=f"--index-url https://download.pytorch.org/whl/{_CUDA}",
    )
    .pip_install(
        "torch_geometric==2.7.*",
        "torch_scatter",
        "torch_sparse",
        "torch_cluster",
        extra_options=f"--find-links {_PYG_WHEEL}",
    )
    .pip_install("numpy", "pandas", "tqdm", "scikit-learn", "rdkit")
    .add_local_dir("model",   remote_path="/root/flavor-network/model")
    .add_local_dir("graph",   remote_path="/root/flavor-network/graph")
    .add_local_dir("scoring", remote_path="/root/flavor-network/scoring")
)

app = modal.App("flavor-gat-scoring", image=image)

@app.function(timeout=600)
def compute_scores(force: bool) -> bytes:
    import os
    import sys

    os.chdir("/root/flavor-network")
    sys.path.insert(0, "/root/flavor-network")

    from scoring.compute_scores import run_scoring
    run_scoring(force=force)

    with open("scoring/scored_pairs.pkl", "rb") as f:
        return f.read()


@app.local_entrypoint()
def main():
    force = "--force" in sys.argv

    print("Computing all-pair surprise scores on Modal...")
    pkl_bytes = compute_scores.remote(force=force)

    Path("scoring/scored_pairs.pkl").write_bytes(pkl_bytes)
    print(f"✓ Saved scoring/scored_pairs.pkl ({len(pkl_bytes) / 1e6:.1f} MB)")
