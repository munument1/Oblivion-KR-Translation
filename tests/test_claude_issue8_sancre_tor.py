"""Claude audit #8: verified Sancre Tor world-map and cell name records."""
import csv
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
LOCATION_TABLE = HERE / "canonical_locations_v2.csv"
EXPECTED = {
    "Oblivion.esm": {
        "00033C05", "00033C06", "00033FD1", "000341F2",
        "0003447B", "00035D91", "00026EBD",
    },
    "Unofficial Oblivion Patch.esp": {
        "00033C05", "00033C06", "00033FD1",
        "000341F2", "0003447B", "00035D91",
    },
}
UNMODIFIED_TEST_IDS = {"00024803", "000921BD"}


class SancreTorLocationsTests(unittest.TestCase):
    def test_real_player_visible_records_and_utf8(self):
        actual = {source: set() for source in EXPECTED}
        preserved_test_ids = set()
        with LOCATION_TABLE.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["effective_source"] == "Oblivion.esm" and row["raw_formid"] in UNMODIFIED_TEST_IDS:
                    self.assertEqual(row["obcjk_unicode_text"], "생커 토르"
                                     if row["raw_formid"] == "00024803"
                                     else "생커 토르, 지하 묘지")
                    preserved_test_ids.add(row["raw_formid"])
                source = row["effective_source"]
                fid = row["raw_formid"]
                if source not in EXPECTED or fid not in EXPECTED[source]:
                    continue
                self.assertNotIn(fid, actual[source])
                actual[source].add(fid)
                self.assertIn(row["record_type"], {"CELL", "REFR"})
                self.assertEqual(row["field"], "FULL")
                self.assertEqual(row["obcjk_conversion_status"], "verified")
                self.assertIn("Sancre Tor", row["old_english"])
                self.assertIn("생크 토르", row["obcjk_unicode_text"])
                self.assertNotIn("생커 토르", row["obcjk_unicode_text"])
                self.assertEqual(bytes.fromhex(row["obcjk_utf8_hex"]),
                                 row["obcjk_unicode_text"].encode("utf-8") + b"\0")
                if row["record_type"] == "REFR":
                    self.assertEqual((source, fid, row["editor_id"]),
                                     ("Oblivion.esm", "00026EBD", "SancreTorMapMarker"))
        self.assertEqual(actual, EXPECTED)
        self.assertEqual(preserved_test_ids, UNMODIFIED_TEST_IDS)


if __name__ == "__main__":
    unittest.main()
