"""Small fail-closed regression tests; do not need installed Oblivion."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from scripts.reconcile_canonical_ocrp import reconcile, encode_target, decode_target
from scripts.reviewed_memory_gate import load_reviewed_memory

class SafeCanonicalReconciliationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.path = root / "canonical_translation_v2.csv"
        self.audit = root / "audit.json"
        self.english = "The lady holds court during the day."
        self.old = "한밤중에 만날 수 있다."
        self.new = "낮에 만날 수 있다."
        self.audit.write_text(json.dumps({
            "corrections": [{"english": self.english, "previous_korean": self.old,
                             "reviewed_korean": self.new}] * 47,
            "additional_semantic_fixes": [{"english": self.english, "old": self.old,
                                           "new": self.new}] * 8,
        }, ensure_ascii=False), "utf-8")
        self.columns = ["effective_source", "record_type", "raw_formid", "field",
                        "old_english", "new_korean", "obcjk_unicode_text", "obcjk_utf8_hex", "new_bytes_hex"]
        self.row = dict(effective_source="Oblivion.esm", record_type="QUST", raw_formid="0001351B",
                        field="CNAM", old_english=self.english, new_korean=self.old,
                        obcjk_unicode_text=self.old,
                        obcjk_utf8_hex=encode_target(self.old, "utf8"),
                        new_bytes_hex=encode_target(self.old, "legacy"))
        self.write(self.row)

    def write(self, row):
        with self.path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.columns)
            w.writeheader()
            w.writerow(row)

    def test_dry_run_apply_then_idempotent(self):
        self.assertEqual(reconcile(self.path, self.audit)["corrected"], 1)
        self.assertEqual(reconcile(self.path, self.audit, apply=True)["corrected"], 1)
        with self.path.open(encoding="utf-8", newline="") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["new_korean"], self.new)
        self.assertEqual(row["obcjk_unicode_text"], self.new)
        self.assertEqual(decode_target(row["obcjk_utf8_hex"], "utf8"), self.new)
        self.assertEqual(decode_target(row["new_bytes_hex"], "legacy"), self.new)
        self.assertEqual(reconcile(self.path, self.audit, apply=True)["corrected"], 0)

    def test_encoded_disagreement_blocks_write(self):
        self.row["obcjk_utf8_hex"] = encode_target("다른 문구", "utf8")
        self.write(self.row)
        with self.assertRaises(ValueError):
            reconcile(self.path, self.audit, apply=True)
        with self.path.open(encoding="utf-8", newline="") as f:
            self.assertEqual(next(csv.DictReader(f))["new_korean"], self.old)

    def test_unreviewed_csv_is_rejected(self):
        with self.assertRaises(ValueError):
            load_reviewed_memory(self.path)

    def test_explicit_review_metadata_required(self):
        reviewed = self.path.parent / "reviewed.csv"
        fields = ["effective_source", "record_type", "raw_formid", "field",
                  "old_english", "korean", "review_status", "review_source"]
        with reviewed.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerow(dict(effective_source="Oblivion.esm", record_type="QUST",
                            raw_formid="0001351B", field="CNAM", old_english=self.english,
                            korean=self.new, review_status="reviewed",
                            review_source="human_source_comparison"))
        self.assertEqual(len(load_reviewed_memory(reviewed)), 1)

if __name__ == "__main__":
    unittest.main()
