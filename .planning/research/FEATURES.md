# Feature Research

**Domain:** Flavor pairing / food ingredient GNN ML system (portfolio/demo)
**Researched:** 2026-03-11
**Confidence:** MEDIUM — table stakes and differentiators are well-supported by FlavorGraph, KitcheNette, and Ahn 2011 research; active learning demo norms from community sources (LOW-MEDIUM); no direct competitors with identical scope exist

---

## Feature Landscape

### Table Stakes (Users Expect These)

A hiring reviewer or technical audience will assume these exist. Missing any of them makes the demo feel unfinished or like a notebook exercise rather than a system.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Ingredient search with autocomplete | Every food/recommendation demo starts here; without it the system is inaccessible | LOW | Streamlit text_input + fuzzy match on ingredient list; must cover at least 500 ingredients |
| Top-N pairing results list | The core output — what ingredients go with X? FlavorGraph, KitcheNette, and Foodpairing all show this | LOW | Top 10 sorted by pairing score; show score numerically or as a bar |
| Shared flavor molecule display | The scientific hook that distinguishes this from "just ML"; Ahn 2011 is what makes flavor pairing credible | MEDIUM | List 3–5 shared molecules per pair with common names, not just SMILES |
| Radar/spider chart for ingredient profile | Standard visual shorthand for multi-dimensional flavor profiles (sweet/sour/bitter/umami/etc.) | LOW | Plotly radar chart; feeds into explainability of why a pair is recommended |
| Network graph visualization | Graph ML demos are expected to show the graph — without it the GNN aspect is invisible | MEDIUM | PyVis centered on selected ingredient; node size = degree or prevalence, edge weight = shared compounds |
| Pairing score with label | Numeric score alone is meaningless; needs a label ("Surprising", "Classic", "Unusual") | LOW | Map score ranges to labels; show surprise score separately from raw pairing score |
| Working UI with no raw tracebacks | Portfolio standard; stack traces visible to users = immediately disqualifying for a demo | LOW | Streamlit try/except with user-friendly error messages throughout |
| Data source attribution | Academic audience expects to see FlavorDB2, FooDB, Recipe1M+ cited in the UI | LOW | Footer or sidebar with data sources; links optional |

### Differentiators (Competitive Advantage)

These are what make this project a strong portfolio piece for a graph ML / ML engineering role rather than a generic food app. The core differentiation is the combination of molecular data + GNN + active learning in a single coherent demo — no existing public demo does all three.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Surprise score metric (not just similarity) | Shows understanding of recommendation beyond naive cosine similarity; the formula `pairing_score × (1 - recipe_familiarity) × (1 - molecular_overlap × 0.5)` is a concrete, defensible design decision | MEDIUM | Critical to explain the formula inline in the UI — the metric is a differentiator only if it is visible and explained |
| Active learning loop with visible AUC delta | Demonstrates that user feedback changes the model, not just a static predictor; shows the full ML lifecycle | HIGH | Show AUC before and after fine-tuning on the rating page; even a small delta (0.01) proves the loop closes |
| Heterogeneous graph architecture exposure | GNN architecture visible in the UI (e.g., a small diagram or description of node types) elevates from "food app" to "graph ML demo" | LOW | A sidebar diagram or tooltip explaining ingredient nodes vs molecule nodes vs edge types is sufficient |
| Cross-cultural pairing surprise detection | The Ahn 2011 finding is that Western cuisines share compounds; surprising pairings often cross cultural boundaries — this project's core scientific claim | MEDIUM | Cuisine context vector in features + flag when a high-surprise pair comes from different culinary traditions |
| AI-generated recipe with molecular pairing rationale | Closes the loop from "what pairs" to "how to actually cook it"; the molecular rationale grounds the LLM output in science rather than generic recipes | MEDIUM | Claude API prompt must explicitly include shared molecules and surprise score as context so the rationale is non-generic |
| Contrastive InfoNCE loss explanation | Few food demo projects explain their loss function; showing a brief inline comment or UI annotation about dual supervision differentiates from MNIST-level ML projects | LOW | A collapsible "Model details" section with loss function description and training stats |
| Uncertainty display per pair | Shows which pairs the model is least confident about — directly teaches the active learning concept to a non-technical viewer | LOW | Badge or annotation on uncertain pairs in the pairing results list |
| t-SNE / embedding space visualization | Visualizing where ingredients cluster in learned embedding space demonstrates that the GNN learned meaningful representations | MEDIUM | Pre-compute t-SNE on all ingredients, color by food category; add to a "Model Internals" tab |

