"""
Recipe co-occurrence processor — streams 2.2M RecipeNLG recipes to build an
ingredient co-occurrence counter, scrapes AllRecipes politely (with bot-block
fallback), merges both sources, and writes recipes.csv.

Output:
    data/raw/recipes.csv   — ingredient_a, ingredient_b, count

Run standalone:
    python data/scrape_recipes.py
    python data/scrape_recipes.py --force           # overwrite if recipes.csv exists
    python data/scrape_recipes.py --skip-allrecipes # RecipeNLG only

NOTE: RecipeNLG streaming takes 15-45 minutes (2.2M recipes). Use --force
to restart from scratch; the HuggingFace streaming dataset does not support
checkpointing.
"""

import argparse
import ast
import json
import logging
import os
import random
import re
import time
from collections import Counter
from itertools import combinations

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# ---------------------------------------------------------------------------
# Logging — file + console (same pattern as scrape_flavordb.py)
# ---------------------------------------------------------------------------
os.makedirs("logs", exist_ok=True)

_log_format = "%(asctime)s %(levelname)-8s %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=_log_format,
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RECIPES_CSV = "data/raw/recipes.csv"
ALLRECIPES_CSV = "data/raw/recipes_allrecipes.csv"

ALLRECIPES_CATEGORIES = {
    "Italian": "https://www.allrecipes.com/recipes/723/world-cuisine/european/italian/",
    "Asian": "https://www.allrecipes.com/recipes/233/world-cuisine/asian/",
    "Mexican": "https://www.allrecipes.com/recipes/728/world-cuisine/latin-american/mexican/",
    "French": "https://www.allrecipes.com/recipes/1232/world-cuisine/european/french/",
    "American": "https://www.allrecipes.com/recipes/80/main-dish/",
    "Indian": "https://www.allrecipes.com/recipes/233/world-cuisine/asian/indian/",
    "Mediterranean": "https://www.allrecipes.com/recipes/1239/world-cuisine/european/mediterranean/",
    "Middle Eastern": "https://www.allrecipes.com/recipes/227/world-cuisine/middle-eastern/",
    "Japanese": "https://www.allrecipes.com/recipes/96/world-cuisine/asian/japanese/",
    "Thai": "https://www.allrecipes.com/recipes/695/world-cuisine/asian/thai/",
}

RECIPES_PER_CATEGORY = 50
REQUEST_DELAY_MIN = 2.0
REQUEST_DELAY_MAX = 5.0

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

_MANUAL_FALLBACK_MESSAGE = """\
AllRecipes scraping was blocked. To supply data manually:
1. Create data/raw/recipes_allrecipes.csv
2. Columns: recipe_name (str), ingredients (comma-separated ingredient list)
3. Re-run with: python data/scrape_recipes.py
The pipeline will use RecipeNLG data only until this file is provided."""


# ---------------------------------------------------------------------------
# RecipeNLG streaming co-occurrence counter
# ---------------------------------------------------------------------------

RECIPENLG_CSV_URL = (
    "https://huggingface.co/datasets/Mahimas/recipenlg/resolve/main/RecipeNLG.csv"
)
RECIPENLG_TOTAL = 2231142  # total recipes for tqdm estimate


def _parse_ner_list(raw: str) -> list[str]:
    """Parse NER field which is a Python/JSON list literal like '["flour", "egg"]'."""
    if not raw or not isinstance(raw, str):
        return []
    raw = raw.strip()
    if not raw.startswith("["):
        return []
    try:
        return ast.literal_eval(raw)
    except Exception:
        try:
            return json.loads(raw)
        except Exception:
            return []


