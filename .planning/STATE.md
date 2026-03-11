# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-11)

**Core value:** Surface ingredient pairs that are molecularly compatible but culturally underused — the surprise score is the key metric, not just similarity.
**Current focus:** Phase 1: Foundation

## Current Position

Phase: 1 of 6 (Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-11 — Roadmap created; ready to plan Phase 1

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-Phase 1]: PyTorch must be installed via pip wheel index (not conda channel) after RDKit is installed via conda-forge — version conflict killer if done in wrong order
- [Pre-Phase 1]: RecipeNLG (HuggingFace) is primary recipe corpus; AllRecipes scraping is supplemental and treated as unreliable
- [Pre-Phase 1]: InfoNCE temperature starts at 0.1-0.2 (not 0.07 from spec) — food domain has high molecular overlap among negatives
- [Pre-Phase 1]: Claude model target is `claude-sonnet-4-6` (Anthropic SDK 0.84.0)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 risk]: FlavorDB2 endpoint is undocumented and community-known only; cache all responses on first run; FooDB-only fallback acceptable if endpoint changes
- [Phase 2 risk]: PubChem rate limiting can leave silent SMILES gaps; token bucket at 400 req/min ceiling and full cache required before RDKit processing
- [Phase 3 risk]: RandomLinkSplit configuration for HeteroData with multiple edge types has limited worked examples — may need research during planning
- [Phase 5 risk]: Experience replay GNN fine-tune pattern is not well-documented; buffer size and LR schedule need empirical validation

## Session Continuity

Last session: 2026-03-11
Stopped at: Roadmap written; STATE.md initialized
Resume file: None
