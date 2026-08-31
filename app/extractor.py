"""
extractor.py — PDF text extraction and resume info parsing.
Uses PyMuPDF (import pymupdf). No spaCy, sklearn, scipy, numpy.
"""

import re
import pymupdf  # PyMuPDF >= 1.24


# ── PDF extraction ─────────────────────────────────────────────────────────

def extract_text_by_page(filepath: str) -> list[str]:
    """
    Return a list of strings, one per page.
    Raises ValueError for encrypted/unreadable PDFs.
    """
    pages = []
    try:
        doc = pymupdf.open(filepath)
    except Exception as exc:
        raise ValueError(f"Cannot open PDF: {exc}") from exc

    if doc.is_encrypted:
        doc.close()
        raise ValueError("PDF is encrypted and cannot be read.")

    for page in doc:
        text = page.get_text("text") or ""
        pages.append(text.strip())

    doc.close()
    return pages if pages else [""]


# ── Resume info extraction ─────────────────────────────────────────────────

# Regexes
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s\-.]?)?"       # optional country code
    r"(?:\(?\d{2,4}\)?[\s\-.]?)"      # area code
    r"\d{3,4}[\s\-.]?\d{3,5}"
)

_SECTION_HEADERS = {
    "experience":    re.compile(
        r"(?:work\s+)?experience|employment|work\s+history|professional\s+background",
        re.I),
    "education":     re.compile(r"education|academic|qualifications|degrees?", re.I),
    "skills":        re.compile(r"skills?|technical\s+skills?|competencies|expertise", re.I),
    "projects":      re.compile(r"projects?|portfolio|personal\s+projects?", re.I),
    "certifications":re.compile(r"certifications?|licen[sc]es?|credentials?", re.I),
    "achievements":  re.compile(r"achievements?|awards?|honours?|honors?", re.I),
    "summary":       re.compile(r"summary|profile|objective|about\s+me", re.I),
}

# Lines that look like section headers (short, no punctuation mid-line)
_HEADER_LINE_RE = re.compile(r"^[A-Z][A-Za-z &/\-]{2,40}$")


def extract_resume_info(text: str) -> dict:
    """
    Parse plain-text resume into structured dict:
    {
        "name": str,
        "contact": {"email": str, "phone": str},
        "sections": {
            "experience": [line, ...],
            "education":  [line, ...],
            ...
        }
    }
    """
    lines = [l.strip() for l in text.splitlines()]
    non_empty = [l for l in lines if l]

    name    = _extract_name(non_empty)
    email   = _first_match(_EMAIL_RE, text)
    phone   = _first_match(_PHONE_RE, text)
    sections = _extract_sections(lines)

    return {
        "name": name,
        "contact": {
            "email": email or "",
            "phone": phone or "",
        },
        "sections": sections,
    }


def _first_match(pattern: re.Pattern, text: str) -> str:
    m = pattern.search(text)
    return m.group(0).strip() if m else ""


def _extract_name(non_empty_lines: list[str]) -> str:
    """
    Heuristic: first non-empty line that looks like a name
    (2–5 words, mostly alphabetic, no digits, not an email/phone).
    """
    for line in non_empty_lines[:8]:
        if _EMAIL_RE.search(line) or _PHONE_RE.search(line):
            continue
        if re.search(r"\d", line):
            continue
        words = line.split()
        if 2 <= len(words) <= 5 and all(re.match(r"[A-Za-z'\-\.]+$", w) for w in words):
            return line
    return ""


def _extract_sections(lines: list[str]) -> dict:
    """
    Split resume into labelled sections by detecting header lines.
    Returns dict of {section_label: [content_lines]}.
    """
    sections: dict[str, list[str]] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def _flush():
        if current_key and current_lines:
            clean = [l for l in current_lines if l.strip()]
            if clean:
                sections[current_key] = clean

    for line in lines:
        stripped = line.strip()
        matched_section = _match_section_header(stripped)

        if matched_section:
            _flush()
            current_key = matched_section
            current_lines = []
        else:
            if current_key:
                current_lines.append(stripped)

    _flush()
    return sections


def _match_section_header(line: str) -> str | None:
    """Return section key if line is a section header, else None."""
    if not line or len(line) > 60:
        return None
    for key, pattern in _SECTION_HEADERS.items():
        if pattern.fullmatch(line.strip()):
            return key
        # also match if it's a standalone header word/phrase
        if pattern.match(line.strip()) and len(line.split()) <= 4:
            return key
    return None
