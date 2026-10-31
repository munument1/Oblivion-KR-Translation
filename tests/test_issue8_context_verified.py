"""Context-aware name follow-up to issue #8: exact original corpus regression."""
import unittest
from pathlib import Path

from book_title_overrides import apply_book_title_overrides
from build_vanilla_overlay import load_translations
from issue8_reporter_term_patch import correct_reporter_terms
from issue8_remaining_term_patch import correct_remaining_glossary_names
from issue8_context_verified_patch import EXPECTED, correct_context_verified_names

HERE = Path(__file__).resolve().parents[1]
CANONICAL = HERE / "canonical_translation_v2.csv"

class ContextVerifiedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_translations(
            CANONICAL,
            (HERE / "canonical_ui_supplement_v1.csv",
             HERE / "canonical_nexus_56688_fur_v1.csv"),
            encoded_column="obcjk_utf8_hex"
        )
        apply_book_title_overrides(cls.table, HERE / "canonical_book_title_overrides_v1.csv")
        correct_reporter_terms(cls.table, CANONICAL)
        correct_remaining_glossary_names(cls.table, CANONICAL)
        cls.before = {key: tuple(vals) for key, vals in cls.table.items()}
        cls.counts = correct_context_verified_names(cls.table, CANONICAL)

    def test_exact_audited_source_counts_and_all_identifiers_preserved(self):
        self.assertEqual(self.counts,EXPECTED)
        changed = 0
        for key, items in self.before.items():
            after = self.table[key]
            self.assertEqual(len(items),len(after))
            for a,b in zip(items,after):
                self.assertEqual(
                    (a.source,a.record_type,a.formid,a.field,a.english,
                     a.editor_id,a.occurrence,a.line),
                    (b.source,b.record_type,b.formid,b.field,b.english,
                     b.editor_id,b.occurrence,b.line))
                if a.korean != b.korean:
                    self.assertTrue(b.korean.endswith(b"\0"))
                    changed += 1
        self.assertEqual(changed,272)

    def test_real_in_game_title_is_used_in_quest_and_actor_names(self):
        samples = [
          ("Oblivion.esm", b"DIAL", 0x0003C7FE, b"FULL",
           "Bands of the Chosen", "선택받은 자의 팔찌"),
          ("DLCBattlehornCastle.esp", b"NPC_", 0x01013428, b"FULL",
           "Marauder", "습격자"),
          ("Oblivion.esm", b"CREA", 0x000435A2, b"FULL",
           "Gatekeeper", "게이트키퍼"),
        ]
        for key_source, record_type, fid, field, english, expected in samples:
            key = (key_source,record_type,fid,field)
            matches = [x for x in self.table[key] if x.english==english]
            with self.subTest(key=key):
                self.assertEqual(len(matches),1)
                self.assertEqual(matches[0].korean[:-1].decode("utf-8"),expected)
        # Non-name items and the canonical armor FULL keep their wording.
        band_armor = self.table[("Oblivion.esm",b"ARMO",0x0003C803,b"FULL")]
        self.assertEqual(len(band_armor),1)
        self.assertEqual(band_armor[0].korean[:-1].decode("utf-8"),
                         "선택받은 자의 팔찌")

    def test_no_automatic_cupboard_or_general_terms(self):
        key=("Oblivion.esm",b"CONT",0x00005126,b"FULL")
        old=self.before[key]
        new=self.table[key]
        self.assertEqual([r.korean for r in old],[r.korean for r in new])

    def test_empty_corpus_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"source drift"):
            correct_context_verified_names({})

if __name__=="__main__":
    unittest.main()