### Anti-Features (Commonly Requested, Often Problematic)

These features look like good additions but create scope traps or dilute the portfolio signal.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| User accounts / login / saved pairings | Makes the app feel "real" and polished | Auth adds infrastructure, session management, and deployment complexity with zero portfolio signal for a graph ML role; single-user local demo is sufficient | None — explicitly note "single-user demo" in the README |
| Real-time multi-user deployment | Portfolio credibility | Kubernetes/cloud deployment is a different skill set; deploying a GNN demo to prod is a rabbit hole; CPU training is slow, inference is fast but serving a GNN in prod needs model-serving infrastructure | A recorded screencast or Loom video walkthrough counts as "deployed" for portfolio purposes |
| Nutritional optimization or diet constraints | Users of food apps often ask for this | Nutritional recommendation is a completely different problem domain; FooDB macronutrients are in the data but optimizing for them pulls the demo away from the "molecular flavor science" story | Use FooDB data only to enrich molecule features, not to add a diet-tracker feature |
| Image recognition of ingredients from photos | Visually impressive | Computer vision is a separate model, separate data pipeline, and separate training loop; it would dominate implementation time and obscure the graph ML work | Use ingredient name search only |
| Mobile-responsive UI | Broad accessibility | Streamlit mobile experience is poor by default; optimizing for mobile takes CSS overrides that fight Streamlit's layout system | Desktop-first; note this in README |
| Batch recipe generation (multiple recipes at once) | "More output = more value" | Claude API costs scale with batch size; multiple recipes dilute the quality of the molecular rationale per recipe | Single recipe per 2–3 ingredient selection; one high-quality rationale beats three mediocre ones |
| Real-time AllRecipes scraping in the UI | Live data feels fresher | Bot-blocking is unpredictable; live scraping in a demo will randomly fail mid-presentation; the graph must be pre-built | Pre-build graph from scraped data; UI shows pre-trained model only |
| Full recipe search (find recipes containing X) | Feels like a natural extension | Recipe search is ElasticSearch / BM25 territory, not GNN territory; it pulls reviewer attention away from the graph ML work | Show recipe co-occurrence counts as a graph edge attribute, not as a search feature |

---

## Feature Dependencies

```
[Data Pipeline: FlavorDB2 + FooDB + Recipe Data]
    └──requires──> [Graph Construction: NetworkX HeteroData]
                       └──requires──> [GNN Training: GAT dual supervision]
                                          └──requires──> [Ingredient Embeddings]
                                                             └──requires──> [Pairing Scoring]
                                                                                └──requires──> [Surprise Score]

[Surprise Score]
    └──requires──> [Recipe Familiarity Metric] (from co-occurrence data)
    └──requires──> [Molecular Overlap Metric] (from FlavorDB2 molecules)

[Active Learning Loop]
    └──requires──> [Trained Model + Uncertainty Estimates]
    └──requires──> [User Rating UI (Page 2)]
    └──requires──> [Fine-tuning Script (10 epochs on feedback.csv)]
    └──requires──> [AUC delta computation]

[Network Graph Explorer (Page 3)]
    └──requires──> [Ingredient Embeddings]
    └──requires──> [Graph Edge Data in memory or serialized]

[AI Recipe Generation (Page 4)]
    └──requires──> [Pairing Scoring (to select 2-3 surprise ingredients)]
    └──requires──> [Shared Molecule List per pair]
    └──requires──> [Claude API key]

[Radar Chart]
    └──requires──> [Multimodal ingredient features: flavor profile multi-hot]

[t-SNE Visualization]
    └──requires──> [Trained GNN embeddings]
    └──enhances──> [Network Graph Explorer (complementary view)]

[Surprise Score label/badge]
    └──enhances──> [Pairing Results List]

[Uncertainty badge on pairs]
    └──enhances──> [Pairing Results List]
    └──enhances──> [Active Learning Loop (explains what Page 2 is selecting)]
```

