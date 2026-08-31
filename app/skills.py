"""
skills.py — Skill extraction and job description skill matching.
Pure Python. No spaCy, sklearn, scipy, numpy.
"""

import re

# ── Skill dictionary ───────────────────────────────────────────────────────
# Categories → list of skills (lowercase). Add/extend as needed.

SKILL_DICT: dict[str, list[str]] = {
    "programming": [
        "python", "javascript", "typescript", "java", "c", "c++", "c#",
        "go", "golang", "rust", "kotlin", "swift", "ruby", "php", "scala",
        "r", "matlab", "perl", "bash", "shell", "powershell", "vba",
        "dart", "lua", "haskell", "elixir", "clojure",
    ],
    "web": [
        "html", "css", "react", "reactjs", "angular", "angularjs", "vue",
        "vuejs", "nextjs", "nuxtjs", "svelte", "jquery", "bootstrap",
        "tailwind", "webpack", "vite", "sass", "less",
    ],
    "backend": [
        "flask", "django", "fastapi", "express", "expressjs", "node",
        "nodejs", "spring", "springboot", "rails", "laravel", "asp.net",
        "dotnet", ".net", "graphql", "rest", "restful", "grpc", "soap",
    ],
    "databases": [
        "sql", "mysql", "postgresql", "postgres", "sqlite", "mongodb",
        "redis", "elasticsearch", "cassandra", "dynamodb", "oracle",
        "mssql", "mariadb", "firebase", "supabase", "neo4j",
    ],
    "cloud": [
        "aws", "azure", "gcp", "google cloud", "heroku", "vercel",
        "netlify", "digitalocean", "cloudflare", "lambda", "ec2", "s3",
        "kubernetes", "k8s", "docker", "terraform", "ansible", "helm",
    ],
    "data": [
        "pandas", "numpy", "scikit-learn", "sklearn", "tensorflow",
        "pytorch", "keras", "matplotlib", "seaborn", "plotly",
        "spark", "hadoop", "airflow", "dbt", "tableau", "powerbi",
        "excel", "jupyter", "nlp", "machine learning", "deep learning",
        "data analysis", "data science", "statistics",
    ],
    "tools": [
        "git", "github", "gitlab", "bitbucket", "jira", "confluence",
        "slack", "trello", "figma", "postman", "linux", "unix",
        "nginx", "apache", "ci/cd", "jenkins", "github actions",
        "circleci", "pytest", "jest", "selenium", "cypress",
    ],
    "soft": [
        "agile", "scrum", "kanban", "tdd", "bdd", "devops", "mlops",
        "microservices", "api", "sdk", "oop", "solid", "mvc",
    ],
}

# Build a flat lookup: lowercase_skill → category
_SKILL_LOOKUP: dict[str, str] = {}
for _cat, _skills in SKILL_DICT.items():
    for _s in _skills:
        _SKILL_LOOKUP[_s] = _cat


def _normalise(text: str) -> str:
    return text.lower()


def _find_skills_in_text(text: str) -> dict[str, list[str]]:
    """
    Scan text for known skills.
    Returns {category: [skill, ...]} with no duplicates.
    """
    norm = _normalise(text)
    found: dict[str, set] = {}

    # Sort by length descending so multi-word skills match before substrings
    for skill in sorted(_SKILL_LOOKUP, key=len, reverse=True):
        pattern = r"(?<![a-z0-9+#.])" + re.escape(skill) + r"(?![a-z0-9+#.])"
        if re.search(pattern, norm):
            cat = _SKILL_LOOKUP[skill]
            found.setdefault(cat, set()).add(skill)

    # Convert sets to sorted lists
    return {cat: sorted(skills) for cat, skills in found.items()}


# ── Public API ─────────────────────────────────────────────────────────────

def extract_skills(resume_text: str) -> dict[str, list[str]]:
    """
    Extract skills from resume text.
    Returns {category: [skill, ...]}.
    """
    return _find_skills_in_text(resume_text)


def match_skills(
    resume_skills: dict[str, list[str]],
    jd_text: str,
) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """
    Compare resume skills against job description.

    Returns:
        matched   — flat list of skills in both resume and JD
        missing   — flat list of skills required by JD but not in resume
        jd_skills — {category: [skill, ...]} of skills found in JD
    """
    if not jd_text or not jd_text.strip():
        return [], [], {}

    jd_skills = _find_skills_in_text(jd_text)

    # Flat sets
    resume_flat = {s for skills in resume_skills.values() for s in skills}
    jd_flat     = {s for skills in jd_skills.values()     for s in skills}

    matched = sorted(resume_flat & jd_flat)
    missing = sorted(jd_flat - resume_flat)

    return matched, missing, jd_skills
