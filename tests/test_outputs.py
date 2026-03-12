"""
Integration tests for final pipeline output files (all phases).

These tests verify that the core output files of Phase 1 data ingestion exist.
They will FAIL until all data ingestion steps are complete — this is expected
and correct behavior.

This test is intentionally NOT skipped. It serves as the acceptance gate for
Phase 1 completion. The test suite should show these as failing until Plan 01-04
(recipe processing) is complete.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"


def test_output_files_exist():
    """Verify that all Phase 1 pipeline output files exist.

    This test FAILS until data ingestion is complete. That is expected.
    It becomes the final acceptance check for Phase 1.

    Required files:
    - data/raw/ingredients.csv: FlavorDB2 scraper output (Plan 01-02)
    - data/raw/molecules.csv:   FooDB join output (Plan 01-03)
    - data/raw/recipes.csv:     Recipe co-occurrence output (Plan 01-04)

    All three files must exist for Phase 2 (feature engineering) to begin.
    """
    required_files = [
        DATA_RAW / "ingredients.csv",
        DATA_RAW / "molecules.csv",
        DATA_RAW / "recipes.csv",
    ]

    missing = [str(f.relative_to(PROJECT_ROOT)) for f in required_files if not f.exists()]

    assert not missing, (
        f"Missing Phase 1 output files: {missing}\n\n"
        "Complete the following plans in order:\n"
        "  Plan 01-02: FlavorDB2 scraper → data/raw/ingredients.csv\n"
        "  Plan 01-03: FooDB join       → data/raw/molecules.csv\n"
        "  Plan 01-04: Recipe processor → data/raw/recipes.csv\n\n"
        "Then run: python run_pipeline.py"
    )
