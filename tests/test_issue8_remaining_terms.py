"""Issue #8 remaining named-entity audit safety tests."""
import csv
import tempfile
import unittest
from pathlib import Path
from scripts.audit_issue8_remaining_terms import examine, run

class AuditIssue8RemainingTests(unittest.TestCase):
    def test_known_name_variants_are_detected(self):
        row={"old_english":"The Ayleids built this place",
             "obcjk_unicode_text":"아일레이드인들이 지었다",
             "effective_source":"Oblivion.esm","record_type":"INFO",
             "raw_formid":"00001234","field":"NAM1"}
        x=examine(row,2)
        self.assertEqual(len(x),1)
        self.assertEqual(x[0]["term"],"Ayleid")
        self.assertEqual(x[0]["classification"],"alias_candidate")
        self.assertEqual(x[0]["canonical"],"에일리드")

    def test_contextual_gatekeeper_and_tool_chest_are_not_autofixes(self):
        x=examine({"old_english":"Gatekeeper","obcjk_unicode_text":"문지기",
                   "record_type":"CREA","field":"FULL"},2)
        self.assertEqual(x[0]["classification"],"context_required")
        x=examine({"old_english":"Cupboard","obcjk_unicode_text":"찬장",
                   "record_type":"CONT","field":"FULL"},3)
        self.assertEqual(x[0]["classification"],"context_required")

    def test_no_partial_english_word_matches(self):
        x=examine({"old_english":"The dangerous nongatekeeperish species",
                   "obcjk_unicode_text":"문지기"},7)
        self.assertEqual(x,[])

    def test_source_files_are_never_edited(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            header=["effective_source","record_type","raw_formid","field",
                    "old_english","obcjk_unicode_text","occurrence"]
            paths=[p/"canonical_translation_v2.csv",p/"canonical_locations_v2.csv"]
            for path in paths:
                with path.open("w",encoding="utf-8",newline="") as f:
                    writer=csv.writer(f)
                    writer.writerow(header)
                    writer.writerow(["Oblivion.esm","INFO","00000001","NAM1",
                                     "Jauffre is here","조프리가 왔어","0"])
            original=[x.read_bytes() for x in paths]
            summary=run(*paths,p/"reports")
            self.assertEqual(summary["total_term_hits"],2)
            self.assertEqual([x.read_bytes() for x in paths],original)

if __name__=="__main__":
    unittest.main()
