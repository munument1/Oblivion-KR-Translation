"""Issue #8 non-mutating, source-anchored audit regression checks."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_issue8_name_chains import analyze_row, build


class NameChainTests(unittest.TestCase):
    def test_conflicting_map_name_is_review_not_auto_edit(self):
        row = dict(effective_source='Oblivion.esm', record_type='WRLD',
                   raw_formid='0001C31C', field='FULL', editor_id='CheydinhalWorld',
                   old_english='Cheydinhal', obcjk_unicode_text='셰이딘홀')
        hits = analyze_row(row, Path('canonical_locations_v2.csv'), 2)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['classification'], 'REFERENCE_CONFLICT_REVIEW')
        self.assertEqual(row['obcjk_unicode_text'], '셰이딘홀')

    def test_word_boundary_and_book_quest_field_routing(self):
        row = dict(record_type='BOOK', field='DESC',
                   old_english='On the Mysterium Xarxes',
                   obcjk_unicode_text='자서스의 신비에 대하여')
        hit = analyze_row(row, Path('canonical_translation_v2.csv'), 12)[0]
        self.assertEqual(hit['surface'], 'BOOK_BODY')
        self.assertEqual(hit['classification'], 'REFERENCE_CONFLICT_REVIEW')
        row.update(old_english='NotMythic Dawnish writing',
                   obcjk_unicode_text='미씩 던')
        self.assertFalse(analyze_row(row, Path('input.csv'), 99))
        row.update(record_type='QUST', field='CNAM',
                   old_english='Knights of the Nine',
                   obcjk_unicode_text='나인 디바인의 기사단')
        self.assertEqual(analyze_row(row, Path('input.csv'), 9)[0]['surface'],
                         'QUEST_JOURNAL')

    def test_report_has_hashes_and_never_edits_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fields = ['effective_source', 'record_type', 'raw_formid', 'field',
                      'old_english', 'obcjk_unicode_text', 'editor_id', 'occurrence']
            trans, loc = root/'translation.csv', root/'location.csv'
            for path, row in [
                (trans, ['Oblivion.esm', 'INFO', '00000001', 'NAM1',
                         'Mythic Dawn', '미씩 던', 'Topic', '0']),
                (loc, ['Oblivion.esm', 'WRLD', '0001C31C', 'FULL',
                       'Cheydinhal', '셰이딘홀', 'CheydinhalWorld', '']),
            ]:
                with path.open('w', encoding='utf-8', newline='') as f:
                    w = csv.writer(f)
                    w.writerow(fields)
                    w.writerow(row)
            original = [p.read_bytes() for p in (trans, loc)]
            summary = build(trans, loc, root/'out')
            self.assertEqual(summary['candidate_rows'], 2)
            self.assertEqual([p.read_bytes() for p in (trans, loc)], original)
            report = json.loads((root/'out/ISSUE8_NAME_CHAIN_SUMMARY.json')
                                .read_text(encoding='utf-8'))
            self.assertEqual(len(report['sources_sha256']), 2)
            with (root/'out/ISSUE8_NAME_CHAIN_CANDIDATES.csv').open(
                    encoding='utf-8-sig') as f:
                self.assertEqual(len(list(csv.DictReader(f))), 2)


if __name__ == '__main__':
    unittest.main()
