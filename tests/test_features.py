"""Phase 2 Feature Engineering test scaffold.

All tests are marked xfail until implementation in Plans 02-04 completes.
Run with: conda run -n flavor-network python -m pytest tests/test_features.py -x -q
"""
import pytest
from pathlib import Path
import pandas as pd


# ---------------------------------------------------------------------------
# FEAT-01: PubChem SMILES fetch (data/fetch_smiles.py)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_smiles_cache_coverage():
    """FEAT-01: pubchem_cache.json exists and covers all pubchem_ids in molecules.csv."""
    cache_path = Path("data/raw/pubchem_cache.json")
    if not cache_path.exists():
        pytest.xfail("pubchem_cache.json not yet generated")

    import json
    with open(cache_path) as f:
        cache = json.load(f)
    assert isinstance(cache, dict), "Cache must be a JSON dict"

    molecules_path = Path("data/raw/molecules.csv")
    if not molecules_path.exists():
        pytest.xfail("molecules.csv not found")

    mol_df = pd.read_csv(molecules_path)
    pubchem_ids = set(mol_df["pubchem_id"].dropna().astype(int).astype(str).tolist())
    cache_keys = set(cache.keys())
    missing = pubchem_ids - cache_keys
    assert len(missing) == 0, f"Cache missing {len(missing)} pubchem_ids: {list(missing)[:10]}"


@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_smiles_missing_logged():
    """FEAT-01: fetch function stores None for 404 responses rather than omitting the key."""
    fetch_smiles = pytest.importorskip("data.fetch_smiles")

    import asyncio
    # pubchem_id=0 should not exist in PubChem; expect None returned (not omitted)
    result = asyncio.run(fetch_smiles.fetch_smiles_for_ids([0]))
    assert isinstance(result, dict), "fetch_smiles_for_ids must return a dict"
    assert 0 in result or "0" in result, "Missing pubchem_id must be present in result as None"
    value = result.get(0) or result.get("0")
    assert value is None, "404 pubchem_id must store None, not omit the key"


# ---------------------------------------------------------------------------
# FEAT-02: RDKit descriptors (data/build_features.py)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_rdkit_descriptors():
    """FEAT-02: compute_molecule_features returns MW, logP, HBD, HBA, rotatable_bonds, TPSA for valid SMILES."""
    pytest.importorskip("rdkit")
    build_features = pytest.importorskip("data.build_features")

    result = build_features.compute_molecule_features(
        pubchem_id=702, smiles="CCO", common_name="Ethanol"
    )
    assert isinstance(result, dict), "compute_molecule_features must return a dict"
    required_keys = ["MW", "logP", "HBD", "HBA", "rotatable_bonds", "TPSA"]
    for key in required_keys:
        assert key in result, f"Missing descriptor key: {key}"
        assert result[key] is not None, f"Descriptor {key} must not be None for valid SMILES"
        assert isinstance(result[key], float), f"Descriptor {key} must be float, got {type(result[key])}"


@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_rdkit_sanitization_logged():
    """FEAT-02: compute_molecule_features returns all-None descriptors for invalid SMILES without crashing."""
    pytest.importorskip("rdkit")
    build_features = pytest.importorskip("data.build_features")

    result = build_features.compute_molecule_features(
        pubchem_id=1, smiles="INVALID_SMILES", common_name="bad"
    )
    assert isinstance(result, dict), "compute_molecule_features must return a dict even for invalid SMILES"
    descriptor_keys = ["MW", "logP", "HBD", "HBA", "rotatable_bonds", "TPSA"]
    for key in descriptor_keys:
        assert key in result, f"Invalid SMILES result must still contain key: {key}"
        assert result[key] is None, f"Descriptor {key} must be None for invalid SMILES, got {result[key]}"
    assert "morgan_fp_bytes" in result, "morgan_fp_bytes key must be present"
    assert result["morgan_fp_bytes"] is None, "morgan_fp_bytes must be None for invalid SMILES"


