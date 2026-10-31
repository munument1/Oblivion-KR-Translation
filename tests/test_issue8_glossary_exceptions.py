"""Issue #8 remaining non-obvious name exceptions: real-corpus regression."""
from __future__ import annotations

import unittest
from pathlib import Path

from build_vanilla_overlay import load_translations
from book_title_overrides import apply_book_title_overrides
from issue8_reporter_term_patch import correct_reporter_terms
from issue8_remaining_term_patch import correct_remaining_glossary_names
from issue8_context_verified_patch import correct_context_verified_names
from issue8_cupboard_patch import correct_cupboard_names
from issue8_glossary_exceptions import EXPECTED, correct_glossary_exceptions

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "canonical_translation_v2.csv"


class GlossaryExceptionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        t = load_translations(
            ORIGINAL,
            (ROOT / "canonical_ui_supplement_v1.csv",
             ROOT / "canonical_nexus_56688_fur_v1.csv"),
            encoded_column="obcjk_utf8_hex"
        )
        apply_book_title_overrides(t, ROOT / "canonical_book_title_overrides_v1.csv")
        correct_reporter_terms(t, ORIGINAL)
        correct_remaining_glossary_names(t, ORIGINAL)
        correct_context_verified_names(t, ORIGINAL)
        correct_cupboard_names(t, ORIGINAL)
        cls.before = {key:list(items) for key,items in t.items()}
        cls.out = correct_glossary_exceptions(t, ORIGINAL)
        cls.table = t

    def test_expected_counts_from_actual_original(self):
        self.assertEqual(self.out["terms"], EXPECTED)
        self.assertEqual(sum(EXPECTED.values()), 25)
        self.assertEqual(self.out["changed_rows"],12)

    def test_source_ids_and_unrelated_fields_untouched(self):
        changed = 0
        for key, olditems in self.before.items():
            newitems=self.table[key]
            self.assertEqual(len(olditems),len(newitems))
            for a,b in zip(olditems,newitems):
                self.assertEqual((a.source,a.record_type,a.formid,a.field,a.english,
                                  a.editor_id,a.occurrence,a.line),
                                 (b.source,b.record_type,b.formid,b.field,b.english,
                                  b.editor_id,b.occurrence,b.line))
                if a.korean!=b.korean:
                    changed +=1
        self.assertEqual(changed,12)

    def test_city_quest_title(self):
        t=self.table[("Oblivion.esm",b"QUST",0x00085483,b"FULL")]
        self.assertEqual(len(t),1)
        self.assertEqual(t[0].korean[:-1].decode("utf-8"),"체이딘할에서 집 구입")

    def test_mysterium_name_and_mankar_in_journal(self):
        t=self.table[("Oblivion.esm",b"QUST",0x0001E728,b"CNAM")]
        matches=[item for item in t if item.english.startswith("Mankar Camoran escaped to his realm of Paradise") and "Mysterium Xarxes" in item.english]
        self.assertEqual(len(matches),1)
        ko=matches[0].korean[:-1].decode("utf-8")
        self.assertIn("작시스의 신비",ko)
        self.assertIn("맨카 캐모런",ko)
        self.assertNotIn("미스테리움 자르크시스",ko)

    def test_book_header_and_knights_book_body(self):
        t=self.table[("Oblivion.esm",b"BOOK",0x00022B07,b"DESC")]
        target=[item for item in t if "COMMENTARIES ON THE MYSTERIUM XARXES" in item.english]
        self.assertEqual(len(target),1)
        self.assertIn("작시스의 신비 주해",target[0].korean[:-1].decode("utf-8"))
        knights=self.table[("Knights.esp",b"BOOK",0x01000ED2,b"DESC")]
        self.assertEqual(len(knights),1)
        text=knights[0].korean[:-1].decode("utf-8")
        self.assertEqual(text.count("나인 디바인 기사단"),0)
        self.assertGreaterEqual(text.count("나인의 기사단"),14)

    def test_empty_corpus_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"source drift"):
            correct_glossary_exceptions({})


if __name__=="__main__":
    unittest.main()
