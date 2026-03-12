"""
Smoke tests for the conda+pip hybrid environment (ENV-01, ENV-02, ENV-03).

These tests verify that the required packages are importable and that the
MPS backend is available on Apple Silicon. They will PASS once the environment
has been set up with: conda env create -f environment.yml
"""
import sys
import pytest


def test_imports():
    """Verify that all required packages are importable in the active environment.

    Covers ENV-01 (Python packages) and ENV-03 (GNN libraries).
    """
    import torch  # noqa: F401
    import torch_geometric  # noqa: F401
    from rdkit import Chem  # noqa: F401


def test_mps_available():
    """Verify that the MPS (Metal Performance Shaders) backend is available.

    Covers ENV-02 (Apple Silicon GPU acceleration).
    Skipped automatically on non-Darwin platforms.
    """
    if sys.platform != "darwin":
        pytest.skip("MPS is only available on macOS (Apple Silicon)")
    import torch
    assert torch.backends.mps.is_available(), (
        "MPS backend not available — ensure you are running on Apple Silicon "
        "and that PyTorch was installed with MPS support (pip wheel, not conda channel)."
    )


def test_versions():
    """Verify that installed package versions match the project spec.

    Covers ENV-01 version pinning requirements.
    """
    import torch
    from rdkit import __version__ as rdkit_version

    assert torch.__version__.startswith("2.6"), (
        f"Expected torch 2.6.x, got {torch.__version__}"
    )
    assert rdkit_version.startswith("2025"), (
        f"Expected rdkit 2025.x, got {rdkit_version}"
    )
