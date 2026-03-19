"""
One-off script to populate the flavornet-data Modal Volume with local artifacts.
Run: modal run scripts/upload_volume.py
"""
import modal
from pathlib import Path

app = modal.App("flavornet-upload")
volume = modal.Volume.from_name("flavornet-data", create_if_missing=True)

LOCAL_FILES = [
    # (local_path, volume_path)
    ("model/embeddings/ingredient_embeddings.pkl", "ingredient_embeddings.pkl"),
    ("scoring/scored_pairs.pkl", "scored_pairs.pkl"),
    ("data/processed/ingredient_molecule.parquet", "ingredient_molecule.parquet"),
    ("logs/training_metadata.json", "training_metadata.json"),
    ("feedback.csv", "feedback.csv"),
    ("data/processed/hetero_data.pt", "graph/hetero_data.pt"),
    ("data/processed/val_edges.pt", "graph/val_edges.pt"),
    ("model/checkpoints/best_model.pt", "model/checkpoints/best_model.pt"),
    ("model/replay_buffer.pkl", "model/replay_buffer.pkl"),
    ("data/raw/molecules.csv", "molecules.csv"),
]


@app.function(volumes={"/data": volume})
def upload():
    import shutil
    import os
    for local_path, volume_path in LOCAL_FILES:
        src = Path(local_path)
        if not src.exists():
            print(f"  SKIP (not found): {local_path}")
            continue
        dst = Path("/data") / volume_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  OK: {local_path} -> /data/{volume_path}")
    volume.commit()
    print("Volume committed.")


@app.local_entrypoint()
def main():
    upload.remote()
