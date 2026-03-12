"""
Tests for FooDB molecule join (Plan 01-03).

These tests verify the output of the FooDB fuzzy-match join. All tests are
skipped until the join has been run.

FooDB data: Download from foodb.ca/downloads (CC BY-NC 4.0)
Extract to: data/raw/foodb/
"""
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MOLECULES_CSV = PROJECT_ROOT / "data" / "raw" / "molecules.csv"


@pytest.mark.skip(reason="FooDB join not yet run — execute Plan 01-03 first")
def test_join_count():
    """Verify that the FooDB join produced a molecules.csv with sufficient matches.

    When active:
    - molecules.csv must exist with at least 300 rows
    - Must have a 'foodb_matched' boolean column indicating which ingredients
      were successfully matched against the FooDB compound database
    - The match rate should be above 30% (300/1000 minimum)

    Note: If match count < 300, a WARNING is logged but execution continues.
    The Phase 3 graph construction gate enforces the final threshold.
    """
    import pandas as pd

    assert MOLECULES_CSV.exists(), (
        f"molecules.csv not found at {MOLECULES_CSV}. "
        "Run: python data/join_foodb.py"
    )

    df = pd.read_csv(MOLECULES_CSV)
    assert len(df) >= 300, (
        f"Expected >= 300 molecule rows, got {len(df)}. "
        "Check FooDB download and fuzzy matching thresholds. "
        "See logs/pipeline.log for match details."
    )

    assert "foodb_matched" in df.columns, (
        f"molecules.csv is missing 'foodb_matched' column. "
        f"Found columns: {list(df.columns)}"
    )
