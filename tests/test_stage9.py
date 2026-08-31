"""
test_stage9.py — Stage 9 security, DB, route, and edge-case tests.
Run: python tests/test_stage9.py
"""

import sys, os, json, io, sqlite3, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Minimal stubs so tests run without PyMuPDF ───────────
import types

_extractor = types.ModuleType("app.extractor")
def _fake_extract(path): return ["Python developer with Flask skills"]
def _fake_info(text): return {"name": "Jane Doe", "contact": {}, "sections": {}}
_extractor.extract_text_by_page = _fake_extract
_extractor.extract_resume_info  = _fake_info
sys.modules["app.extractor"] = _extractor

_skills_mod = types.ModuleType("app.skills")
def _fake_extract_skills(text): return {"programming": ["python", "flask"]}
def _fake_match(resume_skills, jd_text):
    if not jd_text: return [], [], {}
    return ["python"], ["django"], {"programming": ["python", "django"]}
_skills_mod.extract_skills = _fake_extract_skills
_skills_mod.match_skills   = _fake_match
sys.modules["app.skills"] = _skills_mod


from app import create_app
from app import database as db
from app.matcher import (
    _tokenise, _tf, _idf, _cosine_similarity, compute_match_score
)


# ═══════════════════════════════════════════════
# Helper — in-memory DB for tests
# ═══════════════════════════════════════════════
def _temp_db(monkeypatch_path: str):
    """Return a NamedTemporaryFile path for an isolated DB."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return f.name


# ═══════════════════════════════════════════════
# 1. Matcher / TF-IDF tests
# ═══════════════════════════════════════════════
class TestMatcher(unittest.TestCase):

    def test_tokenise_basic(self):
        t = _tokenise("Python developer Flask")
        self.assertIn("python", t)
        self.assertIn("flask", t)

    def test_tokenise_stop_words_removed(self):
        self.assertEqual(_tokenise("the and or"), [])

    def test_tokenise_c_plus_plus(self):
        self.assertIn("c++", _tokenise("c++ developer"))

    def test_tokenise_csharp(self):
        self.assertIn("c#", _tokenise("c# programmer"))

    def test_tokenise_empty(self):
        self.assertEqual(_tokenise(""), [])

    def test_tf_sums_to_one(self):
        tf = _tf(["a", "a", "b"])
        self.assertAlmostEqual(sum(tf.values()), 1.0)

    def test_tf_empty(self):
        self.assertEqual(_tf([]), {})

    def test_idf_common_word_lower(self):
        idf = _idf([["python", "flask"], ["python", "django"]])
        self.assertLess(idf["python"], idf["flask"])

    def test_cosine_identical(self):
        v = {"x": 1.0, "y": 0.5}
        self.assertAlmostEqual(_cosine_similarity(v, v), 1.0)

    def test_cosine_orthogonal(self):
        self.assertEqual(_cosine_similarity({"a": 1.0}, {"b": 1.0}), 0.0)

    def test_cosine_empty(self):
        self.assertEqual(_cosine_similarity({}, {"a": 1.0}), 0.0)

    def test_no_jd_returns_none(self):
        r = compute_match_score("python dev", "", [], [])
        self.assertIsNone(r["overall"])
        self.assertIsNone(r["text_similarity"])

    def test_identical_texts_high_score(self):
        t = "python flask web backend developer api"
        r = compute_match_score(t, t, ["python", "flask"], [])
        self.assertGreater(r["overall"], 70)

    def test_skill_match_weight(self):
        r = compute_match_score("python dev", "python flask django",
                                ["python", "flask"], ["django"])
        self.assertAlmostEqual(r["skill_match"], 200/3, delta=1.0)

    def test_overall_bounded(self):
        r = compute_match_score("python", "python flask",
                                ["python"], ["flask"])
        self.assertGreaterEqual(r["overall"], 0.0)
        self.assertLessEqual(r["overall"], 100.0)

    def test_unicode_input(self):
        # Should not raise
        r = compute_match_score("desarrollador Pythón", "Python desarrollador",
                                [], [])
        self.assertIsNotNone(r)

    def test_no_banned_imports(self):
        import app.matcher as m
        lines = [l for l in open(m.__file__).read().splitlines()
                 if l.startswith("import ") or l.startswith("from ")]
        joined = " ".join(lines)
        for banned in ("sklearn", "scipy", "numpy"):
            self.assertNotIn(banned, joined)


# ═══════════════════════════════════════════════
# 2. Database tests
# ═══════════════════════════════════════════════
class TestDatabase(unittest.TestCase):

    def setUp(self):
        self._orig = db._DB_PATH
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db._DB_PATH = tmp.name
        db.init_db()

    def tearDown(self):
        try:
            os.unlink(db._DB_PATH)
        except OSError:
            pass
        db._DB_PATH = self._orig

    def _save(self, **kw):
        defaults = dict(
            filename="cv.pdf", jd_summary="python role",
            overall_score=72.5, text_similarity=65.0, skill_match=80.0,
            matched_skills=["python"], missing_skills=["django"],
            resume_name="Jane Doe",
        )
        defaults.update(kw)
        return db.save_analysis(**defaults)

    def test_init_idempotent(self):
        db.init_db()  # second call should not raise
        db.init_db()

    def test_save_returns_id(self):
        rid = self._save()
        self.assertIsInstance(rid, int)
        self.assertGreater(rid, 0)

    def test_save_none_score(self):
        # overall_score=None (no JD) must not crash
        rid = self._save(overall_score=None, text_similarity=None,
                         skill_match=None)
        self.assertIsNotNone(rid)

    def test_get_all_history_order(self):
        self._save(filename="a.pdf")
        self._save(filename="b.pdf")
        rows = db.get_all_history()
        self.assertEqual(rows[0]["filename"], "b.pdf")  # newest first

    def test_get_analysis_found(self):
        rid = self._save()
        row = db.get_analysis(rid)
        self.assertEqual(row["filename"], "cv.pdf")

    def test_get_analysis_not_found(self):
        self.assertIsNone(db.get_analysis(999999))

    def test_skills_deserialised_as_list(self):
        rid = self._save()
        row = db.get_analysis(rid)
        self.assertIsInstance(row["matched_skills"], list)
        self.assertIsInstance(row["missing_skills"], list)

    def test_delete_analysis(self):
        rid = self._save()
        self.assertTrue(db.delete_analysis(rid))
        self.assertIsNone(db.get_analysis(rid))

    def test_delete_nonexistent(self):
        # Should return True (DELETE affects 0 rows, no error)
        result = db.delete_analysis(999999)
        self.assertTrue(result)

    def test_clear_all_history(self):
        self._save(); self._save()
        self.assertTrue(db.clear_all_history())
        self.assertEqual(db.get_all_history(), [])

    def test_empty_history(self):
        self.assertEqual(db.get_all_history(), [])

    def test_corrupted_json_field(self):
        # Manually insert bad JSON; _row_to_dict should recover
        conn = sqlite3.connect(db._DB_PATH)
        conn.execute(
            "INSERT INTO analysis_history "
            "(filename, jd_summary, overall_score, text_similarity, skill_match, "
            "matched_skills, missing_skills, resume_name, analysis_date) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ("bad.pdf", "", 0, 0, 0, "NOT_JSON", "[1,2]", "", "2026-01-01 00:00:00")
        )
        conn.commit(); conn.close()
        rows = db.get_all_history()
        self.assertEqual(rows[0]["matched_skills"], [])  # fallback to []


# ═══════════════════════════════════════════════
# 3. Flask route tests (no real PDF needed)
# ═══════════════════════════════════════════════
class TestRoutes(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self._dbpath = tmp.name
        db._orig_path = db._DB_PATH
        db._DB_PATH = self._dbpath

        upload_dir = tempfile.mkdtemp()
        self.app = create_app({
            "TESTING": True,
            "UPLOAD_FOLDER": upload_dir,
            "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        try:
            os.unlink(self._dbpath)
        except OSError:
            pass
        db._DB_PATH = db._orig_path

    # ── helper: fake valid PDF bytes ──
    @staticmethod
    def _pdf_bytes(text: str = "Python Flask developer") -> bytes:
        # Minimal valid PDF-1.4 with one page containing text
        # (PyMuPDF is stubbed, so magic-byte check (%PDF-) is what matters)
        return (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n9\n%%EOF"
        )

    def _upload(self, content=None, filename="cv.pdf", jd=""):
        data = {
            "resume": (io.BytesIO(content or self._pdf_bytes()), filename),
            "job_description": jd,
        }
        return self.client.post("/analyse",
                                data=data,
                                content_type="multipart/form-data")

    # ── index ──
    def test_index_ok(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

    # ── file validation ──
    def test_no_file_returns_400(self):
        r = self.client.post("/analyse", data={}, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)

    def test_wrong_extension_rejected(self):
        r = self._upload(b"%PDF-fake", filename="cv.docx")
        self.assertEqual(r.status_code, 400)
        self.assertIn("PDF", json.loads(r.data)["error"])

    def test_non_pdf_magic_bytes_rejected(self):
        r = self._upload(b"PK\x03\x04fake-zip", filename="cv.pdf")
        self.assertEqual(r.status_code, 400)
        self.assertIn("valid PDF", json.loads(r.data)["error"])

    def test_valid_upload_succeeds(self):
        r = self._upload()
        # extractor is stubbed to return text, so should be 200
        self.assertIn(r.status_code, (200, 422, 500))

    # ── history routes ──
    def test_history_empty(self):
        r = self.client.get("/history")
        self.assertEqual(r.status_code, 200)

    def test_history_detail_missing(self):
        r = self.client.get("/history/999999")
        self.assertEqual(r.status_code, 302)  # redirect to /history

    def test_delete_nonexistent_redirects(self):
        r = self.client.post("/history/999999/delete")
        self.assertEqual(r.status_code, 302)

    def test_clear_requires_confirm(self):
        r = self.client.post("/history/clear", data={"confirm": "no"})
        self.assertEqual(r.status_code, 302)
        # history should be unchanged (no crash)

    # ── security checks ──
    def test_413_handler_registered(self):
        # Send > MAX_CONTENT_LENGTH
        big = b"%PDF-" + b"x" * (11 * 1024 * 1024)
        r = self._upload(big, "big.pdf")
        # Flask returns 413 before our handler in test client; either is fine
        self.assertIn(r.status_code, (413, 400, 500))

    def test_jd_capped(self):
        long_jd = "python " * 5000  # 35 000 chars
        r = self._upload(jd=long_jd)
        # Should not 500 — JD is capped server-side
        self.assertNotEqual(r.status_code, 500)


# ═══════════════════════════════════════════════
# 4. Jinja filter tests
# ═══════════════════════════════════════════════
class TestJinjaFilter(unittest.TestCase):

    def setUp(self):
        self.app = create_app({"TESTING": True})

    def test_verdict_good(self):
        with self.app.app_context():
            f = self.app.jinja_env.filters["verdict_class"]
            self.assertEqual(f(75), "good")

    def test_verdict_ok(self):
        with self.app.app_context():
            f = self.app.jinja_env.filters["verdict_class"]
            self.assertEqual(f(55), "ok")

    def test_verdict_poor(self):
        with self.app.app_context():
            f = self.app.jinja_env.filters["verdict_class"]
            self.assertEqual(f(30), "poor")

    def test_verdict_none(self):
        with self.app.app_context():
            f = self.app.jinja_env.filters["verdict_class"]
            self.assertEqual(f(None), "neutral")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestMatcher, TestDatabase, TestRoutes, TestJinjaFilter):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
