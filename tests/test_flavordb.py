"""
Tests for FlavorDB2 scraped data (Plan 01-02).

These tests verify the output of the FlavorDB2 scraper. All tests are skipped
until the scraper has been run: python data/scrape_flavordb.py

FlavorDB2 API: https://cosylab.iiitd.edu.in/flavordb/entities_json?id=
NOTE: No "2" in the API path — this is the confirmed working endpoint.
"""
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
INGREDIENTS_CSV = PROJECT_ROOT / "data" / "raw" / "ingredients.csv"
CACHE_DB = PROJECT_ROOT / "data" / "raw" / "flavordb_cache.sqlite"


@pytest.mark.skip(reason="FlavorDB2 scraper not yet run — execute Plan 01-02 first")
def test_cache_populated():
    """Verify that the FlavorDB2 SQLite cache has been populated.

    When active:
    - data/raw/flavordb_cache.sqlite must exist
    - data/raw/ingredients.csv must exist with at least 900 ingredient rows
      (FlavorDB2 contains ~1000 entities; 900 is a conservative minimum)
    """
    import pandas as pd

    assert CACHE_DB.exists(), (
        f"FlavorDB2 cache not found at {CACHE_DB}. "
        "Run: python data/scrape_flavordb.py"
    )

    assert INGREDIENTS_CSV.exists(), (
        f"ingredients.csv not found at {INGREDIENTS_CSV}. "
        "Run: python data/scrape_flavordb.py"
    )

    df = pd.read_csv(INGREDIENTS_CSV)
    assert len(df) >= 900, (
        f"Expected >= 900 ingredients, got {len(df)}. "
        "Check logs/pipeline.log for scraping errors."
    )


@pytest.mark.skip(reason="FlavorDB2 scraper not yet run — execute Plan 01-02 first")
def test_ingredients_schema():
    """Verify that ingredients.csv has the required columns.

    When active:
    - ingredients.csv must have columns: ingredient_id, name, category, molecules_json
    - ingredient_id should be unique
    - molecules_json should be a non-empty JSON array for most rows
    """
    import pandas as pd

    assert INGREDIENTS_CSV.exists(), (
        f"ingredients.csv not found at {INGREDIENTS_CSV}"
    )

    df = pd.read_csv(INGREDIENTS_CSV)
    required_columns = {"ingredient_id", "name", "category", "molecules_json"}
    actual_columns = set(df.columns)
    missing_columns = required_columns - actual_columns

    assert not missing_columns, (
        f"ingredients.csv is missing columns: {missing_columns}. "
        f"Found columns: {list(df.columns)}"
    )

    assert df["ingredient_id"].is_unique, (
        "ingredient_id column has duplicate values — check scraper deduplication logic"
    )