### Dependency Notes

- **GNN Training requires Graph Construction:** The graph must validate (>=500 ingredients, >=2000 molecules) before training begins. This is a hard gate — training on an underbuilt graph produces useless embeddings.
- **Surprise Score requires both Recipe Familiarity and Molecular Overlap:** Both sub-metrics must be computed at graph-build time. The surprise score cannot be computed post-hoc from embeddings alone.
- **Active Learning requires a trained model:** You cannot show AUC delta until a baseline model exists. Page 2 must be built after the model training phase is complete.
- **AI Recipe Generation requires Surprise Score:** The Claude API prompt must include the molecular rationale (shared molecules + surprise score) to produce non-generic output. Building Page 4 before scoring is complete will produce generic recipes.
- **t-SNE enhances but does not block:** It is a visualization of already-computed embeddings; it can be added as a polish step after core features work.

---

## MVP Definition

### Launch With (v1)

Minimum viable to demonstrate the GNN food pairing concept credibly.

- [x] Data pipeline complete: FlavorDB2 + FooDB + Recipe co-occurrence ingested and cleaned
- [x] Graph built and validated (>=500 ingredients, >=2000 molecules, heterogeneous edges)
- [x] GAT model trained with dual supervision; embeddings serialized to disk
- [x] Pairing scoring with surprise metric implemented and produces non-trivial results
- [x] Page 1: Ingredient search → top 10 pairings with surprise scores, shared molecules, radar chart — the core "wow" moment
- [x] Page 3: Network graph explorer — makes the "GNN" in the title visible and tangible
- [x] Page 2: Active learning rating interface — even if AUC delta is small, the loop closing is the story
- [x] Page 4: Recipe generation with molecular rationale via Claude API
- [x] No raw stack traces visible; graceful error handling throughout

### Add After Validation (v1.x)

Features that polish the demo once the core is working.

- [ ] t-SNE embedding space visualization — add when embeddings are confirmed meaningful; compute offline, display as static Plotly scatter
- [ ] Cross-cultural pairing flag — annotate high-surprise pairs from different culinary traditions; add when cultural context vector is working
- [ ] Collapsible "Model Details" section — loss function, training stats, architecture summary; add as a sidebar panel for technical viewers
- [ ] Uncertainty badges on pairing results — annotate which results are actively queried by the active learning loop; low effort, high explainability value

### Future Consideration (v2+)

Defer these entirely — they are out of scope for a portfolio demo.

- [ ] User accounts / persistent ratings — only needed if demo is deployed for real users; adds auth/infra complexity with no portfolio signal
- [ ] Real-time AllRecipes scraping — scraping bot risk in a live demo is not worth it; all data pre-built
- [ ] Nutritional recommendation features — different problem domain; dilutes the graph ML story
- [ ] Mobile-responsive UI — Streamlit mobile is a CSS fight; not worth it for a desktop portfolio demo

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Ingredient search + top-10 pairings | HIGH | LOW | P1 |
| Shared flavor molecules display | HIGH | MEDIUM | P1 |
| Network graph explorer (PyVis) | HIGH | MEDIUM | P1 |
| Surprise score metric + label | HIGH | MEDIUM | P1 |
| Active learning rating loop + AUC delta | HIGH | HIGH | P1 |
| AI recipe with molecular rationale | HIGH | MEDIUM | P1 |
| Radar chart (flavor profile) | MEDIUM | LOW | P1 |
| Uncertainty badges on pairings | MEDIUM | LOW | P2 |
| t-SNE embedding visualization | MEDIUM | MEDIUM | P2 |
| Cross-cultural pairing flag | MEDIUM | MEDIUM | P2 |
| Model architecture details panel | LOW | LOW | P2 |
| Batch recipe generation | LOW | MEDIUM | P3 |
| Nutritional optimization | LOW | HIGH | P3 |
| User accounts | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch (core demo integrity)
- P2: Should have, add after P1 is working
- P3: Do not build — scope trap or out of domain

