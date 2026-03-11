# Pitfalls Research

**Domain:** Graph ML + Molecular Informatics + Active Learning (Flavor Pairing Network)
**Researched:** 2026-03-11
**Confidence:** HIGH (most pitfalls verified via official docs, PyG issues, and peer-reviewed research)

---

## Critical Pitfalls

### Pitfall 1: Information Leakage in Link Prediction Train/Val/Test Splits

**What goes wrong:**
Test target edges are included in the message-passing graph at inference time, inflating evaluation metrics and producing a model that appears to generalize but does not. This can make AUC look 10-20 points higher than real-world performance. In flavor pairing specifically, if the "contains molecule" edges used as negative samples during training overlap with the test evaluation set, the model trivially solves the problem without learning.

**Why it happens:**
Developers adapt node-classification PyG patterns for link prediction by tacking on a decoder — they forget to strip test edges from the edge_index before feeding the graph to the message-passing layers. PyG's `RandomLinkSplit` handles this correctly but must be explicitly configured with `is_undirected=True`, `neg_sampling_ratio`, and `add_negative_train_samples=True`. Skipping these options silently produces leaky splits.

**How to avoid:**
Use `torch_geometric.transforms.RandomLinkSplit` with `edge_types` specified for each edge type in the HeteroData object. Verify that `data['ingredient', 'pairs_with', 'ingredient'].edge_index` at test time contains zero edges from the test label set. Write an assertion that checks overlap is empty before training starts.

**Warning signs:**
- Val AUC > 0.95 on the first epoch of training
- AUC drops sharply on a held-out hand-labeled subset not used in any split
- Surprise scores are uniformly high — the model has memorized co-occurrence

**Phase to address:** Data pipeline / graph construction phase (before model training begins)

---

### Pitfall 2: NetworkX-to-HeteroData Node Index Misalignment

**What goes wrong:**
When constructing the heterogeneous graph manually (ingredient nodes, molecule nodes) using NetworkX and then converting to PyG HeteroData, node integer indices in the edge_index tensor do not correspond to the correct rows in the node feature matrix. Ingredient "tomato" becomes index 4 in NetworkX but index 47 in the HeteroData tensor after conversion. This produces silent corruption — the model trains without errors but learns on misaligned features.

**Why it happens:**
`torch_geometric.utils.from_networkx` calls `nx.convert_node_labels_to_integers` internally, but for heterogeneous graphs, PyG does NOT have a first-class `from_networkx` equivalent. The conversion must be done manually per node type. Developers build a global NetworkX graph, extract edges, and forget that indices must be scoped per node type (0..N_ingredients for ingredient nodes, 0..N_molecules for molecule nodes), not globally.

**How to avoid:**
Maintain explicit `ingredient_id_to_idx` and `molecule_id_to_idx` dictionaries during graph construction. Populate `data['ingredient'].x`, `data['molecule'].x`, and edge tensors using these mappings exclusively. Never use NetworkX's auto-assigned integer IDs as PyG indices. Add a validation function that spot-checks 20 random edges and confirms source/target feature rows match expected ingredient/molecule names.

**Warning signs:**
- Attention weights on trivial neighbors are low across all nodes
- Model outputs are insensitive to ingredient selection in the UI
- Manually tracing a known "good" pairing (e.g., strawberry-chocolate via ethyl butyrate) yields wrong molecule neighbors

**Phase to address:** Graph construction phase

---

### Pitfall 3: FlavorDB2 / FooDB Entity Name Mismatch on Join

**What goes wrong:**
FlavorDB2 uses ingredient names like "Lamb, shoulder, arm" while FooDB uses "Lamb" or "Lamb shoulder." A naive inner join on ingredient name discards 40-60% of valid ingredient matches, silently shrinking the graph below the 500-ingredient threshold without throwing an error. The remaining joined data introduces systematic Western-cuisine bias since non-Western ingredients have more name variation.

**Why it happens:**
Both databases were built independently with no common identifier. FlavorDB2 encodes ingredients from its own taxonomy; FooDB uses food-science nomenclature. Simple string equality misses plurals, parenthetical qualifiers, and regional name variations.

