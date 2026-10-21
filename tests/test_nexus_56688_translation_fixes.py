"""Regression checks for Nexus 56688 translation feedback."""
import csv
import unittest
from collections import Counter
from pathlib import Path

from build_vanilla_overlay import (
    encode_subrecord,
    load_translations,
    parse_subrecords,
    patch_record,
)
from oblivion_korean_codec import decode_legacy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "canonical_translation_v2.csv"


class Nexus56688TranslationFixesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {}
        cls.by_record = {}
        with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["effective_source"] != "Oblivion.esm":
                    continue
                record = (row["record_type"], row["raw_formid"], row["field"])
                if record not in {
                    ("INFO", "000272AE", "NAM1"),
                    ("INFO", "0004762A", "NAM1"),
                    ("QUST", "000224EB", "CNAM"),
                    ("INFO", "000152E5", "NAM1"),
                    ("INFO", "000164D6", "NAM1"),
                    ("INFO", "0001C284", "NAM1"),
                    ("INFO", "0001DC4C", "NAM1"),
                    ("INFO", "00146846", "NAM1"),
                }:
                    continue
                key = (*record, int(row["occurrence"]))
                cls.rows[key] = row
                cls.by_record.setdefault(record, []).append(row)
        cls.table = load_translations(SOURCE, encoded_column="obcjk_utf8_hex")

    def test_tenets_are_spoken_naturally_with_correct_numbering(self):
        record = ("INFO", "000272AE", "NAM1")
        rows = sorted(self.by_record[record], key=lambda r: int(r["occurrence"]))
        self.assertEqual([int(r["occurrence"]) for r in rows], list(range(6)))
        self.assertEqual(rows[0]["new_korean"], "오계명은 다음과 같네.")
        for number, row in enumerate(rows[1:], 1):
            self.assertTrue(row["new_korean"].startswith(f"제{number}계명. "))
            self.assertIn("시디스의 분노", row["new_korean"])
            self.assertNotIn("래스", row["new_korean"])
            self.assertNotIn(":", row["new_korean"])
        self._assert_patch_matches_rows(record, rows)

    def test_sanguine_quest_journal_preserves_stage_ownership(self):
        record = ("QUST", "000224EB", "CNAM")
        rows = sorted(self.by_record[record], key=lambda r: int(r["occurrence"]))
        target = self.rows[(*record, 2)]
        self.assertIn("'생귄, 나의 형제여'", target["new_korean"])
        self.assertNotIn("상귀인", target["new_korean"])
        self.assertIn('"Sanguine, my Brother"', target["old_english"])
        self._assert_patch_matches_rows(record, rows)

    def test_jollring_keeps_polite_first_person(self):
        record = ("INFO", "0004762A", "NAM1")
        row = self.rows[(*record, 0)]
        self.assertEqual(
            row["new_korean"],
            "집사, 졸링입니다. 전 수년 동안 움바카노 주인님을 모셔 왔습니다.",
        )
        self.assertIn("Jollring, the butler.", row["old_english"])
        self._assert_patch_matches_rows(record, [row])

    def test_arena_brawler_dialogue_uses_translated_rank(self):
        for formid in ("000152E5", "000164D6", "0001C284",
                       "0001DC4C", "00146846"):
            with self.subTest(formid=formid):
                record = ("INFO", formid, "NAM1")
                rows = self.by_record[record]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["occurrence"], "0")
                self.assertIn("Brawler", rows[0]["old_english"])
                self.assertIn("싸움꾼", rows[0]["new_korean"])
                self.assertNotIn("브롤러", rows[0]["new_korean"])
                self._assert_patch_matches_rows(record, rows)

        # All dialogue mentioning the Brawler rank should display the
        # translated rank, including rows outside the five reported fixes.
        mentions = 0
        with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["record_type"] != "INFO" or row["field"] != "NAM1":
                    continue
                self.assertNotIn(
                    "브롤러", row["new_korean"],
                    (row["effective_source"], row["raw_formid"], row["occurrence"]),
                )
                if "Brawler" in row["old_english"]:
                    mentions += 1
                    self.assertIn(
                        "싸움꾼", row["new_korean"],
                        (row["effective_source"], row["raw_formid"], row["occurrence"]),
                    )
        self.assertEqual(mentions, 10)

    def _assert_patch_matches_rows(self, record, rows):
        for row in rows:
            text = row["new_korean"]
            self.assertEqual(row["obcjk_unicode_text"], text)
            self.assertEqual(bytes.fromhex(row["obcjk_utf8_hex"]), text.encode("utf-8") + b"\0")
            self.assertEqual(
                decode_legacy(bytes.fromhex(row["new_bytes_hex"])[:-1]), text
            )

        kind, formid, field = record
        body = b"".join(
            encode_subrecord(field.encode("ascii"), row["old_english"].encode("cp1252") + b"\0")
            for row in rows
        )
        # Quest journal translations are tied to Dark01Knife's EDID in the
        # actual plugin, so the synthetic record must carry that identity.
        if rows[0]["editor_id"]:
            body = encode_subrecord(b"EDID", rows[0]["editor_id"].encode("ascii") + b"\0") + body
        result = patch_record(body, "Oblivion.esm", kind.encode("ascii"),
                              int(formid, 16), self.table, Counter(), [])
        values = [value for signature, value, _ in parse_subrecords(result)
                  if signature == field.encode("ascii")]
        self.assertEqual(values, [bytes.fromhex(row["obcjk_utf8_hex"]) for row in rows])
        self.assertEqual(
            patch_record(body, "Oblivion.esm", kind.encode("ascii"),
                         int(formid, 16) + 1, self.table, Counter(), []),
            body,
        )


if __name__ == "__main__":
    unittest.main()
