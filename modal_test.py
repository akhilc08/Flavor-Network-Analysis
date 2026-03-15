"""
modal_test.py — Run the pytest suite on Modal to avoid local memory spikes.

Usage:
    modal run modal_test.py                     # full test suite
    modal run modal_test.py -- -k scoring       # filter by keyword
    modal run modal_test.py -- -v tests/test_scoring.py  # specific file
    modal run modal_test.py -- --co             # collect-only (dry run)

All pytest args after -- are passed through to pytest.
"""

import sys
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Image — same stack as modal_train.py (CPU-only, no GPU needed for tests)
# ---------------------------------------------------------------------------

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
    .pip_install(
        "numpy", "pandas", "tqdm", "scikit-learn", "rdkit",
        "pytest", "pytest-timeout",
        "streamlit", "plotly", "pyvis", "anthropic",
    )
    # Bake in all project source + data artifacts
    .add_local_dir("model",   remote_path="/root/flavor-network/model")
    .add_local_dir("graph",   remote_path="/root/flavor-network/graph")
    .add_local_dir("scoring", remote_path="/root/flavor-network/scoring")
    .add_local_dir("data",    remote_path="/root/flavor-network/data")
    .add_local_dir("tests",   remote_path="/root/flavor-network/tests")
    .add_local_dir("logs",    remote_path="/root/flavor-network/logs")
    .add_local_dir("app",     remote_path="/root/flavor-network/app")
)

app = modal.App("flavor-gat-tests", image=image)

# ---------------------------------------------------------------------------
# Remote test runner — streams output, returns exit code
# ---------------------------------------------------------------------------

@app.function(
    timeout=900,  # 15 min max
)
def run_tests(pytest_args: list[str]) -> int:
    import os
    import sys
    import subprocess

    os.chdir("/root/flavor-network")
    sys.path.insert(0, "/root/flavor-network")

    cmd = ["python", "-m", "pytest"] + pytest_args + ["-v", "--tb=short"]
    result = subprocess.run(cmd, cwd="/root/flavor-network")
    return result.returncode


# ---------------------------------------------------------------------------
# Local entrypoint
# ---------------------------------------------------------------------------

@app.local_entrypoint()
def main(path: str = "tests/", k: str = ""):
    """
    modal run modal_test.py                                          # full suite
    modal run modal_test.py --path tests/test_scoring.py             # single file
    modal run modal_test.py --path "tests/test_ui_search.py tests/test_ui_rate.py"  # space-separated
    modal run modal_test.py --k active_learning                      # keyword filter
    """
    pytest_args = path.split()  # support space-separated paths in one --path arg
    if k:
        pytest_args += ["-k", k]

    print(f"Running: pytest {' '.join(pytest_args)}")
    exit_code = run_tests.remote(pytest_args)

    if exit_code == 0:
        print("\n✓ All tests passed.")
    else:
        print(f"\n✗ Tests failed (exit code {exit_code}).")
    sys.exit(exit_code)