**How to avoid:**
Use fuzzy string matching (RapidFuzz, `fuzz.token_sort_ratio > 85`) as a first pass, then manual review of matches below 95 similarity. Create a canonical `ingredient_canonical_name` field early and use it as the join key throughout the entire pipeline. Log all unmatched FooDB entries for manual inspection. For the 500-ingredient validation check, also log how many ingredients have FooDB enrichment vs. FlavorDB-only — a ratio below 0.4 indicates join quality problems.

**Warning signs:**
- Graph validates at exactly 500 ingredients (minimum threshold) despite FlavorDB2 having 936 natural ingredients
- All FooDB macronutrient fields are NaN for a large fraction of ingredients
- Non-Western ingredients (Asian, African) are underrepresented in node count

**Phase to address:** Data pipeline phase (FlavorDB2 + FooDB ingestion)

---

### Pitfall 4: PubChem API Rate Limiting Causing Silent Feature Gaps

**What goes wrong:**
PubChem enforces 5 requests/second and 400 requests/minute hard limits. For 2000+ molecules, a naive sequential fetch triggers a 503 block within 2-3 minutes. When the block hits mid-batch, SMILES strings for some molecules are missing. If this isn't caught, RDKit feature computation skips those molecules silently (or returns NaN), producing molecule nodes with zero-filled feature vectors that appear valid but carry no information.

**Why it happens:**
Developers add `time.sleep(0.2)` between requests (5/sec), which satisfies the per-second limit but still exceeds the 400/minute limit during burst fetches. The PubChem REST API returns HTTP 503 (not 429) for rate-limit violations, which is easy to conflate with server errors.

**How to avoid:**
Implement a token bucket with a 400/minute ceiling (not just 5/second). Use exponential backoff on 503 responses. Cache all fetched SMILES to `data/raw/pubchem_cache.json` immediately upon retrieval — never re-fetch already-retrieved molecules. After the fetch loop, assert that all molecule IDs have a non-null SMILES entry and log any gaps before proceeding to RDKit feature computation.

**Warning signs:**
- Fetch run completes suspiciously fast (< 5 minutes for 2000 molecules)
- `pubchem_cache.json` has fewer entries than the molecule list
- Molecule feature matrix contains rows of all zeros or NaNs

**Phase to address:** Data pipeline phase (PubChem + RDKit molecular feature computation)

---

### Pitfall 5: RDKit SMILES Sanitization Failures Silently Dropping Molecules

**What goes wrong:**
`Chem.MolFromSmiles(smiles)` returns `None` for SMILES that fail RDKit sanitization (valence errors, KekulizeException, aromatic nitrogen issues). If the calling code does not check for `None`, downstream `Chem.rdMolDescriptors.CalcTPSA(mol)` raises an AttributeError — or worse, if using a try/except that swallows the error, the molecule is silently assigned zero-vector features.

**Why it happens:**
PubChem SMILES can contain ring systems or charged atoms that are chemically valid by PubChem's rules but fail RDKit's stricter sanitization. This is documented behavior — RDKit enforces valence constraints that PubChem does not. Aromatic nitrogen (common in flavor compounds like pyrazines and indoles) is particularly prone to kekulization errors.

**How to avoid:**
Always check `mol is not None` after `MolFromSmiles`. Log all failed SMILES with their molecule ID and the sanitization error type. For nitrogen-containing aromatics, use `Chem.SanitizeMol(mol, catchErrors=True)` and inspect the error flags before discarding. If fewer than 90% of molecules parse successfully, treat that as a pipeline failure, not a data-cleaning detail.

**Warning signs:**
- Morgan fingerprint matrix has many identical all-zero rows
- Molecule nodes cluster at the origin in UMAP visualization of features
- Pyrazine, indole, or other nitrogen-aromatic flavor compounds are absent from the graph

**Phase to address:** Data pipeline phase (RDKit feature computation)

---

### Pitfall 6: GAT Self-Loops on Bipartite Edge Types Causing Training Errors

**What goes wrong:**
When applying GAT attention to heterogeneous bipartite edges (e.g., ingredient → molecule "contains" edges), PyG's GATConv attempts to add self-loops by default. Self-loops are undefined for bipartite graphs because the source and destination node types differ — this raises a runtime error or silently corrupts the attention computation depending on the PyG version.

**Why it happens:**
GATConv's `add_self_loops=True` default is designed for homogeneous graphs. Developers copy standard GATConv usage into HeteroConv wrappers without reading the bipartite-graph caveat in the PyG docs.

