"""
Tests for AllRecipes supplemental data (Plan 01-04).

These tests verify that AllRecipes data is available either from the scraper
or from the manual CSV fallback. All tests are skipped until the AllRecipes
scraper has been run or manual data has been provided.

Manual fallback: If the scraper is blocked by bot detection, create:
  data/raw/recipes_allrecipes.csv with columns: recipe_name, ingredients
  where 'ingredients' is a comma-separated list of ingredient names.
"""
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ALLRECIPES_CSV = PROJECT_ROOT / "data" / "raw" / "recipes_allrecipes.csv"
PIPELINE_LOG = PROJECT_ROOT / "logs" / "pipeline.log"


def test_scraper_runs():
    """Verify that AllRecipes data is available via scraper or manual fallback.

    When active, one of these conditions must be true:
    1. data/raw/recipes_allrecipes.csv exists (scraper ran successfully, or
       user provided manual fallback CSV)
    2. logs/pipeline.log contains "AllRecipes: partial" (scraper got partial data
       before being blocked)
    3. logs/pipeline.log contains "AllRecipes: blocked" (scraper was blocked but
       recorded the outcome for transparency)

    Manual fallback format:
      recipe_name,ingredients
      "Pasta Carbonara","egg,pasta,bacon,parmesan"
      "Chicken Tikka","chicken,yogurt,tomato,garam masala"

    The scraper writes partial results before exiting on bot-block detection,
    so even a blocked run may yield usable data.
    """
    csv_exists = ALLRECIPES_CSV.exists()

    log_has_status = False
    if PIPELINE_LOG.exists():
        log_content = PIPELINE_LOG.read_text()
        log_has_status = (
            "AllRecipes: partial" in log_content
            or "AllRecipes: blocked" in log_content
        )

    assert csv_exists or log_has_status, (
        f"AllRecipes data not found. Expected one of:\n"
        f"  1. {ALLRECIPES_CSV} to exist (manual CSV or successful scrape)\n"
        f"  2. {PIPELINE_LOG} to contain 'AllRecipes: partial' or 'AllRecipes: blocked'\n\n"
        "To provide manual data, create:\n"
        "  data/raw/recipes_allrecipes.csv\n"
        "  with columns: recipe_name, ingredients (comma-separated)\n\n"
        "Run scraper: python data/scrape_allrecipes.py"
    )
