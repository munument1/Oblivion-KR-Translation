"""Regression checks for the isolated GitHub issue #6 markup corrections."""
from __future__ import annotations

import re
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from issue6_book_markup_fix import (
    BASE, BR, JOURNAL_ID, UOP, candidate_manifest, correct_selected_book,
    csv_books, digest, fix_breaks, load_manifest, validate_snapshot,
)


class Issue6BookMarkupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = load_manifest()
        cls.base = csv_books("canonical_translation_v2.csv")
        cls.uop = csv_books("canonical_unofficial_translation_v2.csv")

    def payload(self, plugin: str, fid: str):
        row = self.base[(BASE, fid)] if plugin == BASE else self.uop[(UOP, fid)]
        # The current UOP forwarder selects the base-game canonical target
        # after the UOP-specific canonical translation.
        base = self.base[(BASE, fid)]
        source = row["old_english"].encode("cp1252") + b"\0"
        chosen = bytes.fromhex(base["obcjk_utf8_hex"])
        return row["editor_id"].encode("ascii"), source, chosen

    def test_pinned_snapshot_and_source_count(self):
        self.assertEqual(candidate_manifest(), list(self.pins.values()))
        snapshot = validate_snapshot()
        self.assertEqual(snapshot["cases"], 61)
        self.assertEqual(snapshot["vanilla"], 52)
        self.assertEqual(snapshot["uop_forwarded"], 9)
        self.assertFalse(snapshot["game_runtime_verified"])

    def test_every_case_checks_sha_and_returns_exact_corrected_payload(self):
        for (plugin, formid), entry in self.pins.items():
            with self.subTest(plugin=plugin, formid=formid):
                editor, original, chosen = self.payload(plugin, formid)
                self.assertEqual(digest(original), entry["source_sha256"])
                self.assertEqual(digest(chosen), entry["prior_ko_sha256"])
                corrected = correct_selected_book(
                    plugin, int(formid, 16), editor, original, chosen, self.pins)
                self.assertEqual(digest(corrected), entry["corrected_ko_sha256"])
                self.assertTrue(corrected.endswith(b"\0"))
                self.assertNotIn(b"\0", corrected[:-1])
                # The transformation is idempotent once the result is pinned.
                self.assertEqual(
                    correct_selected_book(
                        plugin, int(formid, 16), editor, original, corrected, self.pins),
                    corrected,
                )
                if entry["mode"] == "plain_newlines":
                    self.assertNotIn("<br>", corrected[:-1].decode("utf-8").lower())

    def test_shop_leaflets_keep_all_non_markup_text_unchanged(self):
        for (plugin, fid), entry in self.pins.items():
            if fid == JOURNAL_ID:
                continue
            editor, source, chosen = self.payload(plugin, fid)
            after = correct_selected_book(plugin, int(fid, 16), editor, source, chosen, self.pins)
            before_text = chosen[:-1].decode("utf-8")
            after_text = after[:-1].decode("utf-8")
            # Ignore only the new linebreak characters we explicitly inserted.
            self.assertEqual(BR.sub("", before_text).replace("\r", "").replace("\n", ""),
                             after_text.replace("\r", "").replace("\n", ""),
                             f"Unexpected body-text edit at {plugin} {fid}")
            self.assertFalse(re.search(r"<\s*br\s*/?>", after_text, re.I))

    def test_uop_journal_retains_original_html_break_syntax(self):
        editor, source, chosen = self.payload(UOP, JOURNAL_ID)
        english = source[:-1].decode("cp1252")
        self.assertTrue(english.startswith("<font face=5>"))
        self.assertIn("<BR>", english)
        corrected = correct_selected_book(
            UOP, int(JOURNAL_ID, 16), editor, source, chosen, self.pins)
        text = corrected[:-1].decode("utf-8")
        self.assertIn("<BR>", text)
        self.assertNotIn("<br>", text)
        self.assertNotIn("\n", text.replace("\r\n", ""))
        self.assertTrue(text.startswith("<font face=5>\r\n<BR>\r\n"))
        self.assertTrue(text.endswith("\r\n</font>"))
        inner = text[len("<font face=5>\r\n<BR>\r\n"):-len("\r\n</font>")]
        self.assertEqual(re.sub(r"<br>", "", chosen[:-1].decode("utf-8"), flags=re.I)
                         .replace("\r", "").replace("\n", ""),
                         re.sub(r"<BR>", "", inner).replace("\r", "").replace("\n", ""))

    def test_issue_screenshot_shop_text_matches_record_00071777(self):
        # Screenshot 1973a2fb: parchment at The Main Ingredient.
        row = self.base[(BASE, "00071777")]
        self.assertEqual(row["editor_id"], "ClutterICShop02")
        self.assertIn("The Main Ingredient", row["old_english"])
        editor, source, chosen = self.payload(BASE, "00071777")
        text = chosen[:-1].decode("utf-8")
        self.assertIn("최고의 품질을 자랑합니다.<br>", text)
        after = correct_selected_book(BASE, 0x00071777, editor, source, chosen, self.pins)
        self.assertIn("최고의 품질을 자랑합니다.\r\n", after[:-1].decode("utf-8"))
        self.assertNotIn("<br>", after[:-1].decode("utf-8"))

    def test_non_target_is_untouched_and_stale_changes_fail_closed(self):
        fid = int(JOURNAL_ID, 16)
        editor, source, chosen = self.payload(BASE, JOURNAL_ID)
        self.assertIsNone(correct_selected_book(BASE, 0x12345678,
                                               editor, source, None, self.pins))
        self.assertIs(chosen, correct_selected_book(BASE, 0x12345678,
                                                   editor, source, chosen, self.pins))
        for e, s, c, expected in (
            (b"WrongEditor", source, chosen, "editor"),
            (editor, source + b"x", chosen, "source"),
            (editor, source, chosen + b"x", "translation"),
        ):
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(ValueError, expected):
                    correct_selected_book(BASE, fid, e, s, c, self.pins)
        with self.assertRaisesRegex(ValueError, "candidate missing"):
            correct_selected_book(BASE, fid, editor, source, None, self.pins)

    def test_source_markup_guard_and_literal_newline_context(self):
        # A literal tag alongside a newline uses the original physical newline.
        self.assertEqual(fix_breaks("첫째<br>\n둘째<br>".encode() + b"\0", "plain_newlines"),
                         "첫째\n둘째\r\n".encode() + b"\0")
        with self.assertRaisesRegex(ValueError, "expected literal"):
            fix_breaks("일반 문장".encode() + b"\0", "plain_newlines")
        with self.assertRaisesRegex(ValueError, "NUL-terminated"):
            fix_breaks(b"not nul", "plain_newlines")

    def test_vanilla_builder_applies_markup_fix_to_real_csv_source(self):
        from build_vanilla_overlay import (
            Translation, encode_subrecord, parse_subrecords, patch_record,
        )

        fid = 0x00071777
        row = self.base[(BASE, "00071777")]
        editor, original, prior = self.payload(BASE, "00071777")
        translations = {
            (BASE, b"BOOK", fid, b"DESC"): [
                Translation(BASE, b"BOOK", fid, b"DESC", row["old_english"],
                            prior, 1, editor, 0)
            ]
        }
        record = (encode_subrecord(b"EDID", editor + b"\0")
                  + encode_subrecord(b"DESC", original))
        audit = []
        corrected_record = patch_record(
            record, BASE, b"BOOK", fid, translations, Counter(), audit,
            utf8_untranslated=True)
        desc = [value for field, value, _ in parse_subrecords(corrected_record)
                if field == b"DESC"]
        self.assertEqual(len(desc), 1)
        self.assertEqual(desc[0], correct_selected_book(
            BASE, fid, editor, original, prior, self.pins))
        self.assertEqual(audit[0]["source_sha256"], digest(original))

    def test_uop_builder_applies_markup_fix_after_base_forwarding(self):
        from build_unofficial_release import collect_changes

        fid = int(JOURNAL_ID, 16)
        editor, source, forwarded_target = self.payload(UOP, JOURNAL_ID)
        fake_records = {
            (b"TES4", 0): [(b"MAST", b"Oblivion.esm\0")],
            (b"BOOK", fid): [
                (b"EDID", editor + b"\0"),
                (b"FULL", b"Journal of the Lord Lovidicus\0"),
                (b"DESC", source),
            ],
        }

        def fake_forward(*args):
            return forwarded_target if args[4] == b"DESC" else None

        with (patch("build_unofficial_release.read_records", return_value=fake_records),
              patch("build_unofficial_release.forward_text", side_effect=fake_forward)):
            changes, counts = collect_changes(
                Path(UOP), None, text_forwarding={"mock": True})
        expected = correct_selected_book(
            UOP, fid, editor, source, forwarded_target, self.pins)
        desc_replacement = [value for field, _, value in
                            changes[(b"BOOK", fid)].values() if field == b"DESC"]
        self.assertEqual(desc_replacement, [expected])
        self.assertEqual(counts["canonical_text_forwarded"], 1)


if __name__ == "__main__":
    unittest.main()
