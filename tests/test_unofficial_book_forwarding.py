import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from build_unofficial_release import collect_changes, read_records, rewrite
from build_vanilla_overlay import structure_signature
from unofficial_book_forwarding import forward_book, load_book_forwarding
from unofficial_text_forwarding import load_text_forwarding
from test_unofficial_forwarding import record

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'Unofficial Oblivion Patch.esp'


class BookForwardingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_book_forwarding(ROOT)
        cls.builder_table = load_text_forwarding(ROOT)

    def test_all_manifest_sources_and_canonical_targets_are_valid(self):
        self.assertEqual(len(self.table), 542)
        self.assertEqual(sum(v[-1] == 'forward' for v in self.table.values()), 506)

    def test_changed_english_book_forwards_without_vanilla_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / PLUGIN
            rows = list(csv.DictReader((ROOT / 'canonical_unofficial_translation_v2.csv').open(
                encoding='utf-8-sig', newline='')))
            row = next(r for r in rows if r['effective_source'] == PLUGIN
                       and r['raw_formid'] == '00024564' and r['field'] == 'DESC')
            raw = row['old_english'].encode('cp1252') + b'\0'
            source.write_bytes(record(b'TES4', 0, [(b'MAST', b'Oblivion.esm\0')]) +
                record(b'BOOK', 0x24564, [(b'EDID', row['editor_id'].encode() + b'\0'),
                    (b'DESC', raw), (b'DATA', b'\x01\x02')]))
            changes, counts = collect_changes(source, None, text_forwarding=self.builder_table)
            text = changes[(b'BOOK', 0x24564)][1][2].decode('utf-8')
            for name in ('메이룬스의 면도칼', '알말렉시아', '아주라'):
                self.assertIn(name, text)
            self.assertEqual(counts['canonical_text_forwarded'], 1)
            dest = Path(temp) / 'out.esp'
            self.assertEqual(rewrite(source, dest, changes), 1)
            self.assertEqual(structure_signature(source), structure_signature(dest))
            self.assertEqual(read_records(dest)[(b'BOOK', 0x24564)][2], (b'DATA', b'\x01\x02'))

    def test_identity_source_and_occurrence_are_required(self):
        key = next(k for k, v in self.table.items() if k[1] == 0x24564 and k[2] == b'DESC')
        plugin, fid, field, editor, occurrence = key
        item = self.table[key]
        args = [self.table, plugin, fid, field, editor, occurrence, (item[0], item[1]), b'wrong\0']
        with self.assertRaisesRegex(ValueError, 'Changed patch BOOK source'):
            forward_book(*args)
        for index, value in ((4, b'WrongEditor'), (5, 1), (6, ('Foreign.esm', fid)), (3, b'DATA')):
            bad = list(args); bad[index] = value
            self.assertIsNone(forward_book(*bad))

    def test_intentional_patch_changes_are_preserved(self):
        for fid, field in ((0x8DC83, b'FULL'), (0x72296, b'DESC'), (0x6A7FE, b'DESC')):
            found = [v for k, v in self.table.items() if k[1:3] == (fid, field)]
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0][-1], 'patch')


if __name__ == '__main__':
    unittest.main()
