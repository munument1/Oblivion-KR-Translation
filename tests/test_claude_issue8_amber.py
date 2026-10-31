"""Issue #8 Amber item records: exact, regression-tested translation only."""
import unittest
from pathlib import Path
from collections import Counter

from build_vanilla_overlay import (
    encode_subrecord, load_translations, parse_subrecords, patch_record,
)
from claude_issue8_amber import EXPECTED, correct_amber_equipment_names

HERE = Path(__file__).resolve().parents[1]
FIXTURE_IDS = {
    0x16C7F: ("Fine Amber Arrow", "훌륭한 황색 화살", "훌륭한 호박석 화살"),
    0x16578: ("Amber Helmet", "황색 투구", "호박석 투구"),
    0x16C1C: ("Fine Amber Cuirass", "훌륭한 앰버 흉갑", "훌륭한 호박석 흉갑"),
}


class AmberTerminologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_translations(
            HERE / "canonical_translation_v2.csv", encoded_column="obcjk_utf8_hex"
        )
        cls.before = {key: list(items) for key, items in cls.table.items()}
        cls.counts = correct_amber_equipment_names(cls.table)

    def test_only_151_source_verified_equipment_rows_change(self):
        self.assertEqual(self.counts, EXPECTED)
        changed = 0
        for key, before in self.before.items():
            after = self.table[key]
            self.assertEqual(len(before), len(after))
            for old, new in zip(before, after):
                self.assertEqual(
                    (old.source, old.record_type, old.formid, old.field,
                     old.english, old.line, old.editor_id, old.occurrence),
                    (new.source, new.record_type, new.formid, new.field,
                     new.english, new.line, new.editor_id, new.occurrence),
                )
                if old.korean != new.korean:
                    changed += 1
                    self.assertEqual(key[0], "Oblivion.esm")
                    self.assertIn(key[1], (b"AMMO", b"ARMO", b"WEAP"))
                    self.assertEqual(key[3], b"FULL")
                    self.assertTrue(new.editor_id.startswith(b"SE"))
                    self.assertIn("Amber", old.english)
                    self.assertTrue(new.korean.endswith(b"\0"))
                    self.assertIn("호박석", new.korean[:-1].decode("utf-8"))
        self.assertEqual(changed, 151)

    def test_real_record_patch_is_identity_scoped(self):
        for formid, (english, old_ko, new_ko) in FIXTURE_IDS.items():
            matching = [
                (key, item) for key, items in self.before.items()
                if key[0] == "Oblivion.esm" and key[2] == formid
                and key[3] == b"FULL" for item in items
                if item.english == english and
                item.korean == old_ko.encode("utf-8") + b"\0"
            ]
            self.assertEqual(len(matching), 1, formid)
            key, item = matching[0]
            identity = (encode_subrecord(b"EDID", item.editor_id + b"\0") +
                        encode_subrecord(b"FULL", english.encode("ascii") + b"\0"))
            output = patch_record(identity, "Oblivion.esm", key[1],
                                  formid, self.table, Counter(), [])
            fields = dict((sig, val) for sig, val, _ in parse_subrecords(output))
            self.assertEqual(fields[b"FULL"], new_ko.encode("utf-8") + b"\0")
            self.assertEqual(
                patch_record(identity, "Oblivion.esm", key[1],
                             formid + 0x01000000, self.table, Counter(), []),
                identity,
            )

    def test_count_drift_prevents_edits(self):
        fake = {("Oblivion.esm", b"ARMO", 1, b"FULL"): []}
        with self.assertRaisesRegex(ValueError, "source drift"):
            correct_amber_equipment_names(fake)


if __name__ == "__main__":
    unittest.main()