def process_recipe_nlg() -> Counter:
    """Stream 2.2M RecipeNLG recipes and return ingredient co-occurrence Counter.

    Streams the full RecipeNLG dataset CSV directly from HuggingFace via HTTP
    using pandas read_csv with chunksize (no downloads to disk). Uses the NER
    column (clean ingredient tokens) instead of the raw ingredients strings.

    Normalizes pairs as (min(a, b), max(a, b)) for consistent key ordering.
    Filters tokens shorter than 3 or longer than 50 characters (noise).

    Returns
    -------
    Counter
        Keys are (ingredient_a, ingredient_b) tuples (alphabetical order).
        Values are integer co-occurrence counts.
    """
    logger.info("Starting RecipeNLG streaming co-occurrence processing from HuggingFace...")
    logger.info("Streaming from: %s", RECIPENLG_CSV_URL)

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    resp = session.get(RECIPENLG_CSV_URL, stream=True, timeout=60)
    resp.raise_for_status()

    co_occurrence: Counter = Counter()
    recipe_count = 0
    chunk_size = 5000

    with logging_redirect_tqdm():
        pbar = tqdm(total=RECIPENLG_TOTAL, desc="RecipeNLG", unit="recipes")
        for chunk in pd.read_csv(resp.raw, chunksize=chunk_size, low_memory=False):
            if "NER" not in chunk.columns:
                logger.warning("NER column not found in chunk — skipping")
                pbar.update(len(chunk))
                continue

            for ner_raw in chunk["NER"]:
                tokens_raw = _parse_ner_list(str(ner_raw))
                ingredients = []
                for token in tokens_raw:
                    token = str(token).strip().lower()
                    if 3 <= len(token) <= 50:
                        ingredients.append(token)

                # Deduplicate within recipe before combining
                ingredients = list(set(ingredients))

                for a, b in combinations(sorted(ingredients), 2):
                    co_occurrence[(a, b)] += 1

                recipe_count += 1

            pbar.update(len(chunk))

            if recipe_count % 100_000 == 0 and recipe_count > 0:
                logger.info(
                    "RecipeNLG: processed %d recipes, %d pairs so far",
                    recipe_count,
                    len(co_occurrence),
                )

        pbar.close()

    logger.info(
        "RecipeNLG complete: %d recipes processed, %d unique pairs",
        recipe_count,
        len(co_occurrence),
    )
    return co_occurrence


# ---------------------------------------------------------------------------
# AllRecipes polite scraper
# ---------------------------------------------------------------------------

def _is_recipe_type(node: dict) -> bool:
    """Check if a JSON-LD node has @type Recipe (handles both string and list)."""
    t = node.get("@type")
    if isinstance(t, str):
        return t == "Recipe"
    if isinstance(t, list):
        return "Recipe" in t
    return False


