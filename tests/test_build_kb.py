"""Local fixture tests; never write to the real transcript collection."""

import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_kb", BASE / "build_kb.py")
kb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kb)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "Transcriptions"
        self.source.mkdir()
        (self.root / "manifests").mkdir()
        (self.root / "taxonomy.md").write_bytes((BASE / "taxonomy.md").read_bytes())
        self.put("B.txt", "A business example. " * 600)
        self.put("C.txt", "A second example with Unicode: caf\u00e9. " * 150)
        self.put("._ignored.txt", "not a transcript")

    def put(self, name, text):
        (self.source / name).write_bytes(text.encode("utf-8"))

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return kb.build(self.root)

    def rows(self, name="catalog.csv"):
        with (self.root / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def save(self, name, rows):
        (self.root / name).write_text(kb.csv_text(list(rows[0]), rows), encoding="utf-8")

    def output_snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*")
                if p.is_file() and self.source not in p.parents}

    def assert_failed_without_writes(self):
        before = self.output_snapshot()
        with self.assertRaises((ValueError, UnicodeError)):
            self.build()
        self.assertEqual(before, self.output_snapshot())

    def test_source_bytes_and_ignored_files_unchanged(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.source.iterdir()}
        result = self.build()
        self.assertEqual(2, result["active"])
        self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.source.iterdir()})
        self.assertFalse(any(r["file"].startswith("._") for r in self.rows()))

    def test_portable_script_arbitrary_cwd(self):
        (self.root / "build_kb.py").write_bytes((BASE / "build_kb.py").read_bytes())
        process = subprocess.run([sys.executable, "-B", str(self.root / "build_kb.py")],
                                 cwd=self.source, capture_output=True, text=True)
        self.assertEqual(0, process.returncode, process.stderr)
        self.assertEqual(2, json.loads(process.stdout)["active"])
        self.assertEqual([], list(self.root.rglob("__pycache__")))

    def test_missing_directory_no_overwrite(self):
        self.build()
        for p in self.source.iterdir():
            p.unlink()
        self.source.rmdir()
        self.assert_failed_without_writes()

    def test_no_sources_no_overwrite(self):
        self.build()
        (self.source / "B.txt").unlink()
        (self.source / "C.txt").unlink()
        self.assert_failed_without_writes()

    def test_empty_source_no_overwrite(self):
        self.build()
        self.put("C.txt", "  \n")
        self.assert_failed_without_writes()

    def test_invalid_utf8_no_overwrite(self):
        self.build()
        (self.source / "C.txt").write_bytes(b"\xff")
        self.assert_failed_without_writes()

    def test_ids_add_delete_archive_restore_and_rename(self):
        self.build()
        original = {r["file"]: r["id"] for r in self.rows()}
        self.put("A.txt", "An earlier sorted title.")
        self.build()
        added = {r["file"]: r["id"] for r in self.rows()}
        self.assertEqual(original["B.txt"], added["B.txt"])
        self.assertEqual("003", added["A.txt"])
        payload = (self.source / "B.txt").read_bytes()
        (self.source / "B.txt").unlink()
        (self.source / "Renamed.txt").write_bytes(payload)
        result = self.build()
        rows = {r["file"]: r for r in self.rows()}
        self.assertEqual("archived", rows["B.txt"]["source_status"])
        self.assertEqual("004", rows["Renamed.txt"]["id"])
        self.assertEqual(1, result["archived"])
        (self.source / "B.txt").write_bytes(payload)
        self.build()
        self.assertEqual(original["B.txt"], {r["file"]: r["id"] for r in self.rows()}["B.txt"])

    def test_metadata_confirmed_preserved_and_candidates_not_published(self):
        self.build()
        meta = self.rows("source-metadata.csv")
        meta[0].update(url="https://example.org/recording", published_at="2020-01-02", status="confirmed",
                       evidence="Human matched opening and distinctive passage; publication date displayed.", notes="Keep me", extra="custom")
        meta[1].update(url="https://example.org/candidate", status="candidate", extra="")
        self.save("source-metadata.csv", meta)
        expected = (self.root / "source-metadata.csv").read_bytes()
        self.build()
        self.assertEqual(expected, (self.root / "source-metadata.csv").read_bytes())
        rows = self.rows()
        self.assertEqual("https://example.org/recording", rows[0]["url"])
        self.assertEqual("", rows[1]["url"])
        self.put("D.txt", "A new source.")
        self.build()
        new_meta = self.rows("source-metadata.csv")
        self.assertEqual(meta[0], new_meta[0])
        self.assertEqual("unknown", new_meta[-1]["status"])

    def test_invalid_metadata_fails_without_overwrite(self):
        self.build()
        original = self.rows("source-metadata.csv")
        for edits in [dict(status="confirmed"), dict(status="wrong"), dict(status="candidate", url="javascript:alert(1)"),
                      dict(status="candidate", published_at="2020-02-30"), dict(url="https://example.org"),
                      dict(status="confirmed", url="https://example.org", published_at="2020-01-02", evidence=" ")]:
            with self.subTest(edits=edits):
                rows = [r.copy() for r in original]
                rows[0].update(edits)
                self.save("source-metadata.csv", rows)
                self.assert_failed_without_writes()

    def test_candidate_date_evidence_preserved_not_promoted_report_counts(self):
        self.build()
        meta = self.rows("source-metadata.csv")
        meta[0].update(url="https://example.org/candidate", published_at="2015-03-24", status="candidate",
                       evidence="Official channel title match; introductory transcript not compared.",
                       notes="Publication date of candidate only, not recording date.")
        self.save("source-metadata.csv", meta)
        expected = (self.root / "source-metadata.csv").read_bytes()
        for _ in range(2):
            result = self.build()
            self.assertEqual(expected, (self.root / "source-metadata.csv").read_bytes())
            row = self.rows()[0]
            self.assertEqual("candidate", row["metadata_status"])
            self.assertEqual("", row["url"])
            self.assertEqual("", row["published_at"])
            self.assertEqual({"unknown": 1, "candidate": 1, "confirmed": 0}, result["metadata_counts"])
            report = (self.root / "review-report.md").read_text()
            self.assertIn("source_match_review: externally_supplied_metadata", report)
            self.assertIn("generator_source_verification: not_run", report)
            self.assertIn("Candidate metadata records: 1", report)
            self.assertIn("Unknown metadata records: 1", report)
            self.assertIn("Confirmed metadata records: 0", report)
        meta[1].update(url="https://example.org/confirmed", published_at="2013-01-17", status="confirmed",
                       evidence="Externally supplied introductory caption match and upload date.")
        self.save("source-metadata.csv", meta)
        result = self.build()
        self.assertEqual({"unknown": 0, "candidate": 1, "confirmed": 1}, result["metadata_counts"])
        self.assertIn("Confirmed metadata records: 1", (self.root / "review-report.md").read_text())

    def test_duplicate_metadata_fails(self):
        self.build()
        rows = self.rows("source-metadata.csv")
        rows.append(rows[0].copy())
        self.save("source-metadata.csv", rows)
        self.assert_failed_without_writes()

    def test_title_mapping_regressions(self):
        cases = [
            ("Your Business Elevator Pitch. How to Sell Your Business Plan to Potential Investors", "business_sale"),
            ("Starting a Small Business, Part 4. Finding Your Partners & Advisors", "partner_dispute"),
            ("Bankruptcy Basics for Small Business. Reorganization Under Subchapter V", "client_nonpayment"),
            ("Negotiating Basics for Attorneys, Entrepreneurs and Others", "business_startup"),
            ("Copyright Law Basics", "ip_infringement"),
        ]
        for title, forbidden in cases:
            with self.subTest(title=title):
                row = kb.classify(title, "A neutral example.")
                self.assertNotIn(forbidden, row["situations"].split(";"))
                self.assertEqual("low", row["confidence"])
        self.assertIn("contracts", kb.classify("Legal Issues in Consulting Agreements", "")['topics'].split(";"))
        self.assertIn("business_sale", kb.classify("Before You Sell Your Business", "")['situations'].split(";"))

    def test_content_legal_signal_013(self):
        text = "Discuss overdue bills. You may discuss small claims court and Federal law with a professional."
        row = kb.classify("Dealing With Deadbeats", text)
        self.assertEqual("us_specific", row["legal_signal"])
        self.assertEqual("high", row["us_law_dependency"])
        self.assertEqual("requires_rf_legal_review", row["rf_applicability"])
        self.assertIn(row["legal_evidence"], text)
        self.assertEqual("low", row["confidence"])

    def test_no_signal_means_unknown_not_none(self):
        row = kb.classify("Time Management", "Organize your calendar.")
        self.assertEqual("unknown", row["rf_applicability"])
        self.assertEqual("unknown", row["us_law_dependency"])

    def test_country_mention_alone_not_legal_dependency(self):
        row = kb.classify("Business Pitch", "Many businesses operate in the United States.")
        self.assertEqual("not_detected", row["legal_signal"])
        self.assertEqual("unknown", row["us_law_dependency"])

    def test_chunks_complete_stable_unicode_and_no_whitespace_loss(self):
        self.build()
        initial = (self.root / "chunks.jsonl").read_bytes()
        self.build()
        self.assertEqual(initial, (self.root / "chunks.jsonl").read_bytes())
        chunks = [json.loads(line) for line in initial.splitlines()]
        for name in ("B.txt", "C.txt"):
            selected = [c for c in chunks if c["file"] == name]
            self.assertEqual((self.source / name).read_bytes().decode("utf-8"), "".join(c["text"] for c in selected))
            self.assertEqual(0, selected[0]["char_start"])
            self.assertTrue(all(len(c["text"]) <= 4000 for c in selected))
        for text in ["x" * 9000, "  \r\n" + "caf\u00e9. " * 2000 + "\n\t"]:
            derived = kb.chunks_for("001", "A.txt", "a" * 64, text)
            self.assertEqual(text, "".join(c["text"] for c in derived))

    def test_invalid_catalog_ids_enums_tags_hash(self):
        self.build()
        original = self.rows()
        for field, value in [("id", "000"), ("id", original[1]["id"]), ("rf_applicability", "approved"),
                             ("topics", "made_up"), ("source_sha256", "bad"), ("file", "../outside.txt")]:
            with self.subTest(field=field):
                rows = [r.copy() for r in original]
                rows[0][field] = value
                self.save("catalog.csv", rows)
                self.assert_failed_without_writes()

    def test_invalid_previous_manifest_hash(self):
        result = self.build()
        path = Path(result["manifest"])
        rows = kb.read_csv(path, kb.MANIFEST_HEADER)
        rows[0]["sha256"] = "invalid"
        path.write_text(kb.csv_text(kb.MANIFEST_HEADER, rows), encoding="utf-8")
        self.assert_failed_without_writes()

    def test_catalog_valid_shape_hash_tampering_rejected(self):
        self.build()
        rows = self.rows()
        rows[0]["source_sha256"] = "a" * 64
        self.save("catalog.csv", rows)
        self.assert_failed_without_writes()

    def test_derived_validator_rejects_valid_shape_wrong_hash_and_gap(self):
        result = self.build()
        catalog = self.rows()
        manifest = kb.read_csv(Path(result["manifest"]), kb.MANIFEST_HEADER)
        chunks = [json.loads(line) for line in (self.root / "chunks.jsonl").read_text().splitlines()]
        sources = {name: ((self.source / name).read_bytes(), (self.source / name).read_bytes().decode("utf-8")) for name in ("B.txt", "C.txt")}
        catalog[0]["source_sha256"] = "a" * 64
        with self.assertRaises(ValueError):
            kb.validate_derived(catalog, manifest, chunks, sources)
        catalog = self.rows()
        chunks[0]["char_start"] = 1
        with self.assertRaises(ValueError):
            kb.validate_derived(catalog, manifest, chunks, sources)

    def test_change_detection_and_honest_report(self):
        self.build()
        self.put("B.txt", "Changed text.")
        (self.source / "C.txt").unlink()
        self.put("D.txt", "Added text.")
        result = self.build()
        self.assertEqual({"added": ["D.txt"], "removed": ["C.txt"], "changed": ["B.txt"]}, result["changes"])
        report = (self.root / "review-report.md").read_text()
        self.assertIn("structural_status: verified", report)
        self.assertIn("semantic_review: not_run", report)
        self.assertIn("ai_learning_checks: not_run", report)
        self.assertNotIn("approved", report)

    def test_manual_review_preserved_then_stale(self):
        self.build()
        rows = self.rows()
        rows[0].update(classification_method="manual_review", notes_status="reviewed",
                       last_reviewed_at="2026-01-01", confidence="medium", summary="Human reviewed this source.")
        self.save("catalog.csv", rows)
        self.build()
        self.assertEqual("manual_review", self.rows()[0]["classification_method"])
        self.assertEqual("Human reviewed this source.", self.rows()[0]["summary"])
        self.put("B.txt", "Changed source.")
        self.build()
        row = self.rows()[0]
        self.assertEqual("stale", row["notes_status"])
        self.assertEqual("title_heuristic", row["classification_method"])
        self.assertEqual("2026-01-01", row["last_reviewed_at"])
        self.build()
        self.assertEqual("stale", self.rows()[0]["notes_status"])

    def test_unreviewed_dates_blank_and_taxonomy_preserved(self):
        self.build()
        rows = self.rows()
        legacy = [{k: row[k] for k in kb.HEADER[:19]} for row in rows]
        legacy[0]["last_reviewed_at"] = "2026-01-01"
        self.save("catalog.csv", legacy)
        taxonomy = (self.root / "taxonomy.md").read_bytes() + b"\nManual improvement.\n"
        (self.root / "taxonomy.md").write_bytes(taxonomy)
        self.build()
        self.assertEqual("", self.rows()[0]["last_reviewed_at"])
        self.assertEqual(taxonomy, (self.root / "taxonomy.md").read_bytes())

    def test_symlink_output_no_writes(self):
        self.build()
        path = self.root / "chunks.jsonl"
        path.unlink()
        path.symlink_to(self.root / "taxonomy.md")
        self.assert_failed_without_writes()


if __name__ == "__main__":
    unittest.main()
