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
def upload(files: dict[str, bytes]):
    """Write pre-read file bytes into the volume."""
    for volume_path, data in files.items():
        dst = Path("/data") / volume_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        print(f"  OK: /data/{volume_path} ({len(data) / 1e6:.1f} MB)")
    volume.commit()
    print("Volume committed.")


@app.local_entrypoint()
def main():
    # Read files locally before sending to the remote container
    files: dict[str, bytes] = {}
    for local_path, volume_path in LOCAL_FILES:
        src = Path(local_path)
        if not src.exists():
            print(f"  SKIP (not found): {local_path}")
            continue
        files[volume_path] = src.read_bytes()
        print(f"  Read: {local_path} ({len(files[volume_path]) / 1e6:.1f} MB)")

    if not files:
        print("No files to upload.")
        return

    upload.remote(files)
