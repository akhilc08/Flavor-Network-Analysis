# Flavor Pairing Network

## What This Is

An end-to-end ML system that discovers non-obvious but scientifically grounded food ingredient pairings using a Graph Neural Network trained on molecular flavor data, real-world recipe co-occurrence, and rich multimodal ingredient features. Designed as a polished portfolio/demo project showcasing graph ML, active learning, and data engineering. A Streamlit UI lets users explore surprising pairings, rate them to improve the model, and generate AI-backed recipes.

## Core Value

The model surfaces ingredient pairs that are molecularly compatible but culturally underused — the surprise score is the key metric, not just similarity.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Data pipeline scrapes FlavorDB2 (entities_json endpoint, ids 1–1000) and extracts ingredients + flavor molecules
- [ ] FooDB compounds/foods CSVs downloaded and joined to enrich ingredients with macronutrients and additional compounds
- [ ] Recipe co-occurrence data sourced from BOTH open datasets (Recipe1M+ or RecipeNLG) AND AllRecipes scraping (10 categories × 500 recipes)
- [ ] RDKit computes molecular features from SMILES via PubChem API (MW, logP, HBD/HBA, rotatable bonds, TPSA, Morgan fingerprints)
- [ ] Multimodal ingredient features: texture embedding, temperature affinity, cultural context vector, flavor profile multi-hot vector
- [ ] Heterogeneous graph built with NetworkX → PyTorch Geometric HeteroData (ingredient nodes, molecule nodes, co-occurrence/contains/structural-similarity edges)
- [ ] Graph Attention Network (3 GAT layers, 8 heads, 256 hidden, 128 output) with dual supervision (molecular + recipe + contrastive InfoNCE loss)
- [ ] Graph validates at ≥500 ingredient nodes and ≥2000 molecule nodes before training
- [ ] Surprise scoring formula implemented: pairing_score × (1 - recipe_familiarity) × (1 - molecular_overlap × 0.5)
- [ ] Active learning loop: uncertainty sampling on top-20 most uncertain pairs, user feedback appended to feedback.csv, 10-epoch fine-tuning on feedback
- [ ] Streamlit UI — Page 1: ingredient search → top 10 pairings with radar chart, shared molecules, cuisine context
- [ ] Streamlit UI — Page 2: rate top-5 uncertain pairs (1–5 stars), triggers fine-tuning, shows AUC delta
- [ ] Streamlit UI — Page 3: interactive PyVis flavor graph explorer centered on selected ingredient
- [ ] Streamlit UI — Page 4: select 2–3 surprise-pair ingredients → Claude API (claude-sonnet) generates recipe with molecular pairing rationale
- [ ] Project follows specified directory structure (data/, graph/, model/, scoring/, app/)
- [ ] Inline comments explain non-obvious design decisions (dual supervision, surprise scoring, active learning query strategy)

### Out of Scope

- Mobile app or non-Streamlit UI — web-first, polish the Streamlit demo
- Real-time multi-user deployment — single-user local demo is sufficient
- Persistent user accounts / login — no auth needed
- Video or audio content — text + charts + interactive graph only

## Context

- This is a greenfield portfolio project; no existing codebase
- The key research insight is the "flavor pairing hypothesis" from Ahn et al. 2011 — ingredients sharing flavor compounds tend to pair well in Western cuisines, but the model should discover cross-cultural surprises
- AllRecipes scraping may encounter bot-blocking; use delays, user-agents, and accept partial data loss; supplement heavily with open recipe datasets
- Recipe generation uses Claude API (Anthropic SDK, claude-sonnet-4-5 or latest), not OpenAI
- RDKit requires conda/pip install separately; note in requirements
- PyTorch Geometric has version-sensitive CUDA deps — pin versions in requirements.txt
- Graph training is compute-intensive; checkpoint frequently; CPU training should still be feasible (just slower)

## Constraints

- **Tech Stack**: Python 3.11, PyTorch + PyG, RDKit, NetworkX, Streamlit, Plotly, PyVis, Anthropic SDK, Pandas/NumPy
- **API Keys**: PubChem (free, no key), Anthropic API key (required for Page 4), FlavorDB2 (public endpoint, no key)
- **Data**: Must validate graph has ≥500 ingredients + ≥2000 molecules before model training
- **Demo Quality**: UI must be polished enough to showcase in a portfolio — clear labeling, charts load reliably, no raw stack traces visible to user

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Recipe generation via Claude API (not OpenAI) | User preference; Anthropic SDK | — Pending |
| Dual recipe data sources (open datasets + AllRecipes) | More co-occurrence data improves edge quality in graph | — Pending |
| Surprise score formula weights molecular_overlap at 0.5 penalty | Penalize fully but not completely obvious molecule overlap | — Pending |
| InfoNCE temperature = 0.07 | Standard for contrastive learning; may need tuning | — Pending |

---
*Last updated: 2026-03-11 after initialization*
