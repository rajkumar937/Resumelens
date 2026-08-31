"""
matcher.py — Pure-Python TF-IDF + cosine similarity.
Standard library only: re, math, collections.
"""

import re
import math
from collections import Counter


# ── tokenisation ──────────────────────────────────────────
_STOP_WORDS = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","being","have","has","had","do",
    "does","did","will","would","could","should","may","might","shall",
    "that","this","these","those","it","its","as","by","from","about",
    "into","through","during","before","after","above","below","between",
    "each","all","both","few","more","most","other","some","such","no",
    "not","only","same","so","than","too","very","just","can","how",
    "when","where","who","which","what","i","you","he","she","we","they",
}


def _tokenise(text: str) -> list[str]:
    # Matches: normal words, c++, c#, .net-style tokens
    tokens = re.findall(
        r"[a-z][a-z0-9]*(?:[+#]+|(?:\.[a-z0-9]+)+)?|[a-z0-9]+",
        text.lower()
    )
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


# ── TF-IDF ────────────────────────────────────────────────
def _tf(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {word: count / total for word, count in counts.items()}


def _idf(corpus_token_lists: list[list[str]]) -> dict[str, float]:
    n = len(corpus_token_lists)
    df: Counter = Counter()
    for tokens in corpus_token_lists:
        for word in set(tokens):
            df[word] += 1
    return {
        word: math.log((n + 1) / (count + 1)) + 1.0
        for word, count in df.items()
    }


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = _tf(tokens)
    return {word: tf_val * idf.get(word, 1.0) for word, tf_val in tf.items()}


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    shared = set(vec_a) & set(vec_b)
    dot = sum(vec_a[w] * vec_b[w] for w in shared)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── public API ────────────────────────────────────────────
def compute_match_score(
    resume_text: str,
    jd_text: str,
    matched_skills: list,
    missing_skills: list,
) -> dict:
    """
    Return a scores dict with:
      overall, text_similarity, skill_match, explanation
    All values are floats 0–100.
    When no JD is provided, text_similarity and skill_match are None
    and overall is None.
    """
    if not jd_text or not jd_text.strip():
        return {
            "overall": None,
            "text_similarity": None,
            "skill_match": None,
            "explanation": "No job description provided — match score unavailable.",
        }

    resume_tokens = _tokenise(resume_text)
    jd_tokens     = _tokenise(jd_text)

    idf = _idf([resume_tokens, jd_tokens])

    vec_resume = _tfidf_vector(resume_tokens, idf)
    vec_jd     = _tfidf_vector(jd_tokens, idf)

    text_sim = _cosine_similarity(vec_resume, vec_jd) * 100

    # skill match score
    total_jd_skills = len(matched_skills) + len(missing_skills)
    if total_jd_skills > 0:
        skill_match = (len(matched_skills) / total_jd_skills) * 100
    else:
        skill_match = 0.0

    # weighted overall: 40% text + 40% skill match + 20% matched count ratio
    matched_ratio = 0.0
    if total_jd_skills > 0:
        matched_ratio = min(len(matched_skills) / max(total_jd_skills, 1), 1.0) * 100

    overall = (
        0.40 * text_sim
        + 0.40 * skill_match
        + 0.20 * matched_ratio
    )
    overall = min(overall, 100.0)

    explanation = (
        f"Overall = 40% × text similarity ({text_sim:.1f}%)"
        f" + 40% × skill match ({skill_match:.1f}%)"
        f" + 20% × matched ratio ({matched_ratio:.1f}%)"
        f" = {overall:.1f}%\n\n"
        f"Matched skills : {len(matched_skills)}\n"
        f"Missing skills : {len(missing_skills)}\n"
        f"Total JD skills: {total_jd_skills}"
    )

    return {
        "overall":         round(overall, 2),
        "text_similarity": round(text_sim, 2),
        "skill_match":     round(skill_match, 2),
        "explanation":     explanation,
    }
