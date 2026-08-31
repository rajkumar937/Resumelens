# ResumeLens 🔍

**AI-powered resume analyser built entirely with the Python standard library.**  
Upload a PDF resume, paste a job description, and get an explainable match score — no cloud APIs, no compiled ML packages, no tracking.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Flask](https://img.shields.io/badge/Flask-3.0.3-lightgrey)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.28.2-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## The Problem

Job seekers paste their resume into online tools that send their data to third-party servers. Recruiters use proprietary ATS systems that score resumes invisibly. Neither side understands *how* the score is calculated.

ResumeLens solves this by running everything **locally** with a transparent, explainable scoring formula you can read in the source code.

---

## Features

| Feature | Detail |
|---|---|
| PDF extraction | PyMuPDF — fast, handles multi-page, detects scanned PDFs |
| Resume parsing | Regex-based name, email, phone, section detection |
| Skill extraction | 8-category skill dictionary (programming, web, backend, databases, cloud, data, tools, soft) |
| TF-IDF similarity | Pure Python — no sklearn, scipy, or numpy |
| Cosine similarity | Pure Python — standard library only |
| Explainable score | Weighted formula shown in the dashboard |
| Analysis history | SQLite via built-in `sqlite3` — no ORM |
| Charts | Chart.js via CDN — bar + doughnut |
| Security | Magic-byte PDF validation, UUID temp files, input caps, no stack traces to client |
| Tests | 44 automated tests — matcher, DB, routes, Jinja filters |

---

## Tech Stack

```
Backend  : Python 3.13, Flask 3.0.3, Werkzeug 3.0.3
PDF      : PyMuPDF 1.28.2  (import pymupdf)
Database : SQLite3 (Python built-in)
Frontend : Vanilla JS, Chart.js 4 (CDN), Google Fonts (CDN)
Config   : python-dotenv 1.0.1
NLP      : Pure Python — re, math, collections (NO sklearn/scipy/numpy)
```

**No compiled ML packages.** Runs on Windows 11 with Application Control policies active.

---

## How the Score Works

### TF-IDF (Term Frequency–Inverse Document Frequency)

Implemented from scratch in `app/matcher.py` using only the Python standard library:

```
TF(word, doc)  = count(word in doc) / total_words(doc)
IDF(word)      = log((N+1) / (df+1)) + 1        # smoothed
TF-IDF(word)   = TF × IDF
```

Each document (resume, job description) becomes a sparse vector of TF-IDF weights.

### Cosine Similarity

```
similarity = (A · B) / (|A| × |B|)
```

Computed over shared vocabulary only — O(shared_terms) not O(all_terms).

### Overall Score

```
Overall = 40% × text_similarity
        + 40% × skill_match_rate
        + 20% × matched_skill_ratio
```

All three components and their individual values are shown in the dashboard.

---

## Architecture

```
resumelens/
├── run.py                   # Entry point — loads .env, calls create_app()
├── .env.example             # Config template (copy to .env)
├── requirements.txt
│
├── app/
│   ├── __init__.py          # App factory, Jinja filters, DB init
│   ├── routes.py            # Flask blueprints — analyse + history CRUD
│   ├── extractor.py         # PyMuPDF extraction + resume info parser
│   ├── skills.py            # Skill dictionary + extraction + matching
│   ├── matcher.py           # Pure-Python TF-IDF + cosine similarity
│   ├── database.py          # SQLite service — save/read/delete history
│   │
│   ├── templates/
│   │   ├── base.html        # Nav, flash messages, footer
│   │   ├── index.html       # Upload panel + results dashboard
│   │   ├── history.html     # Analysis history table
│   │   └── history_detail.html  # Single record + charts
│   │
│   └── static/
│       ├── css/main.css     # Design system — dark theme, responsive
│       └── js/main.js       # Upload, charts, tabs, reset
│
├── instance/                # Runtime only — gitignored
│   ├── resumelens.db        # SQLite database
│   └── uploads/             # Temp PDF storage (deleted after analysis)
│
└── tests/
    ├── test_matcher.py      # TF-IDF unit tests (20 tests)
    └── test_stage9.py       # Full suite — DB, routes, security (44 tests)
```

### Request Lifecycle

```
POST /analyse
  → extension check (.pdf only)
  → magic-byte check (%PDF-)
  → save to UUID-named temp file
  → PyMuPDF: extract text per page
  → detect empty / scanned PDF
  → extract name, email, phone, sections
  → extract skills by category
  → TF-IDF + cosine similarity vs JD
  → skill match: matched / missing lists
  → weighted overall score
  → save to SQLite history
  → delete temp file (always, even on error)
  → return JSON → JS renders dashboard + charts
```

---

## Screenshots

> _Add your own screenshots here after running the app._

| Upload panel | Results dashboard | Analysis history |
|---|---|---|
| `docs/screenshot-upload.png` | `docs/screenshot-dashboard.png` | `docs/screenshot-history.png` |

---

## Installation & Running

### Requirements

- Windows 11 / macOS / Linux
- Python 3.13
- Internet connection (first run only — Google Fonts + Chart.js CDN)

### Setup

```powershell
# Clone the repo
git clone https://github.com/YOUR_USERNAME/resumelens.git
cd resumelens

# Create virtual environment
py -3.13 -m venv venv

# Windows PowerShell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env — set SECRET_KEY to a long random string

# Run
python run.py
```

Open **http://127.0.0.1:5000**

### Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | random (insecure) | Flask session secret — set a strong value |
| `FLASK_DEBUG` | `false` | Set `true` for development only |
| `MAX_UPLOAD_BYTES` | `10485760` | Max PDF size (bytes) — default 10 MB |

---

## Running Tests

```powershell
python tests/test_stage9.py
```

Expected output: `Ran 44 tests ... OK`

The test suite covers:

- TF-IDF tokeniser, TF, IDF, cosine similarity (17 tests)
- Database init, save, read, delete, clear, corrupted JSON recovery (11 tests)
- Flask routes — upload validation, magic-byte check, history CRUD, JD cap, 413 handler (10 tests)
- Jinja `verdict_class` filter (4 tests)
- No banned imports (`sklearn`, `scipy`, `numpy`) confirmed in CI (2 tests)

---

## Security & Privacy

- Uploaded PDFs are **deleted immediately** after analysis — never stored permanently
- Only extracted metadata is saved to SQLite (filename, scores, skill lists, date)
- JD text is capped at 20,000 characters server-side
- File uploads are capped at 10 MB
- Magic-byte validation rejects non-PDF files even with `.pdf` extension
- UUID-prefixed temp filenames prevent concurrent upload collisions
- `SECRET_KEY` must be set via environment variable — never hardcoded
- `FLASK_DEBUG=false` in production — stack traces never reach the client
- SQLite queries use parameterised statements — no SQL injection surface
- `instance/` and `.env` are gitignored — no secrets in source control

---

## Limitations & Future Improvements

| Area | Current | Potential improvement |
|---|---|---|
| OCR | Scanned PDFs rejected | Add Tesseract OCR fallback |
| Skill coverage | ~130 skills in dictionary | User-extensible dictionary |
| NLP | TF-IDF bag-of-words | Sentence embeddings (local model) |
| Multi-user | Single shared history | User sessions / authentication |
| Export | None | PDF / CSV report export |
| Deployment | Development server only | Gunicorn + Nginx config |
| Comparison | Single resume | Side-by-side diff of two resumes |

---

## License

MIT — see `LICENSE` for details.

---

## Author

Built as a portfolio project demonstrating Flask application architecture, pure-Python NLP, SQLite persistence, and security-conscious web development.