**How to avoid:**
Set `add_self_loops=False` on every GATConv instance inside the HeteroConv that handles ingredient↔molecule edges. For ingredient↔ingredient edges (homogeneous), self-loops are valid and can remain. Add this as an explicit comment in the model code so it is not accidentally "fixed" later.

**Warning signs:**
- `ValueError: Cannot add self-loops to heterogeneous edges` at model instantiation
- Attention weights are NaN or uniform across all neighbors (corrupted computation in older PyG versions)
- Model raises no error but loss is constant from epoch 1 onward

**Phase to address:** GNN model construction phase

---

### Pitfall 7: PyG / PyTorch / CUDA Version Incompatibility

**What goes wrong:**
PyTorch Geometric has strict version coupling with PyTorch and (when using CUDA) the CUDA toolkit. Installing the wrong combination produces cryptic import errors or silent CPU-fallback that makes GPU training appear unavailable. On macOS, PyG's metal/MPS support has edge-case bugs in certain versions.

**Why it happens:**
`pip install torch-geometric` installs the latest PyG regardless of the installed PyTorch version. The correct installation requires matching the wheel to the exact PyTorch + CUDA version. This is documented but easy to miss.

**How to avoid:**
Pin all versions in `requirements.txt`: `torch==2.2.x`, `torch-geometric==2.5.x`, `torch-scatter`, `torch-sparse` (or the sparse-free install path for PyG ≥ 2.3). Test the full import chain (`from torch_geometric.data import HeteroData`) in a clean environment before any model code is written. For CPU-only (no CUDA), use the `cpu` wheel variant explicitly.

**Warning signs:**
- `ImportError: cannot import name 'scatter'` or `CUBLAS_STATUS_NOT_INITIALIZED`
- Training loop runs but `torch.cuda.is_available()` is False when GPU is expected
- `torch_geometric.__version__` mismatches the installed PyTorch major version

**Phase to address:** Environment setup phase (first phase)

---

### Pitfall 8: Active Learning Cold Start — Uncertainty Sampling Fails Before Sufficient Training

**What goes wrong:**
In the first few epochs, the GAT model has not learned meaningful representations. Uncertainty sampling on a freshly-initialized or minimally-trained model selects pairs based on random initialization noise, not genuine model uncertainty. The top-20 most uncertain pairs presented to the user are essentially arbitrary — user feedback in this phase poisons the fine-tuning data with noise rather than signal.

**Why it happens:**
The active learning loop is triggered as soon as training completes, regardless of how converged the model is. Model confidence (from sigmoid output) clusters around 0.5 for all pairs when the model is undertrained, making all pairs appear equally uncertain.

**How to avoid:**
Gate the active learning loop behind a minimum training metric: require validation AUC ≥ 0.70 before enabling uncertainty sampling. Display a "model confidence" indicator in the UI so the user knows whether feedback will be meaningful. Log the entropy distribution of all candidate pairs before each active learning round — if mean entropy > 0.45 across all pairs, skip the round and prompt more training first.

**Warning signs:**
- The top-20 uncertain pairs change completely between consecutive active learning rounds with no new feedback
- All 20 uncertain pairs are from the same ingredient (model has collapsed representation for one ingredient type)
- AUC delta shown in the UI is negative after incorporating user feedback

**Phase to address:** Active learning fine-tuning phase

---

### Pitfall 9: Catastrophic Forgetting During Active Learning Fine-Tuning

**What goes wrong:**
The 10-epoch fine-tuning run on `feedback.csv` overwrites the pretrained weights learned from the full dataset. After 3-4 rounds of user feedback (30-40 epochs of fine-tuning on a tiny dataset of ~20-80 samples), the model's performance on ingredient pairs the user never rated degrades significantly. The graph explorer shows increasingly strange recommendations over time.

**Why it happens:**
The fine-tuning loop trains only on feedback samples without any replay of the original training distribution. With a learning rate carried over from full training, 10 epochs on 20-80 samples is sufficient to substantially shift weights away from the global minimum learned on thousands of pairs.

**How to avoid:**
During fine-tuning, use a learning rate 10x lower than full training (e.g., 1e-5 vs 1e-4). Mix feedback samples with a random sample of 5x the feedback size from the original training set in each fine-tuning batch (experience replay). Checkpoint the pre-fine-tuning model weights before each active learning round so the user can reset if recommendations degrade.

