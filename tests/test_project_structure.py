"""
Directory existence tests for the project skeleton (ENV-04).

These tests verify that all required directories are present on disk.
They should PASS immediately after environment setup (Task 1 of Plan 01-01).
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def test_directories():
    """Verify that all required project directories exist.

    Covers ENV-04 (project directory structure).
    All directories are created by Plan 01-01 Task 1 with .gitkeep files.
    """
    required_dirs = [
        "data/raw",
        "data/processed",
        "graph",
        "model/embeddings",
        "scoring",
        "app",
        "logs",
        "tests",
    ]
    missing = []
    for d in required_dirs:
        path = PROJECT_ROOT / d
        if not path.is_dir():
            missing.append(d)

    assert not missing, (
        f"Missing required directories: {missing}\n"
        "Run: mkdir -p data/raw data/processed graph model/embeddings scoring app logs tests"
    )
