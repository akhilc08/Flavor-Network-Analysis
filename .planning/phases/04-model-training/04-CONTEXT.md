# Phase 4: Model Training - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Train the 3-layer heterogeneous GAT on the validated graph from Phase 3, using dual supervision (molecular + recipe BCE) and InfoNCE contrastive loss. Produces a best-AUC checkpoint and 128-dim ingredient embeddings at `model/embeddings/ingredient_embeddings.pkl`. Scoring, active learning, and UI are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Training UX & Console Output

**User deferred all decisions here to Claude for best portfolio outcome.**

- tqdm outer progress bar over epochs (consistent with Phase 1 pattern — 1 bar showing epoch N/200)
- Per-epoch compact summary line: `Epoch 45/200 | AUC: 0.742↑ | Loss: 0.312 (mol=0.128, rec=0.115, nce=0.069) | LR: 8.3e-4`
- Arrow indicator (↑/↓/=) on AUC shows trend at a glance — portfolio-friendly
- All 3 loss components (molecular, recipe, InfoNCE) logged separately — never merged into single number
- CSV log written to `logs/training_metrics.csv`: one row per epoch with all loss components, AUC, lr — enables learning curve plots
- Final summary printed at end: best AUC epoch, total time, checkpoint path

### Checkpoint & Resume Strategy

**User deferred all decisions here to Claude for best portfolio outcome.**

- Save best checkpoint on AUC improvement: `model/checkpoints/best_model.pt` (single authoritative best)
- Periodic safety checkpoints every 50 epochs: `model/checkpoints/epoch_050.pt`, `epoch_100.pt`, `epoch_150.pt`, `epoch_200.pt` (ring buffer, 4 max — bounds disk usage)
- Checkpoint includes: model state dict, optimizer state dict, scheduler state dict, current epoch, best AUC — enables exact resume
- CLI flag `--resume model/checkpoints/epoch_050.pt` to restart from a checkpoint; cosine LR schedule restarted from saved epoch (not from 0)
- If `--resume` and `best_model.pt` both exist, resume preserves the existing best AUC as the comparison baseline

### Hyperparameter Configurability

**User deferred all decisions here to Claude for best portfolio outcome.**

- All hyperparameters as named argparse flags with spec defaults — zero changes needed to reproduce the paper result, easy to experiment
- Full flag list: `--epochs 200 --lr 1e-3 --hidden 256 --embed 128 --heads 8 --dropout 0.3 --alpha 0.4 --beta 0.4 --gamma 0.2 --tau 0.15 --mol-threshold 5 --recipe-threshold 10`
- `--help` output is portfolio-visible and shows all hyperparameters with defaults — demonstrates engineering rigor
- Argument values echoed to console at training start (and to `logs/training_metrics.csv` header comments) for reproducibility

### OOM & MPS Fallback

**User deferred all decisions here to Claude for best portfolio outcome.**

- Auto-detect backend: MPS if `torch.backends.mps.is_available()`, else CPU — no manual flag needed
- Warning printed if falling back to CPU: `[WARNING] MPS not available — training on CPU (expect ~5x slower)`
- Before training: print memory estimate based on graph node/edge counts and hidden_dim
- OOM handling: catch `RuntimeError` containing "out of memory", call `torch.mps.empty_cache()`, print clear message with suggested fix (`--hidden 128` or reduce `--heads 4`), then exit cleanly — no silent crash or corrupted checkpoint
- Embedding export uses `@torch.no_grad()` and moves tensors to CPU before pkl write to minimize peak memory

### Claude's Discretion
- Exact learning rate scheduler implementation details (warm-up vs cold start with cosine)
- Internal batch construction for link prediction (negative sampling ratio)
- Whether to use `torch.compile()` for MPS acceleration (test if it helps on PyG HeteroConv)
- Log file rotation / append vs overwrite behavior for repeated training runs

</decisions>

<specifics>
## Specific Ideas

- User's primary goal: **portfolio showcase for recruiters** — the training output should look clean and professional, not noisy. The per-epoch one-liner + tqdm bar achieves this.
- `logs/training_metrics.csv` enables post-training learning curve plots — good for a README / portfolio write-up demonstrating the model actually learned something.
- `--help` output serves as implicit documentation of the model architecture — reviewers will read it.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_pipeline.py`: orchestrator pattern (direct function import, not subprocess) — Phase 4 training script should be invocable the same way
- `logs/pipeline.log`: established log path; training metrics go to `logs/training_metrics.csv` (separate file, not mixed into pipeline log)
- `model/embeddings/` directory: already exists (created in Phase 1 scaffold)
- `graph/hetero_data.pt`: input artifact from Phase 3 — load with `torch.load()`

### Established Patterns
- Always continue + summarize: OOM exits cleanly with actionable message (never silent crash)
- tqdm per operation: outer epoch bar; no per-batch bar (too noisy for 200 epochs)
- Summary table at end of script: "Training complete | Best AUC: 0.742 @ epoch 89 | Checkpoint: model/checkpoints/best_model.pt"
- `logs/pipeline.log` for run-level logging; dedicated CSV for per-epoch metrics

### Integration Points
- **Input**: `graph/hetero_data.pt` + index dicts from Phase 3 (ingredient_id_to_idx, molecule_id_to_idx)
- **Output**: `model/checkpoints/best_model.pt` → consumed by Phase 5 scoring
- **Output**: `model/embeddings/ingredient_embeddings.pkl` → consumed by Phase 5 scoring and Phase 6 UI
- **Output**: `logs/training_metrics.csv` → used for README plots and portfolio documentation
- Active learning gate (AUC >= 0.70) checked at Phase 5/6 startup against this checkpoint

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope (user deferred all implementation decisions to Claude's discretion for portfolio-optimal outcome)

</deferred>

---

*Phase: 04-model-training*
*Context gathered: 2026-03-11*