**Warning signs:**
- Pairings that were highly scored before feedback rounds now score near zero
- The "AUC delta" shown in the UI is based only on the feedback set — implement a held-out global validation check as well
- User feedback on the same pair changes the scores of unrelated pairs drastically

**Phase to address:** Active learning fine-tuning phase

---

### Pitfall 10: InfoNCE Contrastive Loss Temperature Miscalibration

**What goes wrong:**
The fixed InfoNCE temperature (τ = 0.07 per project spec) may produce gradient instability during early training. At τ = 0.07, the loss is very sensitive to small differences in similarity scores — if molecular features are poorly initialized or the graph is sparse, gradients explode in the first few batches. Conversely, if the molecular overlap between negative pairs is high (as it is in food flavor compounds — many ingredients share pyrazines or esters), τ = 0.07 creates hard negatives that are chemically similar, causing the model to push apart related compounds that should be nearby.

**Why it happens:**
τ = 0.07 is standard for image contrastive learning (SimCLR, MoCo) where negatives are semantically dissimilar. Food flavor molecules violate this assumption — vanilla and coffee share many volatile compounds, so a hard-negative regime forces the model to learn spurious distinctions.

**How to avoid:**
Start with τ = 0.1–0.2 for molecular contrastive pairs and tune downward. Add gradient clipping (`torch.nn.utils.clip_grad_norm_`, max_norm=1.0) to the training loop to guard against early-training instability regardless of temperature. Log the InfoNCE loss component separately from the molecular and recipe supervision losses to detect if contrastive loss is dominating or collapsing.

**Warning signs:**
- Training loss spikes then NaN in the first 5 epochs
- The InfoNCE loss component is 10x larger than the recipe co-occurrence supervision loss
- Molecule embeddings collapse to a single point in UMAP (mode collapse from overly-aggressive contrastive loss)

**Phase to address:** GNN training phase

---

### Pitfall 11: PyVis Graph Rendering Failure Beyond ~500 Nodes in Streamlit

**What goes wrong:**
PyVis renders graphs via an HTML iframe in Streamlit using a vis.js canvas. Graphs with more than ~500-1000 nodes cause the browser to hang, the Streamlit tab to become unresponsive, or the page to reload entirely. The flavor graph has 500+ ingredients + 2000+ molecules — rendering even a 2-hop neighborhood of a central ingredient can pull in hundreds of nodes.

**Why it happens:**
PyVis passes the full node/edge list to the browser in a single iframe. vis.js has no built-in virtualization or level-of-detail reduction. Streamlit's iframe component has no size cap on the embedded graph.

**How to avoid:**
Never render more than 1-hop neighbors in the PyVis explorer (enforced in code, not just documentation). Cap the displayed graph at 50 nodes and 150 edges, selecting by edge weight (top connections only). Show a node count warning if the neighborhood exceeds the cap. Provide a "download full subgraph as JSON" option instead of rendering larger views.

**Warning signs:**
- Browser tab CPU spikes to 100% when opening the graph explorer page
- Selecting a highly-connected ingredient (e.g., "lemon") crashes the visualization
- PyVis iframe height is set to a fixed pixel value that cuts off the graph (common copy-paste error)

**Phase to address:** Streamlit UI phase (graph explorer page)

---

### Pitfall 12: AllRecipes Scraping Rate-Limit / Bot-Block Causing Incomplete Co-Occurrence Data

**What goes wrong:**
AllRecipes actively detects scraping behavior using AI-based bot detection that considers User-Agent, request timing, and browsing history patterns. Even with proper delays, fetching 500 recipes across 10 categories triggers a 429 or soft-block (returns empty pages or redirects) after 50-100 requests per session. Incomplete scraping data means some cuisine categories are under-represented in the co-occurrence graph, biasing edge weights.

**Why it happens:**
A single IP with a static User-Agent making sequential requests at fixed intervals is detectable even with `time.sleep(2)`. AllRecipes uses Cloudflare or similar WAF that tracks request fingerprints across a session.

**How to avoid:**
This is already flagged in PROJECT.md as a known risk. Treat AllRecipes as a supplemental source with expected data loss. Prioritize RecipeNLG or Recipe1M+ (open datasets) as the primary co-occurrence source — they require no scraping and have millions of recipes. For AllRecipes, implement random delays (2-8 seconds), rotate User-Agents, and use session-based cookies. Accept up to 50% scrape failure and document it. Assert a minimum of 50,000 co-occurrence pairs from the combined dataset before proceeding to graph construction.

