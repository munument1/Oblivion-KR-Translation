"""Regression tests for the 2026-10-15 UOP book text restoration."""
import csv
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from build_unofficial_release import collect_changes
from uop_book_restoration import (
    BARZ_FIVE, CLAUDIUS_JOURNAL, EXPECTED_REPAIRS, WILD_ELVES, UOP_PLUGIN,
    load_restorations, normalize_volume_five_title, restore_book_body,
    suspicious_book_body,
)

ROOT = Path(__file__).resolve().parents[1]


class UOPBookRestorationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.restorations = load_restorations(
            ROOT / "uop_book_body_restore_v1.csv",
            ROOT / "canonical_translation_v2.csv")

    def test_all_112_restorations_are_present_and_have_full_bodies(self):
        self.assertEqual(len(self.restorations), EXPECTED_REPAIRS)
        self.assertIn(BARZ_FIVE, self.restorations)
        self.assertIn(WILD_ELVES, self.restorations)
        self.assertIn(CLAUDIUS_JOURNAL, self.restorations)
        for fid, (source_sha, target) in self.restorations.items():
            self.assertEqual(len(source_sha), 64)
            self.assertTrue(target.endswith(b"\0"), f"{fid:08X}")
            text = target[:-1].decode("utf-8")
            self.assertGreater(len(text), 80, f"{fid:08X}")
            self.assertRegex(text, "[가-힣]", f"{fid:08X}")

    def test_known_uop_source_rows_match_exactly_manifest(self):
        damaged = {}
        with (ROOT / "canonical_unofficial_translation_v2.csv").open(
                encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["effective_source"] != UOP_PLUGIN or row["record_type"] != "BOOK":
                    continue
                if row["field"] != "DESC":
                    continue
                if suspicious_book_body(row["old_english"], row["new_korean"]):
                    damaged[int(row["raw_formid"], 16)] = row["source_sha256"]
        self.assertEqual(set(damaged), set(self.restorations))
        for fid, raw_sha in damaged.items():
            self.assertEqual(raw_sha, self.restorations[fid][0])

    def test_long_book_to_title_regression_fails(self):
        source = '<font face=1><br>' + 'Chapter paragraph. ' * 80
        self.assertTrue(suspicious_book_body(source, "책 제목"))
        self.assertFalse(suspicious_book_body(source, source.replace(
            "Chapter paragraph.", "한국어 문단.")))

    def test_restore_checks_source_hash(self):
        raw = b"<font face=1><br>English body.\0"
        source = hashlib.sha256(raw).hexdigest()
        replacement = ("<font face=1><br>" + "전체 한국어 책 본문. " * 30).encode() + b"\0"
        mapping = {0x1234: (source, replacement)}
        self.assertEqual(restore_book_body(0x1234, raw, mapping), replacement)
        with self.assertRaisesRegex(ValueError, "source hash"):
            restore_book_body(0x1234, raw + b"x", mapping)
        self.assertIsNone(restore_book_body(0x4321, raw, mapping))

    def test_nexus_56688_darkest_darkness_exact_source_override(self):
        # This UOP book differs from the base source by a single apostrophe
        # in Mehrunes' Razor; its older UOP Korean text is not the reviewed
        # vanilla translation.
        fid = 0x00024564
        overrides = load_restorations(
            ROOT / "uop_book_reviewed_override_v1.csv",
            ROOT / "canonical_translation_v2.csv", expected_count=1)
        self.assertEqual(set(overrides), {fid})
        self.assertNotIn(fid, self.restorations)
        source = None
        with (ROOT / "canonical_unofficial_translation_v2.csv").open(
                encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if (row["effective_source"] == UOP_PLUGIN and
                        row["record_type"] == "BOOK" and
                        row["field"] == "DESC" and
                        row["raw_formid"] == "00024564"):
                    self.assertIsNone(source, "Duplicate source book")
                    source = row["old_english"].encode("cp1252") + b"\0"
        self.assertIsNotNone(source, "Missing UOP source book")
        self.assertEqual(hashlib.sha256(source).hexdigest(), overrides[fid][0])
        restored = restore_book_body(fid, source, overrides)
        body = restored[:-1].decode("utf-8")
        for name in ("메이룬스의 면도칼", "알말렉시아", "아주라"):
            self.assertIn(name, body)
        for stale in ("메루니스의 칼", "Almalexia", "Sotha Sil",
                      "Mehrunes Razor", "Boethiah"):
            self.assertNotIn(stale, body)
        with self.assertRaisesRegex(ValueError, "source hash"):
            restore_book_body(fid, source[:-1] + b"!" + b"\0", overrides)

    def test_special_uop_changes(self):
        wild = self.restorations[WILD_ELVES][1].decode("utf-8")
        self.assertIn("1E 2790-2E 227", wild)
        journal = self.restorations[CLAUDIUS_JOURNAL][1].decode("utf-8")
        self.assertIn("심장과 가죽", journal)
        self.assertTrue(journal.startswith("<font face=5><BR>"))
        self.assertIn("<BR>\r\n<BR>", journal)

    def test_fifth_volume_title(self):
        self.assertEqual(
            normalize_volume_five_title("진짜 바렌지아, 5권".encode() + b"\0"),
            "진정한 바렌지아, 5권".encode() + b"\0")
        self.assertEqual(
            normalize_volume_five_title("진정한 바렌지아, 5권".encode() + b"\0"),
            "진정한 바렌지아, 5권".encode() + b"\0")

    def test_builder_override_wins_without_vanilla_audit(self):
        fid = BARZ_FIVE
        original_desc = (b"<div align=center><br>"
                         + b"English book content. " * 50 + b"\0")
        restored = self.restorations[fid][1]
        fields = {
            (b"TES4", 0): [(b"MAST", b"Oblivion.esm\0")],
            (b"BOOK", fid): [
                (b"EDID", b"BookRealBarenziah05\0"),
                (b"FULL", b"The Real Barenziah, v 5\0"),
                (b"DESC", original_desc)],
        }
        full = "진짜 바렌지아, 5권".encode() + b"\0"
        from collections import defaultdict
        from build_vanilla_overlay import Translation
        patch_table = defaultdict(list)
        patch_table[(UOP_PLUGIN, b"BOOK", fid, b"FULL")].append(
            Translation(UOP_PLUGIN, b"BOOK", fid, b"FULL",
                        "The Real Barenziah, v 5", full, 1))
        with patch("build_unofficial_release.read_records", return_value=fields):
            override = {fid: (hashlib.sha256(original_desc).hexdigest(), restored)}
            changes, counts = collect_changes(
                Path(UOP_PLUGIN), None, patch_table=patch_table,
                book_restorations=override)
        self.assertEqual(counts["uop_book_desc_restored"], 1)
        self.assertEqual(counts["uop_book_title_fixed"], 1)
        self.assertEqual(changes[(b"BOOK", fid)][2][2], restored)
        self.assertEqual(changes[(b"BOOK", fid)][1][2],
                         "진정한 바렌지아, 5권".encode() + b"\0")


if __name__ == "__main__":
    unittest.main()
