"""Regression checks for Claude issue #8: Crate containers are not chairs."""
import unittest
from collections import Counter
from pathlib import Path

from build_vanilla_overlay import (
    encode_subrecord, load_translations, parse_subrecords, patch_record,
)
from claude_issue8_crate import OLD, NEW, EXPECTED, correct_crate_names

HERE = Path(__file__).resolve().parents[1]


class ClaudeCrateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_translations(
            HERE / "canonical_translation_v2.csv",
            encoded_column="obcjk_utf8_hex",
        )
        cls.original = [
            (key, item)
            for key, candidates in cls.table.items()
            if key[0] == "Oblivion.esm" and key[1] == b"CONT"
            and key[3] == b"FULL"
            for item in candidates
            if item.source == "Oblivion.esm"
            and item.english == "Crate" and item.korean == OLD
        ]
        cls.count = correct_crate_names(cls.table)

    def test_only_verified_mistranslations_change(self):
        self.assertEqual(len(self.original), EXPECTED)
        self.assertEqual(self.count, EXPECTED)
        for key, old in self.original:
            with self.subTest(key=key):
                matches = [x for x in self.table[key]
                           if x.source == old.source
                           and x.english == old.english
                           and x.editor_id == old.editor_id
                           and x.occurrence == old.occurrence]
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].korean, NEW)
                self.assertEqual(matches[0].formid, old.formid)
        self.assertEqual(len(NEW), len("상자".encode("utf-8")) + 1)

    def test_exact_source_and_formid_are_required(self):
        for key, original in self.original:
            with self.subTest(key=key):
                name = (original.editor_id or b"")
                data = (encode_subrecord(b"EDID", name + b"\0") +
                        encode_subrecord(b"FULL", b"Crate\0"))
                result = patch_record(
                    data, "Oblivion.esm", b"CONT", original.formid,
                    self.table, Counter(), [],
                )
                payload = [value for kind, value, _ in parse_subrecords(result)
                           if kind == b"FULL"]
                self.assertEqual(payload, [NEW])
                unchanged = patch_record(
                    data, "Oblivion.esm", b"CONT", original.formid + 0x1000000,
                    self.table, Counter(), [],
                )
                self.assertEqual(unchanged, data)
                wrong_english = (encode_subrecord(b"EDID", name + b"\0") +
                                 encode_subrecord(b"FULL", b"Chair\0"))
                self.assertEqual(
                    patch_record(wrong_english, "Oblivion.esm", b"CONT",
                                 original.formid, self.table, Counter(), []),
                    wrong_english,
                )

    def test_drift_rejected_before_any_modification(self):
        blank = {}
        with self.assertRaisesRegex(ValueError, "identity/count drift"):
            correct_crate_names(blank)


if __name__ == "__main__":
    unittest.main()
