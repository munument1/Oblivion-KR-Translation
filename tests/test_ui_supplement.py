import csv
import struct
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from build_vanilla_overlay import encode_subrecord, load_translations, parse_subrecords, patch_plugin

HERE = Path(__file__).resolve().parents[1]
TABLE = HERE / "canonical_ui_supplement_v1.csv"


class UISupplementTests(unittest.TestCase):
    def test_ui_supplement_integrity(self):
        with TABLE.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))

        self.assertEqual(len(rows), 238)
        self.assertEqual(
            Counter(row["record_type"] for row in rows),
            Counter({"FACT": 136, "SKIL": 84, "INFO": 14, "QUST": 2, "NPC_": 1, "DOOR": 1}),
        )

        identities = {
            (
                row["effective_source"],
                row["record_type"],
                row["raw_formid"],
                row["field"],
                row["editor_id"],
                row["occurrence"],
            )
            for row in rows
        }
        self.assertEqual(len(identities), len(rows))

        for row in rows:
            self.assertTrue(row["old_english"])
            self.assertTrue(row["obcjk_unicode_text"])
            encoded = bytes.fromhex(row["obcjk_utf8_hex"])
            self.assertTrue(encoded.endswith(b"\0"))
            self.assertEqual(
                encoded[:-1].decode("utf-8"),
                row["obcjk_unicode_text"],
            )

    def test_official_chapel_locations_present(self):
        location_table = HERE / "canonical_locations_v2.csv"
        with location_table.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))

        expected = {
            ("000308CD", "AnvilChapelofDibella"): "디벨라 예배당",
            ("00030427", "CheydinhalChapelOfArkay"): "아케이의 대성당",
            ("00030537", "LeyawiinChapelOfZenithar"): "제니타르의 대성당",
            ("0000080A", "ChorrolChapelOfStendarr"): "스텐다르 예배당",
        }
        actual = {
            (r["raw_formid"], r["editor_id"]): r["obcjk_unicode_text"]
            for r in rows
            if r["effective_source"] == "Oblivion.esm"
            and (r["raw_formid"], r["editor_id"]) in expected
        }
        self.assertEqual(actual, expected)

    def test_key_user_visible_rows_present(self):
        with TABLE.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))

        keys = {
            (r["record_type"], r["raw_formid"], r["field"], r["occurrence"]): r
            for r in rows
        }
        self.assertEqual(keys[("SKIL", "00000044", "ANAM", "")]["editor_id"], "SkillAlchemy")
        self.assertEqual(keys[("FACT", "0002F872", "MNAM", "5")]["obcjk_unicode_text"], "사일렌서")
        self.assertEqual(keys[("FACT", "0006A7FC", "MNAM", "9")]["obcjk_unicode_text"], "광기의 신")
        self.assertIn(("QUST", "00081DD5", "CNAM", "0"), keys)
        self.assertEqual(keys[("INFO", "0003E452", "NAM1", "0")]["obcjk_unicode_text"], "그쪽 전리품을 살펴보고 싶구만.")
        self.assertEqual(keys[("NPC_", "000908B2", "FULL", "0")]["obcjk_unicode_text"], "검은 활 도적")
        self.assertEqual(keys[("DOOR", "000282AF", "FULL", "0")]["obcjk_unicode_text"], "나무 문")

    def test_arena_combatant_rank_names_complete(self):
        with TABLE.open(encoding="utf-8-sig", newline="") as stream:
            rows = [
                r for r in csv.DictReader(stream)
                if r["effective_source"] == "Oblivion.esm"
                and r["record_type"] == "FACT"
                and r["raw_formid"] == "000299B9"
                and r["editor_id"] == "ArenaCombatants"
            ]
        ranks = {
            0: ("Pit Dog", "투견"),
            1: ("Brawler", "싸움꾼"),
            2: ("Bloodletter", "블러드레터"),
            3: ("Myrmidon", "미르미돈"),
            4: ("Warrior", "전사"),
            5: ("Gladiator", "검투사"),
            6: ("Hero", "영웅"),
            7: ("Champion", "챔피언"),
            8: ("Grand Champion", "그랜드 챔피언"),
        }
        by_key = {(r["field"], int(r["occurrence"])): r for r in rows}
        self.assertEqual(set(by_key), {(field, rank) for field in ("MNAM", "FNAM") for rank in ranks})
        for rank, (english, korean) in ranks.items():
            for field in ("MNAM", "FNAM"):
                row = by_key[(field, rank)]
                self.assertEqual(row["old_english"], english)
                self.assertEqual(row["obcjk_unicode_text"], korean)
                self.assertEqual(bytes.fromhex(row["obcjk_utf8_hex"]), korean.encode("utf-8") + b"\0")

    def test_player_faction_rank_fields_cover_every_level(self):
        with TABLE.open(encoding="utf-8-sig", newline="") as stream:
            rows = [r for r in csv.DictReader(stream) if r["record_type"] == "FACT"]
        expected = {
            "000299B9": ("Oblivion.esm", "ArenaCombatants", 9),
            "00024164": ("Oblivion.esm", "ThievesGuild", 8),
            "0002F872": ("Oblivion.esm", "DarkBrotherhood", 8),
            "0002228F": ("Oblivion.esm", "FightersGuild", 10),
            "00022296": ("Oblivion.esm", "MagesGuild", 10),
            "000274AB": ("Oblivion.esm", "Blades", 3),
            "0006A7FC": ("Oblivion.esm", "SECourtofMadnessFaction", 10),
            "01000CEE": ("Knights.esp", "NDKnightsoftheNine", 3),
        }
        for fid, (source, editor, length) in expected.items():
            relevant = [r for r in rows if r["effective_source"] == source and r["raw_formid"] == fid]
            self.assertEqual(
                {(r["field"], int(r["occurrence"])) for r in relevant},
                {(field, rank) for field in ("MNAM", "FNAM") for rank in range(length)},
                msg=f"{editor} {fid} rank coverage",
            )
            self.assertTrue(all(r["editor_id"] == editor for r in relevant))
        court = {(r["field"], int(r["occurrence"])): r for r in rows if r["raw_formid"] == "0006A7FC"}
        for field, rank, source, target in (
            ("FNAM", 5, "Duchess of Dementia", "디멘시아의 여공작"),
            ("FNAM", 6, "Duchess of Mania", "매니아의 여공작"),
            ("MNAM", 7, "Regent", "섭정"),
            ("FNAM", 7, "Regent", "섭정"),
            ("FNAM", 8, "Defender of the Realm", "왕국의 수호자"),
            ("MNAM", 9, "Madgod", "광기의 신"),
            ("FNAM", 9, "Madgod", "광기의 신"),
        ):
            row = court[(field, rank)]
            self.assertEqual((row["old_english"], row["obcjk_unicode_text"]), (source, target))

    def test_faction_rank_overrides_apply_through_release_patcher(self):
        """A synthetic grouped plugin exercises the real release patcher's fast path."""
        translations = load_translations(
            HERE / "canonical_translation_v2.csv", (TABLE,), encoded_column="obcjk_utf8_hex"
        )
        with TABLE.open(encoding="utf-8-sig", newline="") as stream:
            rows = [r for r in csv.DictReader(stream)
                    if r["record_type"] == "FACT" and r["effective_source"] == "Oblivion.esm"]
        by_form = {}
        player_faction_ids = {
            0x000299B9, 0x00024164, 0x0002F872, 0x0002228F,
            0x00022296, 0x000274AB, 0x0006A7FC,
        }
        for row in rows:
            fid = int(row["raw_formid"], 16)
            if fid in player_faction_ids:
                by_form.setdefault(fid, []).append(row)
        records = []
        for fid, rank_rows in by_form.items():
            full_candidates = translations.get(("Oblivion.esm", b"FACT", fid, b"FULL"), ())
            if not full_candidates:
                continue
            old_full = full_candidates[0].english.encode("cp1252") + b"\0"
            body = (
                encode_subrecord(b"EDID", rank_rows[0]["editor_id"].encode("ascii") + b"\0")
                + encode_subrecord(b"FULL", old_full)
            )
            ranks = sorted({int(r["occurrence"]) for r in rank_rows})
            for rank in ranks:
                body += encode_subrecord(b"RNAM", struct.pack("<I", rank))
                for field in ("MNAM", "FNAM"):
                    matches = [r for r in rank_rows if int(r["occurrence"]) == rank and r["field"] == field]
                    self.assertEqual(len(matches), 1)
                    body += encode_subrecord(field.encode("ascii"), matches[0]["old_english"].encode("cp1252") + b"\0")
            rec = struct.pack("<4sIIII", b"FACT", len(body), 0, fid, 0) + body
            records.append((fid, len(ranks), rec))
        self.assertEqual(len(records), 7)
        data = b"".join(r[2] for r in records)
        group = b"GRUP" + struct.pack("<I", len(data) + 20) + b"FACT" + b"\0" * 8 + data
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "original.esm", Path(tmp) / "patched.esm"
            source.write_bytes(group)
            counts = Counter()
            patch_plugin(source, target, "Oblivion.esm", translations, counts, [], utf8_untranslated=True)
            raw = target.read_bytes()
        self.assertEqual(counts["applied"], sum(2 * n + 1 for _, n, _ in records))
        pos = 20
        for fid, nranks, _ in records:
            kind, size, _, got_fid, _ = struct.unpack_from("<4sIIII", raw, pos)
            self.assertEqual((kind, got_fid), (b"FACT", fid))
            parts = list(parse_subrecords(raw[pos + 20: pos + 20 + size]))
            actual = [value[:-1].decode("utf-8") for field, value, _ in parts
                      if field in (b"MNAM", b"FNAM")]
            rows_for_fid = by_form[fid]
            expected = [next(r["obcjk_unicode_text"] for r in rows_for_fid
                             if r["field"] == field and int(r["occurrence"]) == rank)
                        for rank in sorted({int(r["occurrence"]) for r in rows_for_fid})
                        for field in ("MNAM", "FNAM")]
            self.assertEqual(len(actual), 2 * nranks)
            self.assertEqual(actual, expected)
            pos += size + 20
        self.assertEqual(pos, len(raw))


if __name__ == "__main__":
    unittest.main()
