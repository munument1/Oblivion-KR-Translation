"""Ensure the Nexus 56688 book report does not regress in canonical UTF-8 output.

The game may still display older strings if a later ESP overrides the book.
This test verifies only the source data and the main ESM replacement path;
it cannot prove in-game load order or renderer behavior.
"""
import csv
import unittest
from collections import Counter
from pathlib import Path

from build_vanilla_overlay import (
    encode_subrecord, load_translations, parse_subrecords, patch_record,
)

SOURCE = Path(__file__).resolve().parents[1] / "canonical_translation_v2.csv"
BOOK_ID = 0x00024564
EDITOR_ID = b"Book2CommonDarkestDarkness"


class Nexus56688BookSourcesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {}
        with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if (row["effective_source"] == "Oblivion.esm"
                        and row["record_type"] == "BOOK"
                        and int(row["raw_formid"], 16) == BOOK_ID
                        and row["field"] in ("FULL", "DESC")):
                    field = row["field"]
                    if field in cls.rows:
                        raise AssertionError(f"duplicate BOOK {BOOK_ID:08X} {field}")
                    cls.rows[field] = row
        if set(cls.rows) != {"FULL", "DESC"}:
            raise AssertionError(f"missing book fields: {set(cls.rows)}")

    def test_darkest_darkness_canonical_body_has_reviewed_names(self):
        book = self.rows["DESC"]
        self.assertEqual(book["editor_id"], EDITOR_ID.decode("ascii"))
        self.assertEqual(book["occurrence"], "0")
        self.assertIn("Mehrunes Razor", book["old_english"])
        translated = book["new_korean"]
        self.assertIn("접촉 마비 능력", translated)
        self.assertNotIn("마봄비의 4월", translated)
        for expected in ("메이룬스의 면도칼", "알말렉시아", "아주라"):
            self.assertIn(expected, translated)
        for stale in ("메루니스의 칼", "Almalexia", "Azura"):
            self.assertNotIn(stale, translated)
        self.assertEqual(book["obcjk_unicode_text"], translated)
        self.assertEqual(bytes.fromhex(book["obcjk_utf8_hex"]),
                         translated.encode("utf-8") + b"\0")

    def test_built_book_text_uses_exact_record_identity(self):
        table = load_translations(SOURCE, encoded_column="obcjk_utf8_hex")
        full = self.rows["FULL"]
        desc = self.rows["DESC"]
        self.assertEqual(full["old_english"], "Darkest Darkness")
        original = (
            encode_subrecord(b"EDID", EDITOR_ID + b"\0")
            + encode_subrecord(b"FULL", full["old_english"].encode("cp1252") + b"\0")
            + encode_subrecord(b"DESC", desc["old_english"].encode("cp1252") + b"\0")
        )
        rendered = patch_record(original, "Oblivion.esm", b"BOOK", BOOK_ID,
                                table, Counter(), [])
        values = {field: value for field, value, _ in parse_subrecords(rendered)}
        self.assertEqual(values[b"FULL"], bytes.fromhex(full["obcjk_utf8_hex"]))
        self.assertEqual(values[b"DESC"], bytes.fromhex(desc["obcjk_utf8_hex"]))
        self.assertEqual(
            patch_record(original, "Oblivion.esm", b"BOOK", BOOK_ID + 1,
                         table, Counter(), []), original)
        wrong_editor = original.replace(EDITOR_ID, b"X" * len(EDITOR_ID), 1)
        self.assertEqual(
            patch_record(wrong_editor, "Oblivion.esm", b"BOOK", BOOK_ID,
                         table, Counter(), []), wrong_editor)


if __name__ == "__main__":
    unittest.main()
