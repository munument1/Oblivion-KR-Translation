import unittest
from collections import defaultdict
from pathlib import Path

from book_title_overrides import apply_book_title_overrides
from build_vanilla_overlay import Translation

HERE = Path(__file__).resolve().parents[1]
OVERRIDES = HERE / "canonical_book_title_overrides_v1.csv"
TITLE_KEY = ("Oblivion.esm", b"BOOK", 0x00024574, b"FULL")
COMMENTARIES_2_KEY = ("Oblivion.esm", b"BOOK", 0x00022B05, b"FULL")


def book(title, formid=0x00024574):
    return Translation("Oblivion.esm", b"BOOK", formid, b"FULL",
                       "The Real Barenziah, v 5",
                       title.encode("utf-8") + b"\0", 2)


def commentary_2(title):
    return Translation("Oblivion.esm", b"BOOK", 0x00022B05, b"FULL",
                       "Mythic Dawn Commentaries 2",
                       title.encode("utf-8") + b"\0", 2)


def table_with(barenziah, commentary):
    return defaultdict(list, {
        TITLE_KEY: [book(barenziah)],
        COMMENTARIES_2_KEY: [commentary_2(commentary)],
    })


class BookTitleOverridesTests(unittest.TestCase):
    def test_fifth_volume_corrected_without_changing_suffix(self):
        table = table_with("진짜 바렌지아, 제 5권", "미식 던 논평집 2")
        self.assertEqual(apply_book_title_overrides(table, OVERRIDES), 1)
        self.assertEqual(table[TITLE_KEY][0].korean[:-1].decode("utf-8"),
                         "진정한 바렌지아, 제 5권")
        self.assertEqual(table[COMMENTARIES_2_KEY][0].korean[:-1].decode("utf-8"),
                         "미식 던 논평집 2")

    def test_second_commentaries_title_matches_other_volumes(self):
        table = table_with("진정한 바렌지아, 제 5권", "미씩 던 주석서 2")
        before = table[COMMENTARIES_2_KEY][0]
        self.assertEqual(apply_book_title_overrides(table, OVERRIDES), 1)
        after = table[COMMENTARIES_2_KEY][0]
        self.assertEqual(after.korean[:-1].decode("utf-8"), "미식 던 논평집 2")
        self.assertEqual(
            (after.source, after.record_type, after.formid, after.field,
             after.english, after.line, after.editor_id, after.occurrence),
            (before.source, before.record_type, before.formid, before.field,
             before.english, before.line, before.editor_id, before.occurrence))
        self.assertEqual(table[TITLE_KEY][0].korean[:-1].decode("utf-8"),
                         "진정한 바렌지아, 제 5권")

    def test_already_correct_is_idempotent(self):
        table = table_with("진정한 바렌지아 5권", "미식 던 논평집 2")
        self.assertEqual(apply_book_title_overrides(table, OVERRIDES), 0)

    def test_actual_canonical_second_volume_is_source_anchored(self):
        # Only the display text is amended at build time; canonical input is not rewritten.
        from build_vanilla_overlay import load_translations
        table = load_translations(HERE / "canonical_translation_v2.csv",
                                  encoded_column="obcjk_utf8_hex")
        matches = [item for item in table[COMMENTARIES_2_KEY]
                   if item.source == "Oblivion.esm"
                   and item.record_type == b"BOOK"
                   and item.formid == 0x00022B05
                   and item.field == b"FULL"
                   and item.english == "Mythic Dawn Commentaries 2"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].korean, "미씩 던 주석서 2".encode("utf-8") + b"\0")
        original_key = (matches[0].source, matches[0].record_type,
                        matches[0].formid, matches[0].field,
                        matches[0].english, matches[0].line,
                        matches[0].editor_id, matches[0].occurrence)
        apply_book_title_overrides(table, OVERRIDES)
        after = [item for item in table[COMMENTARIES_2_KEY]
                 if item.english == "Mythic Dawn Commentaries 2"]
        self.assertEqual(len(after), 1)
        self.assertEqual(after[0].korean, "미식 던 논평집 2".encode("utf-8") + b"\0")
        self.assertEqual(original_key, (after[0].source, after[0].record_type,
                         after[0].formid, after[0].field, after[0].english,
                         after[0].line, after[0].editor_id, after[0].occurrence))

    def test_missing_translation_is_caught(self):
        with self.assertRaises(ValueError):
            apply_book_title_overrides(defaultdict(list), OVERRIDES)


if __name__ == "__main__":
    unittest.main()
