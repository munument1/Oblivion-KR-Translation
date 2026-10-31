"""Issue #8 reporter term source bounds, output and identity regressions."""
import csv
import re
import unittest
from collections import Counter
from pathlib import Path

from book_title_overrides import apply_book_title_overrides
from build_vanilla_overlay import load_translations
from issue8_reporter_term_patch import EXPECTED, correct_reporter_terms, verify_canonical

HERE = Path(__file__).resolve().parents[1]
CANONICAL = HERE / "canonical_translation_v2.csv"
LOCATIONS = HERE / "canonical_locations_v2.csv"


class ReporterTermsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        verify_canonical(CANONICAL)
        cls.table = load_translations(CANONICAL, (
            HERE / "canonical_ui_supplement_v1.csv",
            HERE / "canonical_nexus_56688_fur_v1.csv",
        ), encoded_column="obcjk_utf8_hex")
        apply_book_title_overrides(cls.table, HERE / "canonical_book_title_overrides_v1.csv")
        cls.before = {key: list(items) for key, items in cls.table.items()}
        cls.counts = correct_reporter_terms(cls.table, CANONICAL)

    def test_only_named_terms_change_and_all_source_identities_preserved(self):
        changes = 0
        for key, before in self.before.items():
            after = self.table[key]
            self.assertEqual(len(before), len(after))
            for left, right in zip(before, after):
                self.assertEqual(
                    (left.source, left.record_type, left.formid, left.field,
                     left.english, left.line, left.editor_id, left.occurrence),
                    (right.source, right.record_type, right.formid, right.field,
                     right.english, right.line, right.editor_id, right.occurrence))
                if left.korean != right.korean:
                    changes += 1
                    self.assertTrue(right.korean.endswith(b"\0"))
        # 13 physical records mention two audited English concepts, so
        # 574 terminology hits correspond to 561 distinct changed records.
        self.assertEqual(sum(self.counts.values()) - changes, 13)
        self.assertEqual(self.counts["Cheydinhal"], EXPECTED["Cheydinhal"])
        self.assertEqual(self.counts["Mysterium Xarxes"], EXPECTED["Mysterium Xarxes"])
        self.assertEqual(self.counts["Knights of the Nine"], EXPECTED["Knights of the Nine"])
        self.assertEqual(self.counts["Crusader equipment"], EXPECTED["Crusader equipment"])
        self.assertIn(self.counts["Mythic Dawn"], (105, 106))

    def test_book2_and_corrected_quest_dialogue(self):
        key = ("Oblivion.esm", b"BOOK", 0x00022B05, b"FULL")
        rows = [x for x in self.table[key]
                if x.english == "Mythic Dawn Commentaries 2"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].korean, "미식 던 논평집 2".encode("utf-8") + b"\0")
        for key, items in self.table.items():
            for item in items:
                if item.record_type in (b"INFO", b"QUST", b"BOOK"):
                    # Names in quest/dialogue/book should never retain the
                    # single-source aliases after our exact-source correction.
                    if re.search(r"(?<![A-Za-z])Cheydinhal(?![A-Za-z])",
                                 item.english, re.I) and item.source == "Oblivion.esm":
                        output = item.korean[:-1].decode("utf-8")
                        self.assertNotIn("셰이딘홀", output)
                        self.assertNotIn("쉐이딘홀", output)
                        self.assertNotIn("체이딘홀", output)

    def test_preflight_rejects_empty_input_without_editing(self):
        with self.assertRaisesRegex(ValueError, "candidate drift"):
            correct_reporter_terms({})

    def test_location_and_marker_source_and_utf8_hex(self):
        changed=Counter()
        with LOCATIONS.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                eng = row["old_english"]
                src = row["effective_source"]
                if re.search(r"(?<![A-Za-z])Cheydinhal(?![A-Za-z])", eng, re.I):
                    if any(x in row["obcjk_unicode_text"] for x in
                           ("셰이딘홀", "쉐이딘홀", "체이딘홀")):
                        self.fail(f"Unnormalized Cheydinhal: {src} {row['raw_formid']}")
                    if "체이딘할" in row["obcjk_unicode_text"]:
                        changed["Cheydinhal"] += 1
                if (src in ("Knights.esp", "Knights - Unofficial Patch.esp")
                    and eng == "The Shrine of the Crusader"):
                    self.assertIn("성기사", row["obcjk_unicode_text"])
                    changed["Crusader"] += 1
                self.assertEqual(
                    bytes.fromhex(row["obcjk_utf8_hex"]),
                    row["obcjk_unicode_text"].encode("utf-8") + b"\0",
                )
        self.assertEqual(changed, Counter(Cheydinhal=21, Crusader=2))


if __name__ == "__main__":
    unittest.main()