**Warning signs:**
- HTML responses contain "please verify you are human" text
- All scraped pages return HTTP 200 but ingredient lists are empty
- Recipe count per category drops below 50 after scraping

**Phase to address:** Data pipeline phase (recipe co-occurrence ingestion)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode ingredient/molecule indices in early notebooks | Faster prototyping | Index drift when data pipeline is re-run; silent corruption | Never in production code — use the canonical mapping dicts from day 1 |
| Skip the PubChem cache and re-fetch on every pipeline run | No cache management code | Hits rate limits, slow, burns quota | Never — cache is mandatory given rate limits |
| Use a fixed random seed without seeding all PyG samplers | Reproducible on one machine | Different results on re-run due to PyG's DataLoader workers | Always seed, but note PyG requires seeding `torch`, `numpy`, `random`, AND `torch_geometric` separately |
| Train on full batch instead of mini-batches for speed | Simpler code | OOM on larger graphs, not extensible | Acceptable for CPU-only demo with < 1000 ingredient nodes |
| Use `torch.float32` for edge labels in link prediction | No type conversion needed | `BCEWithLogitsLoss` requires float; `CrossEntropyLoss` requires long — wrong dtype silently produces NaN loss | Never mix up — be explicit about label dtype |
| Display raw stack traces in Streamlit on API/model errors | Fast debugging | Portfolio demo looks broken and unprofessional | Never — all user-facing exceptions must be caught and shown as friendly error messages |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| PubChem REST API | Using `requests.get` without timeout; server hangs cause pipeline to block indefinitely | Always use `requests.get(url, timeout=10)` with retry logic |
| PubChem REST API | Fetching by name (fuzzy match) instead of CID | Resolve name → CID first using the `/compound/name/{name}/cids/JSON` endpoint, then fetch by CID for deterministic results |
| FlavorDB2 entities_json endpoint | Assuming endpoint is paginated; actually returns all entities at once for IDs 1–1000 but returns 404 for nonexistent IDs | Iterate IDs 1–1000, skip 404s, do not assume sequential ID space is fully populated |
| FooDB CSVs | Using `compounds.csv` alone; this table lacks food-to-compound linkage | Join `compounds.csv` → `contents.csv` → `foods.csv` to resolve the many-to-many food-compound relationship |
| Anthropic Claude API (recipe generation) | Sending the full graph embedding as context (too large) | Send only the top-5 shared molecules with their SMILES and common names; keep prompt under 1000 tokens for fast response |
| PyVis in Streamlit | Using `net.show("graph.html")` which writes to disk and requires file serving | Use `net.generate_html()` and embed with `st.components.v1.html()` directly |
| PyTorch Geometric RandomLinkSplit on HeteroData | Applying the transform to the entire HeteroData object; it processes all edge types including non-prediction edges | Use `edge_types` parameter to specify only the prediction edge type (e.g., ingredient-pairs_with-ingredient) |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Computing Morgan fingerprints inside the training loop per batch | Training epoch takes 10+ minutes | Pre-compute all fingerprints once during data pipeline; store as tensors | Immediately — molecular feature computation should never happen at training time |
| Loading full HeteroData graph to CPU/GPU for every forward pass | OOM on systems with < 16GB RAM | Use PyG's `NeighborLoader` for mini-batch training; the full flavor graph with 2500 nodes is borderline for full-batch on 8GB GPU | At ~2500 nodes with 3 GAT layers, full-batch is feasible but tight; check memory at 500 ingredients + 2000 molecules |
| Re-running the entire data pipeline on every Streamlit startup | App takes 5+ minutes to load | Separate pipeline from app; save final HeteroData object as `graph/flavor_graph.pt` and load at startup | First run in demo without pre-built graph artifact |
| Calling `networkx.Graph.degree()` to compute edge weights for large graphs | O(N²) co-occurrence counting | Use counter-based co-occurrence from pandas groupby; never use NetworkX for counting operations | At > 100k recipe-ingredient pairs |
| Logging every PubChem fetch response to console during pipeline run | Terminal floods and pipeline appears to hang | Use Python `logging` with level INFO; log only errors and milestones | Immediately when fetching 2000+ molecules |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Hardcoding Anthropic API key in source code or notebook | Key exposure in git history; API cost from unauthorized use | Use `.env` file with `python-dotenv`; add `.env` to `.gitignore` immediately at project init |
| Storing user feedback (ingredient pair ratings) without sanitization | Injection into `feedback.csv` if app is ever exposed beyond localhost | Since this is local-only, low risk; but still validate that feedback values are integers 1-5 and ingredient names match the known ingredient list |
| Trusting SMILES strings from PubChem directly in RDKit without error handling | Process crash if malformed SMILES is passed to Chem.MolFromSmiles | Always wrap SMILES parsing in try/except and validate the returned `mol` object is not None |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing raw "surprise score" float (e.g., 0.7324) without context | User doesn't understand if 0.73 is good or bad | Display as a percentile rank ("Top 12% most surprising") or labeled bar (Low / Medium / High / Surprising) |
| Displaying molecule names as PubChem CIDs or SMILES strings | Users see "CID 5932" instead of "Vanillin" | Always resolve CIDs to common names during the pipeline; store common_name in the molecule node attributes |
| Active learning page shows "AUC delta: +0.003" as the only feedback signal | User doesn't know if their feedback did anything meaningful | Show before/after AUC, a sample of pairs that changed ranking, and a "model is improving" / "more feedback needed" message |
| Recipe generation page (Page 4) has no loading indicator during Claude API call | User thinks the page is broken during the 5-10 second API call | Use `st.spinner("Generating recipe...")` wrapping the API call |
| PyVis graph shows ingredient names with underscores or database IDs | Looks raw and unpolished in portfolio demo | Normalize display names: title case, replace underscores with spaces, strip numeric suffixes |

