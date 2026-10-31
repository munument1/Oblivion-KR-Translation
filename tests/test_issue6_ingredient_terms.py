"""Issue #6: harvested ingredients use their world flora's Korean name."""

import csv
import unittest
from pathlib import Path

from oblivion_korean_codec import encode_legacy


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    ("INGR", "00084471", "Fly Amanita Cap", "FlyAmanitaCap"):
        "파리 광대독버섯의 갓",
    ("DIAL", "000A78B2", "Fly Amanita", "IngredIFlyAmanita"):
        "파리 광대독버섯",
    ("DIAL", "000A78A2", "Stinkhorn", "IngredIStinkhorn"):
        "말뚝버섯",
}
REFERENCES = {
    ("FLOR", fid, "Fly Amanita"): "파리 광대독버섯"
    for fid in ("0001C718", "0001C765", "0001C77C", "0001C77D")
} | {
    ("FLOR", "000336B2", "Stinkhorn"): "말뚝버섯",
    ("INGR", "0008446D", "Stinkhorn Cap"): "말뚝버섯 머리",
}


class Issue6IngredientTermsTests(unittest.TestCase):
    def test_ingredient_names_match_source_flora_in_both_encodings(self):
        found = set()
        reference_found = set()
        with (ROOT / "canonical_translation_v2.csv").open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["effective_source"] != "Oblivion.esm" or row["field"] != "FULL":
                    continue
                identity = (row["record_type"], row["raw_formid"], row["old_english"])
                scoped = (*identity, row["editor_id"])
                if scoped in EXPECTED:
                    self.assertEqual(row["occurrence"], "0")
                    expected = EXPECTED[scoped]
                    found.add(scoped)
                elif identity in REFERENCES:
                    expected = REFERENCES[identity]
                    reference_found.add(identity)
                else:
                    continue
                self.assertEqual(row["new_korean"], expected)
                self.assertEqual(row["obcjk_unicode_text"], expected)
                self.assertEqual(bytes.fromhex(row["new_bytes_hex"]), encode_legacy(expected) + b"\0")
                self.assertEqual(bytes.fromhex(row["obcjk_utf8_hex"]), expected.encode("utf-8") + b"\0")
        self.assertEqual(found, set(EXPECTED))
        self.assertEqual(reference_found, set(REFERENCES))


if __name__ == "__main__":
    unittest.main()
