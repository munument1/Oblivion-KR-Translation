"""Regression tests for Nexus 56688's mixed Fur armor terminology.

Only exact FormID, record kind, field, source English, occurrence, and EDID
may receive these reviewed overrides. Other armor remains untouched.
"""
import csv
import unittest
from collections import Counter
from pathlib import Path

from build_vanilla_overlay import encode_subrecord, load_translations, parse_subrecords, patch_record

HERE = Path(__file__).resolve().parents[1]
CANONICAL = HERE / "canonical_translation_v2.csv"
FUR = HERE / "canonical_nexus_56688_fur_v1.csv"
EXPECTED = {
    "00024765": ("Fur Gauntlets", "털가죽 장갑", "모피 장갑", "FurGauntlets"),
    "00024767": ("Fur Boots", "털가죽 전투화", "모피 전투화", "FurBoots"),
    "00024768": ("Fur Helmet", "털가죽 투구", "모피 투구", "FurHelmet"),
    "000733E2": ("Fur Helmet", "털가죽 투구", "모피 투구", "ArenaFurHelmet"),
}


class FurTerminologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = {}
        with CANONICAL.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["effective_source"] == "Oblivion.esm" and row["record_type"] == "ARMO" and row["field"] == "FULL" and row["raw_formid"] in EXPECTED:
                    key = row["raw_formid"]
                    if key in cls.original:
                        raise AssertionError(f"duplicate canonical armor {key}")
                    cls.original[key] = row
        cls.overlay = {}
        with FUR.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["raw_formid"] in cls.overlay:
                    raise AssertionError(f"duplicate override armor {row['raw_formid']}")
                cls.overlay[row["raw_formid"]] = row
        cls.table = load_translations(CANONICAL, extra_paths=(FUR,), encoded_column="obcjk_utf8_hex")

    def test_only_four_verified_armor_records_are_overridden(self):
        self.assertEqual(set(self.original), set(EXPECTED))
        self.assertEqual(set(self.overlay), set(EXPECTED))
        for formid, (english, old_korean, new_korean, editor_id) in EXPECTED.items():
            with self.subTest(formid=formid):
                old = self.original[formid]
                new = self.overlay[formid]
                self.assertEqual(old["old_english"], english)
                self.assertEqual(old["new_korean"], old_korean)
                self.assertEqual(old["editor_id"], editor_id)
                self.assertEqual(new["old_english"], english)
                self.assertEqual(new["editor_id"], editor_id)
                self.assertEqual(new["effective_source"], "Oblivion.esm")
                self.assertEqual(new["record_type"], "ARMO")
                self.assertEqual(new["field"], "FULL")
                self.assertEqual(new["occurrence"], "0")
                self.assertEqual(new["new_korean"], new_korean)
                self.assertEqual(bytes.fromhex(new["obcjk_utf8_hex"]), new_korean.encode("utf-8") + b"\0")

    def test_real_overlay_wins_and_guards_identity(self):
        for formid, (english, _, korean, editor_id) in EXPECTED.items():
            with self.subTest(formid=formid):
                kind, fid = b"ARMO", int(formid, 16)
                source = (encode_subrecord(b"EDID", editor_id.encode("ascii") + b"\0") +
                          encode_subrecord(b"FULL", english.encode("ascii") + b"\0"))
                result = patch_record(source, "Oblivion.esm", kind, fid, self.table, Counter(), [])
                fields = dict((sig, val) for sig, val, _ in parse_subrecords(result))
                self.assertEqual(fields[b"FULL"], korean.encode("utf-8") + b"\0")
                self.assertEqual(patch_record(source, "Oblivion.esm", kind, fid + 0x1000000,
                                              self.table, Counter(), []), source)
                incorrect_editor = (encode_subrecord(b"EDID", b"WrongName\0") +
                                    encode_subrecord(b"FULL", english.encode("ascii") + b"\0"))
                self.assertEqual(patch_record(incorrect_editor, "Oblivion.esm", kind, fid,
                                              self.table, Counter(), []), incorrect_editor)
                incorrect_english = (encode_subrecord(b"EDID", editor_id.encode("ascii") + b"\0") +
                                     encode_subrecord(b"FULL", b"Wrong Armor\0"))
                self.assertEqual(patch_record(incorrect_english, "Oblivion.esm", kind, fid,
                                              self.table, Counter(), []), incorrect_english)


if __name__ == "__main__":
    unittest.main()
