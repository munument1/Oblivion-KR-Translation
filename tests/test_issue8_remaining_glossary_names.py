"""Issue #8 second pass original record and safe naming regression tests."""
from __future__ import annotations

import csv
import unittest
from pathlib import Path

from book_title_overrides import apply_book_title_overrides
from build_vanilla_overlay import load_translations
from issue8_reporter_term_patch import correct_reporter_terms
from issue8_remaining_term_patch import (
    correct_remaining_glossary_names, EXPECTED
)

HERE = Path(__file__).resolve().parents[1]
CANONICAL = HERE / "canonical_translation_v2.csv"
LOCATIONS = HERE / "canonical_locations_v2.csv"

class RemainingNamesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_translations(CANONICAL, (
            HERE / "canonical_ui_supplement_v1.csv",
            HERE / "canonical_nexus_56688_fur_v1.csv",
        ), encoded_column="obcjk_utf8_hex")
        apply_book_title_overrides(cls.table, HERE / "canonical_book_title_overrides_v1.csv")
        correct_reporter_terms(cls.table, CANONICAL)
        cls.before={key:list(v) for key,v in cls.table.items()}
        cls.counts=correct_remaining_glossary_names(cls.table,CANONICAL)

    def test_all_named_source_matched_counts(self):
        self.assertEqual(self.counts, EXPECTED)
        self.assertEqual(sum(self.counts.values()), 424)

    def test_all_other_records_and_source_identity_preserved(self):
        changes=0
        for key,items in self.before.items():
            after=self.table[key]
            self.assertEqual(len(items), len(after))
            for old, new in zip(items,after):
                self.assertEqual((old.source,old.record_type,old.formid,old.field,
                    old.english,old.editor_id,old.occurrence,old.line),
                    (new.source,new.record_type,new.formid,new.field,
                     new.english,new.editor_id,new.occurrence,new.line))
                if old.korean != new.korean:
                    changes += 1
                    self.assertEqual(key[0],new.source)
                    self.assertTrue(new.korean.endswith(b"\0"))
        self.assertEqual(changes,424)

    def test_selected_original_fields(self):
        fixtures={
          ("Oblivion.esm", b"DIAL", 0x000025E3, b"FULL"):
            ("Jauffre","죠프리"),
          ("Oblivion.esm", b"WEAP", 0x0004FD09, b"FULL"):
            ("Staff of Sheogorath","쉐오고라스의 지팡이"),
          ("Oblivion.esm", b"ARMO", 0x0001A32B, b"FULL"):
            ("Golden Saint Armor","골든 세인트 아머"),
          ("Oblivion.esm", b"ARMO", 0x0004121D, b"FULL"):
            ("Dark Seducer Helmet","다크 세듀서 헬멧"),
        }
        for key,(english,want) in fixtures.items():
            with self.subTest(key=key):
                hits=[r for r in self.table[key] if r.english==english]
                self.assertEqual(len(hits),1)
                self.assertEqual(hits[0].korean[:-1].decode("utf-8"),want)

    def test_one_location_row_and_hex(self):
        names=[]
        with LOCATIONS.open("r",encoding="utf-8-sig",newline="") as stream:
            for row in csv.DictReader(stream):
                if (row["effective_source"],row["record_type"],
                    row["raw_formid"],row["field"])==(
                        "Oblivion.esm","CELL","0000082B","FULL"):
                    names.append(row)
        self.assertEqual(len(names),1)
        self.assertEqual(names[0]["old_english"],"Modryn Oreyn's House")
        self.assertEqual(names[0]["obcjk_unicode_text"],"모드윈 오레인의 집")
        self.assertEqual(bytes.fromhex(names[0]["obcjk_utf8_hex"]),
                         "모드윈 오레인의 집".encode("utf-8")+b"\0")

    def test_count_guard_rejects_invalid_source(self):
        with self.assertRaisesRegex(ValueError,"source drift"):
            correct_remaining_glossary_names({})

if __name__=="__main__":
    unittest.main()
