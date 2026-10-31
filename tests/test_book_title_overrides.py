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
        table = table_with("진짜 바렌지아, 제 5권", "미씩 던 논평집 2")
        self.assertEqual(apply_book_title_overrides(table, OVERRIDES), 1)
        self.assertEqual(table[TITLE_KEY][0].korean[:-1].decode("utf-8"),
                         "진정한 바렌지아, 제 5권")
        self.assertEqual(table[COMMENTARIES_2_KEY][0].korean[:-1].decode("utf-8"),
                         "미씩 던 논평집 2")

    def test_second_commentaries_title_matches_other_volumes(self):
        table = table_with("진정한 바렌지아, 제 5권", "미씩 던 주석서 2")
        before = table[COMMENTARIES_2_KEY][0]
        self.assertEqual(apply_book_title_overrides(table, OVERRIDES), 1)
        after = table[COMMENTARIES_2_KEY][0]
        self.assertEqual(after.korean[:-1].decode("utf-8"), "미씩 던 논평집 2")
        self.assertEqual(
            (after.source, after.record_type, after.formid, after.field,
             after.english, after.line, after.editor_id, after.occurrence),
            (before.source, before.record_type, before.formid, before.field,
             before.english, before.line, before.editor_id, before.occurrence))
        self.assertEqual(table[TITLE_KEY][0].korean[:-1].decode("utf-8"),
                         "진정한 바렌지아, 제 5권")

    def test_already_correct_is_idempotent(self):
        table = table_with("진정한 바렌지아 5권", "미씩 던 논평집 2")
        self.assertEqual(apply_book_title_overrides(table, OVERRIDES), 0)

    def test_missing_translation_is_caught(self):
        with self.assertRaises(ValueError):
            apply_book_title_overrides(defaultdict(list), OVERRIDES)


if __name__ == "__main__":
    unittest.main()
