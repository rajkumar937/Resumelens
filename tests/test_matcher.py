"""
test_matcher.py — unit tests for pure-Python TF-IDF + cosine similarity.
Run: python -m pytest tests/test_matcher.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.matcher import (
    _tokenise,
    _tf,
    _idf,
    _tfidf_vector,
    _cosine_similarity,
    compute_match_score,
)


# ── tokeniser ──────────────────────────────────────────────────
def test_tokenise_basic():
    tokens = _tokenise("Python developer with Flask experience")
    assert "python" in tokens
    assert "flask" in tokens
    # stop words removed
    assert "with" not in tokens

def test_tokenise_empty():
    assert _tokenise("") == []

def test_tokenise_strips_stop_words():
    tokens = _tokenise("the and or is are")
    assert tokens == []

def test_tokenise_preserves_plus_hash():
    tokens = _tokenise("c++ c# .net")
    assert "c++" in tokens
    assert "c#" in tokens


# ── TF ─────────────────────────────────────────────────────────
def test_tf_sums_to_approx_one():
    tokens = ["python", "python", "flask"]
    tf = _tf(tokens)
    assert abs(sum(tf.values()) - 1.0) < 1e-9

def test_tf_empty():
    assert _tf([]) == {}


# ── IDF ────────────────────────────────────────────────────────
def test_idf_common_word_lower():
    corpus = [["python", "flask"], ["python", "django"]]
    idf = _idf(corpus)
    # "python" appears in both docs → lower IDF than "flask"
    assert idf["python"] < idf["flask"]

def test_idf_single_doc():
    idf = _idf([["python", "flask"]])
    assert "python" in idf
    assert all(v > 0 for v in idf.values())


# ── cosine similarity ───────────────────────────────────────────
def test_cosine_identical():
    vec = {"python": 0.5, "flask": 0.3}
    assert abs(_cosine_similarity(vec, vec) - 1.0) < 1e-9

def test_cosine_orthogonal():
    vec_a = {"python": 1.0}
    vec_b = {"django": 1.0}
    assert _cosine_similarity(vec_a, vec_b) == 0.0

def test_cosine_empty():
    assert _cosine_similarity({}, {"python": 1.0}) == 0.0

def test_cosine_partial_overlap():
    vec_a = {"python": 1.0, "flask": 1.0}
    vec_b = {"python": 1.0, "django": 1.0}
    sim = _cosine_similarity(vec_a, vec_b)
    assert 0.0 < sim < 1.0


# ── compute_match_score ────────────────────────────────────────
def test_no_jd_returns_none_scores():
    result = compute_match_score("some resume text", "", [], [])
    assert result["overall"] is None
    assert result["text_similarity"] is None
    assert result["skill_match"] is None

def test_identical_texts_high_score():
    text = "python flask developer web backend api"
    result = compute_match_score(text, text, ["python", "flask"], [])
    assert result["overall"] > 70

def test_unrelated_texts_low_score():
    resume = "python flask web developer backend"
    jd = "accountant finance tax excel spreadsheet"
    result = compute_match_score(resume, jd, [], ["excel", "finance"])
    assert result["overall"] < 40

def test_skill_match_weight():
    resume = "python developer"
    jd = "python flask django"
    # matched 2, missing 1
    result = compute_match_score(resume, jd, ["python", "flask"], ["django"])
    sm = result["skill_match"]
    assert abs(sm - (2 / 3 * 100)) < 1.0

def test_overall_bounded_0_100():
    result = compute_match_score(
        "python flask", "python flask", ["python"], []
    )
    assert 0.0 <= result["overall"] <= 100.0

def test_explanation_present():
    result = compute_match_score("python", "python flask", ["python"], ["flask"])
    assert "explanation" in result
    assert "Overall" in result["explanation"]

def test_no_sklearn_scipy_numpy():
    """Confirm banned packages are not imported in matcher."""
    import app.matcher as m
    import_lines = [
        ln for ln in open(m.__file__).read().splitlines()
        if ln.startswith("import ") or ln.startswith("from ")
    ]
    joined = " ".join(import_lines)
    for banned in ("sklearn", "scipy", "numpy"):
        assert banned not in joined, f"{banned} found in matcher.py imports"
