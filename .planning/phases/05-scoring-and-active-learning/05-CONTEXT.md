# Phase 5: Scoring and Active Learning - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Compute surprise scores for every ingredient pair and implement the active learning loop: user ratings fine-tune the model with experience replay, and scored_pairs are re-exported after each round. Streamlit UI integration is Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Scored Pairs Scope and Storage
- Compute ALL ingredient pair combinations — no filtering or threshold cutoff
- Use vectorized matrix operations (torch or numpy matmul on full embedding matrix) for O(n²) compute, not a Python loop — essential at 500k+ pairs on M2
- Store as a pandas DataFrame pickle at `scoring/scored_pairs.pkl`
- Columns: `ingredient_a`, `ingredient_b`, `surprise_score`, `pairing_score`, `molecular_overlap`, `recipe_familiarity`, `label`
- DataFrame sorted by `surprise_score` descending on disk — Phase 6 can directly filter/groupby without re-sorting
- ~500k rows at ~100 bytes/row = ~50MB — acceptable for M2 8GB RAM demo
- Summary table printed at end: "Scored 499,500 pairs. Top label breakdown: Surprising: 12%, Unexpected: 35%, Classic: 53%"

### Experience Replay Buffer
- During Phase 4 training, save a replay buffer to `model/replay_buffer.pkl` before training ends
- Buffer = 1000 stratified positive edge pairs sampled from training set: 500 high-molecular-overlap pairs (anchor stability) + 500 high-co-occurrence pairs (recipe knowledge anchors)
- Buffer saved as dict: `{"ingredient_pairs": [(a_idx, b_idx), ...], "labels": [1, ...]}`
- Each fine-tune round: sample 5× feedback_batch_size from buffer uniformly, combine with feedback batch for 10 epochs
- If `model/replay_buffer.pkl` is missing at fine-tune time: log a WARNING and proceed without replay (graceful degradation, don't crash the UI)
- LR for fine-tuning: 1e-4 (10× lower than base 1e-3, per LEARN-03)

### Post-Fine-Tune Re-Scoring
- Always full re-score after every fine-tune round — overwrite `scoring/scored_pairs.pkl`
- Rationale: embeddings change globally after GNN weight updates; selective re-scoring would produce stale scores for unrated pairs
- Vectorized recompute takes ~5–15 seconds on M2 — acceptable for portfolio demo, shows the pipeline actually works
- Checkpoint saved to `model/checkpoints/pre_finetune_round_{N}.pt` before each round, where N increments from 1

### Module Interface (for Phase 6)
- Direct Python imports — no subprocess, no CLI invocations
- `scoring/score.py` exports clean public API:
  - `compute_all_pairs(embeddings, co_occurrence, molecule_sets) -> pd.DataFrame`
  - `load_scored_pairs() -> pd.DataFrame` (reads from `scoring/scored_pairs.pkl`)
  - `get_top_pairings(ingredient_name, n=10) -> list[dict]`
  - `get_uncertain_pairs(n=20) -> list[dict]` (pairing_score closest to 0.5)
- `model/active_learning.py` exports:
  - `submit_rating(ingredient_a, ingredient_b, rating) -> dict` — appends to feedback.csv, triggers fine-tune, returns `{"auc_before": float, "auc_after": float}`
  - `is_active_learning_enabled() -> bool` (checks AUC ≥ 0.70 gate, per LEARN-05)
- Consistent with Phase 1 pattern of direct function import in run_pipeline.py

### Scoring Script as Standalone + Importable
- `scoring/compute_scores.py` is both a runnable script (`python scoring/compute_scores.py`) and importable
- Uses `if __name__ == "__main__":` guard — same pattern as Phase 1 data scripts
- Script variant reads embeddings from `model/embeddings/ingredient_embeddings.pkl` and graph from `graph/hetero_data.pt`

### Claude's Discretion
- Exact replay buffer sampling strategy (uniform vs stratified by label)
- Validation AUC computation implementation detail (use same val split as Phase 4)
- How to handle the case where feedback.csv has >100 rows (whether to cap the feedback batch size)
- DataFrame index choice (integer index vs MultiIndex on ingredient pair)

</decisions>

<specifics>
## Specific Ideas

- User delegated all implementation decisions: "do whatever results in the best possible final product to showcase to other people and recruiters and results in the least amount of bugs"
- Primary constraint: M2 MacBook Air 8GB RAM — vectorized scoring compute must not OOM; 500k pairs × 128-dim floats = manageable
- Portfolio framing: the active learning loop is a key story — make it visible that the model actually improves. AUC delta should be prominently available for Phase 6 to display.
- The experience replay buffer demonstrates knowledge of catastrophic forgetting — worth an inline comment explaining why it exists

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `logs/pipeline.log` + tqdm pattern: established in Phase 1 — use same logging setup
- Summary table print pattern: "X processed, Y failed (Z%)" — use same format at end of `compute_scores.py`
- Skip-if-exists pattern: check `scoring/scored_pairs.pkl` before recomputing
- `model/embeddings/ingredient_embeddings.pkl`: output of Phase 4 — primary input to Phase 5

### Established Patterns
- Direct function imports (not subprocess) — set in Phase 1 orchestrator
- Always continue + summarize, never crash on partial data
- Cache and checkpoint frequently (FlavorDB cache in Phase 1, model checkpoints in Phase 4)

### Integration Points
- **Reads from Phase 4:** `model/embeddings/ingredient_embeddings.pkl`, `graph/hetero_data.pt` (for co-occurrence weights and molecule sets), `model/checkpoints/best_model.pt` (base checkpoint for fine-tuning)
- **Writes for Phase 6:** `scoring/scored_pairs.pkl`, `feedback.csv`, `model/replay_buffer.pkl` (read back during fine-tune)
- **Phase 6 imports:** `from scoring.score import load_scored_pairs, get_top_pairings, get_uncertain_pairs` and `from model.active_learning import submit_rating, is_active_learning_enabled`

</code_context>

<deferred>
## Deferred Ideas

- None — user delegated all decisions; discussion stayed within phase scope

</deferred>

---

*Phase: 05-scoring-and-active-learning*
*Context gathered: 2026-03-11*
