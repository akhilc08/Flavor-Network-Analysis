"""
Tests for recipe co-occurrence data (Plan 01-04).

These tests verify the output of the RecipeNLG processing step. All tests are
skipped until the recipe processing has been run.

RecipeNLG source: HuggingFace datasets (primary corpus)
Processing note: Must be processed in streaming/chunked mode on 8GB RAM machines.
"""
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RECIPES_CSV = PROJECT_ROOT / "data" / "raw" / "recipes.csv"


def test_cooccurrence_count():
    """Verify that the recipe co-occurrence table has sufficient pair coverage.

    When active:
    - recipes.csv must have more than 1000 rows (ingredient pairs with co-occurrence counts)
    - Must have columns: ingredient_a, ingredient_b, count
    - ingredient_a and ingredient_b should be normalized ingredient names
      (lowercase, stripped, matched to FlavorDB ingredient names)
    - count should be a positive integer representing how many recipes
      contained both ingredients

    Note: This file merges co-occurrence counts from both RecipeNLG (primary)
    and AllRecipes (supplemental) into a single co-occurrence table.
    Both sources contribute equally to edge weights in the graph.
    """
    import pandas as pd

    assert RECIPES_CSV.exists(), (
        f"recipes.csv not found at {RECIPES_CSV}. "
        "Run: python data/process_recipes.py"
    )

    df = pd.read_csv(RECIPES_CSV)
    assert len(df) > 1000, (
        f"Expected > 1000 co-occurrence pairs, got {len(df)}. "
        "Check recipe processing logs in logs/pipeline.log."
    )

    required_columns = {"ingredient_a", "ingredient_b", "count"}
    actual_columns = set(df.columns)
    missing_columns = required_columns - actual_columns

    assert not missing_columns, (
        f"recipes.csv is missing columns: {missing_columns}. "
        f"Found columns: {list(df.columns)}"
    )

    assert (df["count"] > 0).all(), (
        "All co-occurrence counts must be positive integers"
    )