# ---------------------------------------------------------------------------
# FEAT-03: Morgan fingerprints (data/build_features.py)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_morgan_fingerprint():
    """FEAT-03: compute_molecule_features returns morgan_fp_bytes as 1024-byte bytes object."""
    pytest.importorskip("rdkit")
    build_features = pytest.importorskip("data.build_features")

    result = build_features.compute_molecule_features(
        pubchem_id=702, smiles="CCO", common_name="Ethanol"
    )
    assert "morgan_fp_bytes" in result, "morgan_fp_bytes key must be present in result"
    fp = result["morgan_fp_bytes"]
    assert isinstance(fp, bytes), f"morgan_fp_bytes must be bytes, got {type(fp)}"
    assert len(fp) == 1024, f"morgan_fp_bytes must be 1024 bytes (1024-bit fingerprint), got {len(fp)}"


# ---------------------------------------------------------------------------
# FEAT-04: Tanimoto edges (data/build_features.py)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_tanimoto_edges():
    """FEAT-04: compute_tanimoto_edges returns a list; identical molecules produce at least one edge."""
    pytest.importorskip("rdkit")
    from rdkit.Chem import AllChem
    build_features = pytest.importorskip("data.build_features")

    # Two near-identical SMILES (same molecule) must produce similarity=1.0 → edge exists
    smiles_a = "CC(C)O"  # isopropanol
    smiles_b = "CC(C)O"  # same molecule → sim = 1.0

    mol_a = AllChem.MolFromSmiles(smiles_a)
    mol_b = AllChem.MolFromSmiles(smiles_b)
    fp_a = AllChem.GetMorganFingerprintAsBitVect(mol_a, radius=2, nBits=1024)
    fp_b = AllChem.GetMorganFingerprintAsBitVect(mol_b, radius=2, nBits=1024)

    fps_and_ids = [(fp_a, 1), (fp_b, 2)]
    result = build_features.compute_tanimoto_edges(fps_and_ids)
    assert isinstance(result, list), f"compute_tanimoto_edges must return a list, got {type(result)}"
    assert len(result) >= 1, "Identical molecules must produce at least one Tanimoto edge"


# ---------------------------------------------------------------------------
# FEAT-05: Texture encoding (data/build_features.py)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_texture_encoding():
    """FEAT-05: encode_texture returns 5-dim one-hot vector; graceful fallback for unknown categories."""
    build_features = pytest.importorskip("data.build_features")

    result = build_features.encode_texture("herb")
    assert isinstance(result, list), f"encode_texture must return a list, got {type(result)}"
    assert len(result) == 5, f"Texture vector must have length 5, got {len(result)}"
    assert sum(result) == 1, f"Texture vector must be one-hot (sum=1), got sum={sum(result)}"
    assert all(v in (0, 1) for v in result), "Texture vector must contain only 0s and 1s"

    # Unknown category must still return length-5 vector (graceful fallback)
    fallback = build_features.encode_texture("unknown_xyz")
    assert isinstance(fallback, list), "encode_texture must return list for unknown category"
    assert len(fallback) == 5, f"Fallback texture vector must have length 5, got {len(fallback)}"


# ---------------------------------------------------------------------------
# FEAT-06: Temperature encoding (data/build_features.py)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_temperature_encoding():
    """FEAT-06: encode_temperature returns 4-dim one-hot vector; graceful fallback for unknown categories."""
    build_features = pytest.importorskip("data.build_features")

    result = build_features.encode_temperature("herb")
    assert isinstance(result, list), f"encode_temperature must return a list, got {type(result)}"
    assert len(result) == 4, f"Temperature vector must have length 4, got {len(result)}"
    assert sum(result) == 1, f"Temperature vector must be one-hot (sum=1), got sum={sum(result)}"
    assert all(v in (0, 1) for v in result), "Temperature vector must contain only 0s and 1s"

    # Unknown category must still return length-4 vector (graceful fallback)
    fallback = build_features.encode_temperature("unknown_xyz")
    assert isinstance(fallback, list), "encode_temperature must return list for unknown category"
    assert len(fallback) == 4, f"Fallback temperature vector must have length 4, got {len(fallback)}"