def _extract_ingredients_json_ld(soup: BeautifulSoup) -> list[str]:
    """Try to extract recipeIngredient from JSON-LD script blocks.

    Handles @type as both string ("Recipe") and list (["Recipe"]),
    as well as nested @graph structures.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # JSON-LD can be a list or a single object
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and _is_recipe_type(item):
                        return item.get("recipeIngredient", [])
            elif isinstance(data, dict):
                if _is_recipe_type(data):
                    return data.get("recipeIngredient", [])
                # Sometimes nested under @graph
                for item in data.get("@graph", []):
                    if isinstance(item, dict) and _is_recipe_type(item):
                        return item.get("recipeIngredient", [])
        except (json.JSONDecodeError, AttributeError):
            continue
    return []


def _extract_ingredients_css(soup: BeautifulSoup) -> list[str]:
    """CSS fallback for ingredient extraction when JSON-LD is absent or fails.

    Tries multiple selectors covering AllRecipes current and legacy markup.
    """
    selectors = [
        "li[class*='ingredient']",
        "span[class*='ingredient']",
        "span.ingredients-item-name",
        "li.ingredients-item",
        "p[class*='ingredient']",
        "[data-ingredient-name]",
    ]
    for sel in selectors:
        elements = soup.select(sel)
        if elements:
            return [el.get_text(strip=True) for el in elements if el.get_text(strip=True)]
    return []


def _parse_ingredient_name(raw: str) -> str:
    """Strip quantities/units from a raw ingredient string to get a clean name."""
    # Remove leading numbers, fractions, and common units
    cleaned = re.sub(
        r"^\d[\d/\s]*\s*(cup|cups|tablespoon|tablespoons|tbsp|tsp|teaspoon|teaspoons|"
        r"ounce|ounces|oz|pound|pounds|lb|lbs|gram|grams|g|kg|ml|liter|liters|"
        r"clove|cloves|slice|slices|piece|pieces|can|cans|jar|jars|package|packages|"
        r"bunch|bag|bags|head|heads|sprig|sprigs|pinch|dash)s?\s*",
        "",
        raw,
        flags=re.IGNORECASE,
    )
    # Remove parenthetical notes like "(optional)" or "(finely chopped)"
    cleaned = re.sub(r"\(.*?\)", "", cleaned)
    # Take only the first comma-delimited part (e.g. "flour, sifted" → "flour")
    cleaned = cleaned.split(",")[0]
    cleaned = cleaned.strip().lower()
    return cleaned


def _is_blocked(response: requests.Response) -> bool:
    """Detect bot-blocking signals from a response.

    AllRecipes uses Cloudflare as a CDN — their normal pages reference
    'cloudflare' in HTML. Only flag actual challenge/CAPTCHA pages, not
    legitimate pages that happen to mention Cloudflare.
    """
    if response.status_code in (403, 429):
        return True
    # Only flag Cloudflare if there's an actual bot challenge present
    text_lower = response.text.lower()
    if "challenge-form" in text_lower and "cloudflare" in text_lower:
        return True
    if "cf_chl_" in response.text:
        return True
    # Actual Cloudflare CAPTCHA page indicator
    if response.status_code == 403 and "cloudflare" in text_lower:
        return True
    # cf-mitigated: challenge header signals Cloudflare blocked the request
    if response.headers.get("cf-mitigated", "").lower() == "challenge":
        return True
    return False


def scrape_allrecipes(force: bool = False) -> tuple[Counter, int]:
    """Scrape AllRecipes for co-occurrence data, handling bot-blocking gracefully.

    Checks for manual fallback CSV first. If neither CSV nor manual data exists,
    fetches from allrecipes.com with polite delays and browser-like headers.

    On bot-block detection: saves partial ALLRECIPES_CSV, logs warning, prints
    manual fallback instructions, and returns whatever was collected. Does NOT
    raise exceptions.

    Parameters
    ----------
    force:
        If True, re-scrape even if ALLRECIPES_CSV already exists.

    Returns
    -------
    tuple[Counter, int]
        (co_occurrence Counter, number of recipes successfully processed)
    """
    # --- Manual fallback check FIRST ---
    if not force and os.path.exists(ALLRECIPES_CSV):
        logger.info("AllRecipes: using manual/cached CSV at %s", ALLRECIPES_CSV)
        try:
            df = pd.read_csv(ALLRECIPES_CSV)
            co_occurrence: Counter = Counter()
            recipes_loaded = 0
            for _, row in df.iterrows():
                ingredients_raw = str(row.get("ingredients", ""))
                tokens = [t.strip().lower() for t in ingredients_raw.split(",") if t.strip()]
                tokens = list(set(t for t in tokens if 3 <= len(t) <= 50))
                for a, b in combinations(sorted(tokens), 2):
                    co_occurrence[(a, b)] += 1
                recipes_loaded += 1
            logger.info(
                "AllRecipes: loaded %d recipes from CSV, %d pairs",
                recipes_loaded,
                len(co_occurrence),
            )
            return co_occurrence, recipes_loaded
        except Exception as exc:
            logger.warning("AllRecipes: failed to read CSV (%s) — will re-scrape", exc)

    # --- Live scrape ---
    session = requests.Session()
    session.headers.update(_BROWSER_HEADERS)

    co_occurrence = Counter()
    recipes_processed = 0
    partial_rows: list[dict] = []
    blocked = False

    os.makedirs("data/raw", exist_ok=True)

    logger.info("AllRecipes: starting scrape of %d categories", len(ALLRECIPES_CATEGORIES))

    for category_name, category_url in ALLRECIPES_CATEGORIES.items():
        if blocked:
            break

        logger.info("AllRecipes: fetching category '%s'", category_name)
        try:
            resp = session.get(category_url, timeout=15)
        except Exception as exc:
            logger.warning("AllRecipes: request error for category '%s': %s", category_name, exc)
            continue

        if _is_blocked(resp):
            logger.warning(
                "AllRecipes: blocked after %d recipes (category: %s, status: %d)",
                recipes_processed,
                category_name,
                resp.status_code,
            )
            blocked = True
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract recipe URLs from listing page
        recipe_links: list[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # AllRecipes recipe URLs match /recipe/<id>/<slug>/
            if re.match(r"https?://www\.allrecipes\.com/recipe/\d+/", href):
                if href not in recipe_links:
                    recipe_links.append(href)
            if len(recipe_links) >= RECIPES_PER_CATEGORY:
                break

        if not recipe_links:
            logger.warning(
                "AllRecipes: no recipe links found for category '%s' — site may have changed structure",
                category_name,
            )

        for recipe_url in recipe_links:
            if blocked:
                break

            time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

            try:
                recipe_resp = session.get(recipe_url, timeout=15)
            except Exception as exc:
                logger.warning("AllRecipes: request error for recipe '%s': %s", recipe_url, exc)
                continue

            if _is_blocked(recipe_resp):
                logger.warning(
                    "AllRecipes: blocked after %d recipes (status: %d)",
                    recipes_processed,
                    recipe_resp.status_code,
                )
                blocked = True
                break

            recipe_soup = BeautifulSoup(recipe_resp.text, "html.parser")

            # Extract ingredients: try JSON-LD first, then CSS fallback
            raw_ingredients = _extract_ingredients_json_ld(recipe_soup)
            if not raw_ingredients:
                raw_ingredients = _extract_ingredients_css(recipe_soup)

            if not raw_ingredients:
                logger.debug("AllRecipes: no ingredients extracted from %s", recipe_url)
                continue

            # Parse and normalize ingredient names
            clean_ingredients = []
            for raw in raw_ingredients:
                name = _parse_ingredient_name(raw)
                if name and 3 <= len(name) <= 50:
                    clean_ingredients.append(name)

            clean_ingredients = list(set(clean_ingredients))

            for a, b in combinations(sorted(clean_ingredients), 2):
                co_occurrence[(a, b)] += 1

            # Record for partial CSV
            recipe_name = recipe_url.rstrip("/").split("/")[-1]
            partial_rows.append({
                "recipe_name": recipe_name,
                "ingredients": ",".join(clean_ingredients),
            })
            recipes_processed += 1

            logger.debug(
                "AllRecipes: scraped recipe %d (%d ingredients): %s",
                recipes_processed,
                len(clean_ingredients),
                recipe_url,
            )

    # --- Save ALLRECIPES_CSV (both success and partial/blocked) ---
    if partial_rows:
        df_partial = pd.DataFrame(partial_rows)
        df_partial.to_csv(ALLRECIPES_CSV, index=False)
        logger.info(
            "AllRecipes: saved %d recipes to %s",
            len(partial_rows),
            ALLRECIPES_CSV,
        )

    if blocked:
        logger.warning("AllRecipes: blocked after %d recipes", recipes_processed)
        print(_MANUAL_FALLBACK_MESSAGE)

    logger.info(
        "AllRecipes: %d recipes processed, %d co-occurrence pairs",
        recipes_processed,
        len(co_occurrence),
    )
    return co_occurrence, recipes_processed


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(force: bool = False, skip_allrecipes: bool = False) -> None:
    """Build ingredient co-occurrence CSV from RecipeNLG + AllRecipes.

    Parameters
    ----------
    force:
        If True, re-run even if recipes.csv already exists.
    skip_allrecipes:
        If True, skip AllRecipes scraping (RecipeNLG only).
    """
    # --- Idempotence check ---
    if not force and os.path.exists(RECIPES_CSV):
        logger.info("[SKIP] %s already exists. Use --force to re-run.", RECIPES_CSV)
        return

    os.makedirs("data/raw", exist_ok=True)

    # --- RecipeNLG streaming ---
    nlg_counter = process_recipe_nlg()
    nlg_pairs = len(nlg_counter)

    # --- AllRecipes scraping ---
    if skip_allrecipes:
        allrecipes_counter: Counter = Counter()
        allrecipes_recipes = 0
        allrecipes_pairs = 0
        logger.info("AllRecipes: skipped (--skip-allrecipes flag)")
    else:
        allrecipes_counter, allrecipes_recipes = scrape_allrecipes(force=force)
        allrecipes_pairs = len(allrecipes_counter)

    # --- Merge by summing counts for matching pairs ---
    merged = nlg_counter + allrecipes_counter

    # --- Build DataFrame sorted by count descending ---
    rows = [
        {"ingredient_a": a, "ingredient_b": b, "count": c}
        for (a, b), c in merged.items()
    ]
    df = pd.DataFrame(rows, columns=["ingredient_a", "ingredient_b", "count"])
    df = df.sort_values("count", ascending=False).reset_index(drop=True)

    df.to_csv(RECIPES_CSV, index=False)

    total_pairs = len(df)
    logger.info(
        "RecipeNLG: %d pairs; AllRecipes: %d recipes, %d pairs; Total merged: %d pairs",
        nlg_pairs,
        allrecipes_recipes,
        allrecipes_pairs,
        total_pairs,
    )
    logger.info("Wrote %d rows to %s", total_pairs, RECIPES_CSV)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Stream RecipeNLG (2.2M recipes) and optionally scrape AllRecipes "
            "to build ingredient co-occurrence table. Writes data/raw/recipes.csv."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if recipes.csv already exists.",
    )
    parser.add_argument(
        "--skip-allrecipes",
        action="store_true",
        help="Skip AllRecipes scraping (RecipeNLG only — faster for testing).",
    )
    args = parser.parse_args()
    main(force=args.force, skip_allrecipes=args.skip_allrecipes)
