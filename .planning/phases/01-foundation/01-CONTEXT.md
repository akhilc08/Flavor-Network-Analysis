# Phase 1: Foundation - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up the conda+pip hybrid environment and scrape/download all raw data to disk. Delivers: working environment, data/raw/ingredients.csv, molecules.csv, recipes.csv. Feature engineering, graph construction, and model training are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Pipeline Orchestration
- Single `run_pipeline.py` master script that calls each stage in order
- Flags like `--skip-scrape`, `--skip-foodb` etc. to resume from a checkpoint
- Check if output files already exist and skip that stage automatically (no re-runs if data is present)
- Each script in data/ also runs standalone with `python data/scrape_flavordb.py`
- Setup instructions live in README.md quickstart: conda create → pip install → run pipeline

### Progress & Logging UX
- tqdm progress bars per batch (scraping FlavorDB entities, fetching SMILES, etc.)
- All output logged to `logs/pipeline.log` (full run log); console shows progress + summary
- Summary table printed at end of each script: counts of scraped/failed/matched with percentages
- Example: "FlavorDB: 823 scraped, 177 failed (404). FooDB join: 612/823 matched (74%)"

### AllRecipes Handling
- Write a polite scraper with delays and user-agent headers
- If bot-blocking detected, scraper saves partial results and prints clear manual instructions
- Manual fallback: user can supply `data/raw/recipes_allrecipes.csv` with columns: recipe_name, ingredients (comma-separated)
- AllRecipes and RecipeNLG co-occurrence counts merged into single co-occurrence table: ingredient_a, ingredient_b, count
- Both sources contribute to edge weights equally (merged counts)

### Failure Behavior
- Always continue + summarize: log every failure, never crash on partial data
- If FooDB fuzzy match yields <300 ingredients: print prominent WARNING with count, continue — Phase 3 graph validation gate handles the threshold enforcement
- FlavorDB cache: if cache exists, use it silently without hitting network
- No automatic threshold-lowering or retry escalation — failures are reported, not hidden

### Claude's Discretion
- Exact delays and retry logic for AllRecipes scraper
- Log format details (timestamp format, log rotation)
- FooDB CSV download method (requests vs manual instructions)

</decisions>

<specifics>
## Specific Ideas

- User noted: if AllRecipes scraping is blocked, they will supply the data manually — make the fallback path obvious and the expected CSV format explicit in the README
- M2 MacBook Air with 8GB RAM is the target machine — RecipeNLG must be processed in streaming/chunked mode, never fully loaded into RAM

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — greenfield project

### Established Patterns
- None yet — this phase establishes the patterns

### Integration Points
- `data/raw/` outputs (ingredients.csv, molecules.csv, recipes.csv) feed directly into Phase 2 feature engineering
- `logs/pipeline.log` is consumed by the user for debugging across all phases
- FlavorDB cache (`data/raw/flavordb_cache/`) carries forward to Phase 2 if SMILES are needed

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-11*