---

## "Looks Done But Isn't" Checklist

- [ ] **Data pipeline:** Often missing FooDB join — verify that `ingredient.macronutrients` fields are populated for at least 60% of nodes, not just that the join code exists
- [ ] **Molecular features:** Often missing sanitization failure log — verify a `data/logs/rdkit_failures.csv` file exists and has been reviewed before proceeding to training
- [ ] **Graph construction:** Often missing the edge-type validation — verify that all three edge types (contains, co-occurs, structural-similarity) have at least 1000 edges each, logged at pipeline end
- [ ] **Link prediction split:** Often missing the leakage check — verify test edges are absent from the message-passing graph by running the overlap assertion, not just trusting that `RandomLinkSplit` was called
- [ ] **Active learning:** Often missing the held-out global validation — verify AUC is tracked on the full validation set (not just the feedback set) after each fine-tuning round
- [ ] **Streamlit UI:** Often missing user-facing error handling — verify every external call (Claude API, model inference, graph load) has a try/except with a friendly `st.error()` message
- [ ] **PubChem cache:** Often missing cache validation — verify that re-running the pipeline with an existing cache does not make any new HTTP requests
- [ ] **Surprise score:** Often missing calibration — verify the formula produces non-trivial distributions: at least 20% of pairs should score > 0.6 and at least 20% should score < 0.2

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Information leakage discovered post-training | HIGH | Discard trained weights; rebuild split with `RandomLinkSplit`; retrain from scratch; re-evaluate all reported metrics |
| Node index misalignment discovered post-training | HIGH | Rebuild graph from scratch using canonical index maps; retrain; no shortcut — corrupted features cannot be fixed without reconstruction |
| FlavorDB/FooDB join too sparse (< 300 matched ingredients) | MEDIUM | Implement fuzzy matching with RapidFuzz; manually review top-50 unmatched pairs; augment with FooDB synonym table |
| PubChem cache incomplete (> 10% gaps) | LOW | Re-run fetch with exponential backoff; gaps in cache are additive on re-run if cache-check logic is correct |
| Active learning feedback poisoning (bad user ratings) | LOW | Delete corrupt rows from `feedback.csv` manually; re-run fine-tuning; maintain checkpoint before each AL round |
| PyG version incompatibility discovered mid-project | MEDIUM | Pin versions in `requirements.txt`, create fresh virtualenv, reinstall with correct wheel variants |
| PyVis graph crash in demo | LOW | Pre-generate the PyVis HTML for top-10 most common ingredients at startup; serve cached HTML instead of generating on-the-fly |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Link prediction information leakage | Graph construction / data pipeline | Run overlap assertion between test label edges and message-passing edge_index |
| NetworkX-to-HeteroData index misalignment | Graph construction | Spot-check 20 random edges: confirm source/target feature rows match expected node names |
| FlavorDB2/FooDB name mismatch | Data pipeline — FlavorDB2 + FooDB ingestion | Assert ≥ 300 matched ingredients with macronutrient fields populated |
| PubChem rate limiting + cache gaps | Data pipeline — molecular feature computation | Assert cache covers 100% of molecule IDs before RDKit processing |
| RDKit SMILES sanitization failures | Data pipeline — molecular feature computation | Log failure rate; assert < 10% failure; review `rdkit_failures.csv` |
| GAT self-loops on bipartite edges | GNN model construction | Unit test: instantiate model, run forward pass on toy HeteroData, verify no NaN in attention weights |
| PyG/PyTorch version incompatibility | Environment setup (Phase 1) | Run `from torch_geometric.data import HeteroData; print(torch_geometric.__version__)` in clean env |
| Active learning cold start | Active learning phase | Gate AL loop behind AUC ≥ 0.70; log entropy distribution of candidate pairs before each round |
| Catastrophic forgetting in fine-tuning | Active learning phase | Track global validation AUC (not just feedback-set AUC) after every fine-tuning round |
| InfoNCE temperature instability | GNN training phase | Log each loss component separately; add gradient clipping; tune τ starting from 0.1 |
| PyVis graph performance collapse | Streamlit UI phase | Cap subgraph at 50 nodes; test with "lemon" (high-degree node) before demo |
| AllRecipes scraping failure | Data pipeline — recipe co-occurrence ingestion | Assert ≥ 50,000 co-occurrence pairs from combined open + scraped sources |