# ---------------------------------------------------------------------------
# FEAT-07: Cultural context vectors (data/build_features.py)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_cultural_context():
    """FEAT-07: build_cultural_context_vectors returns 10-dim vectors for each ingredient with non-zero entries."""
    build_features = pytest.importorskip("data.build_features")

    # Tiny in-memory DataFrame: 2 recipes with distinct cultural signals
    recipes_df = pd.DataFrame({
        "recipe_name": ["Indian Tikka Masala", "Mexican Tamales"],
        "ingredients": ["chicken", "corn"],
    })

    result = build_features.build_cultural_context_vectors(recipes_df)
    assert isinstance(result, dict), f"build_cultural_context_vectors must return a dict, got {type(result)}"
    assert "chicken" in result, "Result must contain entry for 'chicken'"
    assert "corn" in result, "Result must contain entry for 'corn'"

    for ingredient in ("chicken", "corn"):
        vec = result[ingredient]
        assert isinstance(vec, list), f"Cultural context for '{ingredient}' must be a list"
        assert len(vec) == 10, f"Cultural context for '{ingredient}' must have length 10, got {len(vec)}"
        assert any(v != 0 for v in vec), f"Cultural context for '{ingredient}' must have at least one non-zero value"


# ---------------------------------------------------------------------------
# FEAT-08: Flavor profile vocabulary and encoding (data/build_features.py)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_flavor_profile_vocab():
    """FEAT-08: build_flavor_vocab + encode_flavor_profile produce correct multi-hot encoding."""
    build_features = pytest.importorskip("data.build_features")

    # Tiny mock molecules DataFrame with flavor_profile column
    mol_df = pd.DataFrame({
        "pubchem_id": [1, 2],
        "flavor_profile": ["sweet@floral", "sweet@bitter@umami"],
    })

    vocab_index = build_features.build_flavor_vocab(mol_df)
    assert isinstance(vocab_index, dict), f"build_flavor_vocab must return a dict (token→index), got {type(vocab_index)}"

    expected_tokens = {"sweet", "floral", "bitter", "umami"}
    for token in expected_tokens:
        assert token in vocab_index, f"Vocab must contain '{token}'"
    assert len(vocab_index) == 4, f"Vocab must have exactly 4 entries for this input, got {len(vocab_index)}"

    # Encode a single row with "sweet@floral"
    encoded = build_features.encode_flavor_profile("sweet@floral", vocab_index)
    assert isinstance(encoded, list), f"encode_flavor_profile must return a list, got {type(encoded)}"
    assert len(encoded) == len(vocab_index), f"Encoded vector length must match vocab size {len(vocab_index)}"

    sweet_idx = vocab_index["sweet"]
    assert encoded[sweet_idx] == 1, f"'sweet' dimension must be 1 in encoded vector"


# ---------------------------------------------------------------------------
# FEAT-09: Integration — parquet outputs exist and have correct schema
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_parquet_outputs_exist():
    """FEAT-09: All four processed parquet files exist."""
    expected = [
        Path("data/processed/ingredients.parquet"),
        Path("data/processed/molecules.parquet"),
        Path("data/processed/tanimoto_edges.parquet"),
        Path("data/processed/cooccurrence.parquet"),
    ]
    missing = [str(p) for p in expected if not p.exists()]
    if missing:
        pytest.xfail(f"Parquet files not yet generated: {missing}")
    for p in expected:
        assert p.exists(), f"Expected parquet file not found: {p}"


@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_molecules_parquet_schema():
    """FEAT-09: molecules.parquet contains required columns."""
    molecules_path = Path("data/processed/molecules.parquet")
    if not molecules_path.exists():
        pytest.xfail("molecules.parquet not yet generated")

    df = pd.read_parquet(molecules_path)
    required_columns = [
        "pubchem_id", "smiles", "MW", "logP", "HBD", "HBA",
        "rotatable_bonds", "TPSA", "morgan_fp_bytes",
    ]
    for col in required_columns:
        assert col in df.columns, f"molecules.parquet missing required column: {col}"


@pytest.mark.xfail(strict=False, reason="implementation pending")
def test_ingredients_parquet_schema():
    """FEAT-09: ingredients.parquet contains required columns (prefix-matched for multi-column groups)."""
    ingredients_path = Path("data/processed/ingredients.parquet")
    if not ingredients_path.exists():
        pytest.xfail("ingredients.parquet not yet generated")

    df = pd.read_parquet(ingredients_path)
    exact_columns = ["ingredient_id", "name", "category"]
    for col in exact_columns:
        assert col in df.columns, f"ingredients.parquet missing required column: {col}"

    # Prefix checks for multi-column feature groups
    prefixes = ["texture_", "temperature_", "cultural_context_", "flavor_profile_"]
    for prefix in prefixes:
        matching = [c for c in df.columns if c.startswith(prefix)]
        assert len(matching) >= 1, f"ingredients.parquet must have at least one column with prefix '{prefix}'"
