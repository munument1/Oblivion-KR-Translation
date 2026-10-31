"""Issue #8 Cupboard semantic correction against real, intact canonical records."""
from __future__ import annotations

import unittest
from pathlib import Path
from collections import Counter

from build_vanilla_overlay import load_translations
from book_title_overrides import apply_book_title_overrides
from issue8_reporter_term_patch import correct_reporter_terms
from issue8_remaining_term_patch import correct_remaining_glossary_names
from issue8_context_verified_patch import correct_context_verified_names
from issue8_cupboard_patch import EXPECTED, correct_cupboard_names

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "canonical_translation_v2.csv"


class CupboardRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        table = load_translations(
            ORIGINAL,
            (ROOT / "canonical_ui_supplement_v1.csv",
             ROOT / "canonical_nexus_56688_fur_v1.csv"),
            encoded_column="obcjk_utf8_hex",
        )
        apply_book_title_overrides(table, ROOT / "canonical_book_title_overrides_v1.csv")
        correct_reporter_terms(table, ORIGINAL)
        correct_remaining_glossary_names(table, ORIGINAL)
        correct_context_verified_names(table, ORIGINAL)
        cls.before = {key: tuple(items) for key, items in table.items()}
        cls.counts = correct_cupboard_names(table, ORIGINAL)
        cls.after = table

    def test_exact_counts(self):
        self.assertEqual(self.counts, EXPECTED)
        self.assertEqual(sum(self.counts.values()), 51)

    def test_only_51_original_records_change(self):
        changed = 0
        for key, items in self.before.items():
            after = self.after[key]
            self.assertEqual(len(items), len(after))
            for old, new in zip(items, after):
                self.assertEqual(
                    (old.source, old.record_type, old.formid, old.field,
                     old.english, old.editor_id, old.line, old.occurrence),
                    (new.source, new.record_type, new.formid, new.field,
                     new.english, new.editor_id, new.line, new.occurrence),
                )
                if old.korean != new.korean:
                    self.assertEqual(new.source, "Oblivion.esm")
                    changed += 1
        self.assertEqual(changed, 51)

    def test_base_game_and_official_dlc_cupboard_labels(self):
        counts=Counter()
        for key, items in self.after.items():
            for item in items:
                if item.record_type==b"CONT" and item.field==b"FULL" and item.english=="Cupboard":
                    ko=item.korean[:-1].decode("utf-8")
                    self.assertEqual(ko, "찬장")
                    counts[item.source]+=1
        self.assertEqual(counts["Oblivion.esm"],48)
        self.assertEqual(sum(counts.values()),54)

    def test_thieves_guild_journal_mentions_myvryna_cupboard(self):
        key=("Oblivion.esm",b"QUST",0x00034EA2,b"CNAM")
        affected=[x for x in self.after[key] if "Myvryna" in x.english and "cupboard" in x.english.lower()]
        self.assertEqual(len(affected),2)
        self.assertTrue(all("미브리나의 찬장" in x.korean[:-1].decode("utf-8") for x in affected))

    def test_book_cupboard_and_shelf_terms_are_distinct(self):
        key=("Oblivion.esm",b"BOOK",0x00090EB2,b"DESC")
        affected=[x for x in self.after[key] if "Food Cupboard" in x.english]
        self.assertEqual(len(affected),1)
        after=affected[0].korean[:-1].decode("utf-8")
        self.assertIn("음식 찬장",after)
        self.assertNotIn("컵보드",after)
        # Shelves in a different furnishing list remain '선반', not '찬장'.
        source=("Oblivion.esm",b"BOOK",0x000B15DA,b"DESC")
        self.assertEqual(
            [x.korean for x in self.before[source]],
            [x.korean for x in self.after[source]],
        )

    def test_glossary_chooses_cupboard_not_shelf(self):
        path=ROOT/"docs/v2_review/OBLIVION_GLOSSARY_V2_ACTIVE.csv"
        from csv import DictReader
        with path.open(encoding="utf-8-sig",newline="") as f:
            matches=[row for row in DictReader(f) if row.get("english")=="Cupboard" or
                     row.get("source")=="Cupboard" or row.get("en")=="Cupboard"]
        if matches:
            self.assertTrue(any("찬장" in row.values() for row in matches))
        else:
            self.assertIn("Cupboard,찬장,EXACT_ONLY,",path.read_text(encoding="utf-8-sig"))

    def test_empty_input_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"Cupboard source drift"):
            correct_cupboard_names({})


if __name__ == "__main__":
    unittest.main()
