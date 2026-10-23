import csv
import hashlib
from pathlib import Path
import tempfile
import unittest

from build_unofficial_release import collect_changes, rewrite, read_records
from build_vanilla_overlay import structure_signature
from unofficial_text_forwarding import load_text_forwarding, forward_text
from test_unofficial_forwarding import record

ROOT = Path(__file__).resolve().parents[1]


class UnofficialTextAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_text_forwarding(ROOT)
        cls.sources = {}
        for name in ('canonical_unofficial_translation_v2.csv', 'canonical_unofficial_locations_v2.csv',
                     'canonical_locations_v2.csv', 'unofficial_extra_sources_v1.csv'):
            with (ROOT / name).open(encoding='utf-8-sig', newline='') as stream:
                for row in csv.DictReader(stream):
                    key = (row['effective_source'], row['record_type'].encode(), int(row['raw_formid'],16),
                           row['field'].encode(), row['editor_id'].encode(), int(row.get('occurrence') or 0))
                    cls.sources.setdefault(key, row['old_english'].encode('cp1252')+b'\0')

    def test_scope_covers_dialogue_journals_names_descriptions_ranks_and_locations(self):
        self.assertGreater(len(self.table), 9000)
        self.assertTrue({b'INFO', b'QUST', b'NPC_', b'ARMO', b'SPEL', b'RACE', b'CLAS', b'FACT', b'CELL'}
                        <= {key[1] for key in self.table})

    def test_every_forwarded_source_is_hash_pinned_and_owner_scoped(self):
        for key, item in self.table.items():
            raw = self.sources[key]
            expected = item[3] if item[-1] == 'forward' else None
            self.assertEqual(forward_text(self.table, *key, item[:2], raw), expected, key)
            self.assertIsNone(forward_text(self.table, *key, ('Foreign.esm', item[1]), raw), key)
        key = next(k for k,v in self.table.items() if v[-1] == 'forward')
        with self.assertRaisesRegex(ValueError, 'Changed patch text source'):
            forward_text(self.table, *key, self.table[key][:2], b'Unexpected source\0')

    def test_class_description_applies_without_optional_vanilla_audit(self):
        key = ('Unofficial Oblivion Patch.esp', b'CLAS', 0x105D6, b'DESC', b'Mage', 0)
        raw = self.sources[key]
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / key[0]
            source.write_bytes(record(b'TES4',0,[(b'MAST',b'Oblivion.esm\0')]) +
                record(b'CLAS',key[2],[(b'EDID',b'Mage\0'),(b'DESC',raw),(b'DATA',b'\x01\x02')]))
            changes, counts = collect_changes(source,None,text_forwarding=self.table)
            self.assertEqual(changes[(key[1],key[2])][1][2],self.table[key][3])
            self.assertEqual(counts['canonical_text_forwarded'],1)
            dest=Path(temp)/'out.esp'
            rewrite(source,dest,changes)
            self.assertEqual(structure_signature(source),structure_signature(dest))
            self.assertEqual(read_records(dest)[key[1:3]][2],(b'DATA',b'\x01\x02'))

    def test_rank_forwarding_works_without_old_audit_or_rank_memory(self):
        key=('Unofficial Oblivion Patch.esp',b'FACT',0x24164,b'MNAM',b'ThievesGuild',4)
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/key[0]
            fields=[(b'EDID',b'ThievesGuild\0')]+[(b'MNAM',b'Other\0')]*4+[(b'MNAM',b'Cat Burglar\0')]
            source.write_bytes(record(b'TES4',0,[(b'MAST',b'Oblivion.esm\0')])+record(b'FACT',key[2],fields))
            changes,_=collect_changes(source,None,text_forwarding=self.table)
            self.assertEqual(changes[(b'FACT',key[2])][5][2],'빈집털이범'.encode()+b'\0')

    def test_manual_corrections_follow_changed_patch_meaning(self):
        from scripts.release_unofficial_sync import load_manual_fixes
        manual=load_manual_fixes()
        self.assertEqual(len(manual),51)
        key=('Unofficial Oblivion Patch.esp',b'GMST',0xCD591,b'DATA',b'sSpecialization',0)
        self.assertIn(b'+5',manual[key])
        self.assertNotIn(b'+10',manual[key])
        key=('Unofficial Oblivion Patch.esp',b'ACTI',0xCCF6,b'FULL',b'OblivionCitadelGateEuptionSwitch2',0)
        self.assertEqual(manual[key],'분출 관문 제어 장치'.encode()+b'\0')

    def test_frozen_installer_contains_fur_translation_input(self):
        self.assertIn("'canonical_nexus_56688_fur_v1.csv'",(ROOT/'OblivionKRBuilder.spec').read_text())


if __name__ == '__main__':
    unittest.main()