---

## Sources

- [Pitfalls in Link Prediction with GNNs (ACM WSDM 2024)](https://dl.acm.org/doi/10.1145/3616855.3635786) — authoritative paper on target-link inclusion leakage
- [PyG Heterogeneous Graph Learning docs](https://pytorch-geometric.readthedocs.io/en/latest/notes/heterogeneous.html) — self-loops on bipartite edges, HeteroConv patterns
- [PyG HeteroData conversion from NetworkX (Discussion #4457)](https://github.com/pyg-team/pytorch_geometric/discussions/4457) — manual index management requirement
- [PubChem PUG-REST best practices](https://iupac.github.io/WFChemCookbook/datasources/pubchem_pugrest1.html) — rate limits: 5 req/sec, 400 req/min
- [PubChemPy advanced usage](https://docs.pubchempy.org/en/latest/guide/advanced.html) — rate limiting guidance
- [RDKit KekulizeException and nitrogen aromaticity (Oxford Protein Informatics, 2024)](https://www.blopig.com/blog/2024/09/out-of-the-box-rdkit-valid-is-an-imperfect-metric-a-review-of-the-kekulizeexception-and-nitrogen-protonation-to-correct-this/)
- [RDKit sanitization blog (Greg Landrum, 2025)](https://greglandrum.github.io/rdkit-blog/posts/2025-06-27-sanitization-and-file-parsing.html)
- [FlavorDB2 paper (Goel et al., 2024)](https://ift.onlinelibrary.wiley.com/doi/10.1111/1750-3841.17298) — data coverage: 936 natural ingredients, 25,595 molecules
- [Temperature-Free InfoNCE (arXiv 2501.17683, 2025)](https://arxiv.org/abs/2501.17683) — temperature scaling causes gradient problems in InfoNCE
- [Contrastive Learning temperature sensitivity (Lilian Weng)](https://lilianweng.github.io/posts/2021-05-31-contrastive/) — τ calibration principles
- [Streamlit + PyVis large graph error (Streamlit community)](https://discuss.streamlit.io/t/streamlit-pyvis-error-when-displaying-large-network/28501) — > 1000 nodes causes page reload
- [Active learning cold start problem (NeurIPS/ICML research 2024)](https://arxiv.org/abs/2403.03728) — diversity-first then uncertainty sampling
- [Catastrophic forgetting in continual fine-tuning](https://arxiv.org/abs/2308.08747) — EWC and replay strategies
- [Uncertainty Sampling for Graphs (arXiv 2405.01462, 2024)](https://arxiv.org/abs/2405.01462) — first benchmark of uncertainty sampling on graphs

---
*Pitfalls research for: Graph ML + Molecular Informatics + Active Learning (Flavor Pairing Network)*
*Researched: 2026-03-11*