---

## Competitor Feature Analysis

| Feature | Ahn 2011 / Flavor Network | FlavorGraph (Sony AI) | KitcheNette | This Project |
|---------|--------------------------|----------------------|-------------|--------------|
| Molecular compound data | Yes (bipartite graph) | Yes (1,561 molecules) | No | Yes (FlavorDB2 + FooDB) |
| Recipe co-occurrence | No | Yes (1M+ recipes) | Yes (300K scored pairs) | Yes (Recipe1M+ + AllRecipes) |
| GNN / graph embedding | No (static graph) | Yes (metapath2vec variant) | No (Siamese NN) | Yes (GAT, heterogeneous) |
| Surprise / novelty metric | Implicit (compound sharing) | No explicit surprise score | Partial (Bayesian Surprise in related work) | Yes (explicit formula) |
| Active learning | No | No | No | Yes (uncertainty sampling) |
| Interactive UI / demo | No (paper figures only) | Minimal (no public UI) | No | Yes (Streamlit 4-page app) |
| LLM recipe generation | No | No | No | Yes (Claude API) |
| Cross-cultural analysis | Yes (Western vs East Asian) | No | No | Partial (cultural context vector) |
| Explainability / rationale | No | No | No | Yes (shared molecules + LLM rationale) |

This project's combination of GNN + active learning + LLM rationale with an interactive UI is differentiated from every known public reference implementation in this domain.

---

## Sources

- [FlavorGraph paper (Scientific Reports, 2021)](https://www.nature.com/articles/s41598-020-79422-8) — graph architecture reference, feature design
- [FlavorGraph GitHub](https://github.com/lamypark/FlavorGraph) — implementation reference
- [NVIDIA FlavorGraph blog](https://developer.nvidia.com/blog/flavorgraph-serves-up-food-pairings-with-ai-molecular-science/) — features and positioning
- [KitcheNette (IJCAI 2019)](https://www.ijcai.org/proceedings/2019/0822.pdf) — Siamese network baseline, Bayesian Surprise metric for novelty
- [Ahn et al. 2011 flavor network](https://pubmed.ncbi.nlm.nih.gov/22355711/) — foundational flavor pairing hypothesis; node/edge visualization conventions
- [Creative Flavor Pairing: RDC Metric (ICCC 2017)](https://computationalcreativity.net/iccc2017/ICCC_17_accepted_submissions/ICCC-17_paper_40.pdf) — surprise/novelty metric design
- [Food Pairing Unveiled (arXiv 2024)](https://arxiv.org/abs/2406.15533) — recommender systems for recipe creation dynamics
- [FlavorDiffusion (arXiv 2025)](https://arxiv.org/html/2502.06871v1) — SOTA comparison; shows diffusion models entering this space
- [Explainable food recommendation (JMIR 2025)](https://mhealth.jmir.org/2025/1/e51271) — rationale display patterns for food systems
- [Active Learning overview (Lil'Log)](https://lilianweng.github.io/posts/2022-02-20-active-learning/) — uncertainty sampling conventions for portfolio demos
- [Adaptive dynamic hypergraph food recommendation (Scientific Reports 2025)](https://www.nature.com/articles/s41598-025-30496-2) — higher-order interaction modeling; confirms GNNs are current SOTA in food recommendation

---
*Feature research for: Flavor Pairing Network — GNN + active learning + LLM demo*
*Researched: 2026-03-11*
