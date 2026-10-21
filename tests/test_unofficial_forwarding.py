import hashlib
import json
from dataclasses import replace
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_unofficial_release as unofficial
from build_unofficial_release import collect_changes, has_localizable_text, read_records, reviewed_identity, rewrite
from build_vanilla_overlay import Translation, encode_subrecord, load_translations, structure_signature


def record(kind, formid, fields):
    body = b''.join(encode_subrecord(field, value) for field, value in fields)
    return struct.pack('<4sIIII', kind, len(body), 0, formid, 0) + body


class UnofficialForwardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / 'DLCFrostcrag - Unofficial Patch.esp'
        self.prior = self.root / 'prior.esp'
        self.owner = 'DLCFrostcrag.esp'
        self.key = (b'QUST', 0x02001234)
        self.fields = [(b'EDID', b'TestQuest\0'), (b'INDX', b'\x0a\x00'),
                       (b'CNAM', b'Source\0'), (b'CNAM', b'Source\0')]
        self.header = record(b'TES4', 0, [(b'MAST', b'Oblivion.esm\0'),
                                        (b'MAST', b'OtherMaster.esm\0'),
                                        (b'MAST', b'DLCFrostcrag.esp\0')])
        self.write()

    def write(self, rawid=0x02001234):
        self.original.write_bytes(self.header + record(b'QUST', rawid, self.fields))
        self.prior.write_bytes(self.original.read_bytes())

    def table(self, targets=(b'Reviewed\0',), source=None):
        return {(self.owner, b'QUST', 0x01001234, b'CNAM'): [
            Translation(source or self.owner, b'QUST', 0x01001234, b'CNAM',
                        'Source', value, index + 2, b'TestQuest', index)
            for index, value in enumerate(targets)]}

    def audit(self):
        return {(self.owner, 'QUST', '01001234', 'CNAM', hashlib.sha256(b'Source\0').hexdigest())}

    def test_missing_kr_reference_is_safe_only_without_visible_text(self):
        metadata_only = self.root / 'metadata-only.esp'
        metadata_only.write_bytes(
            record(b'TES4', 0, [(b'CNAM', b'Author\0')]) +
            record(b'GMST', 0x02000CE6, [(b'DATA', b'\0\0\0')])
        )
        self.assertFalse(has_localizable_text(metadata_only))
        visible = self.root / 'visible.esp'
        visible.write_bytes(
            record(b'TES4', 0, [(b'CNAM', b'Author\0')]) +
            record(b'QUST', 0x02000001, [(b'CNAM', b'Visible quest text\0')])
        )
        self.assertTrue(has_localizable_text(visible))

    def test_canonical_patch_table_rebuilds_without_prior_kr(self):
        patch = {(self.original.name, b'QUST', self.key[1], b'CNAM'): [
            Translation(self.original.name, b'QUST', self.key[1], b'CNAM',
                        'Source', b'Patch canonical\0', 1, b'TestQuest', 0)
        ]}
        changes, counts = collect_changes(self.original, None, patch_table=patch)
        self.assertEqual(changes[self.key][2][2], b'Patch canonical\0')
        self.assertEqual(counts['canonical_patch_translation'], 1)

    def test_official_canonical_outranks_patch_canonical(self):
        patch = {(self.original.name, b'QUST', self.key[1], b'CNAM'): [
            Translation(self.original.name, b'QUST', self.key[1], b'CNAM',
                        'Source', b'Patch canonical\0', 1, b'TestQuest', 0)
        ]}
        changes, _ = collect_changes(self.original, None, self.audit(), self.table(), patch_table=patch)
        self.assertEqual(changes[self.key][2][2], b'Reviewed\0')

    def test_master_slot_maps_to_source_identity(self):
        records = read_records(self.original)
        self.assertEqual(reviewed_identity(records, 0x02001234), (self.owner, 0x01001234))
        self.assertEqual(reviewed_identity(records, 0x00001234), ('Oblivion.esm', 0x00001234))
        self.assertIsNone(reviewed_identity(records, 0x03001234))

    def test_normalized_audit_forwards_each_occurrence(self):
        changes, counts = collect_changes(self.original, self.prior, self.audit(),
                                         self.table((b'First\0', b'Second\0')))
        self.assertEqual(changes[self.key][2][2], b'First\0')
        self.assertEqual(changes[self.key][3][2], b'Second\0')
        self.assertEqual(counts['reviewed_base_translation'], 2)

    def test_patch_owned_id_does_not_receive_master_translation(self):
        self.write(0x03001234)
        changes, _ = collect_changes(self.original, self.prior, self.audit(), self.table())
        self.assertEqual(changes, {})

    def test_reviewed_translation_beats_old_completion(self):
        completion = {(self.original.name, b'QUST', self.key[1], b'CNAM'):
                      (b'Source\0', b'Old bilingual\0')}
        nexus = {(self.original.name, b'QUST', self.key[1], b'CNAM', 0, 10):
                 (b'Source\0', b'Old nexus\0')}
        changes, _ = collect_changes(self.original, self.prior, self.audit(), self.table(),
                                     completions=completion, nexus_completions=nexus)
        self.assertEqual(changes[self.key][2][2], b'Reviewed\0')

    def test_final_review_beats_reviewed_base_and_completions(self):
        changes, _ = collect_changes(self.original, self.prior, self.audit(), self.table(),
                                     self.table((b'Final\0',)))
        self.assertEqual(changes[self.key][2][2], b'Final\0')

    def test_wrong_english_or_editor_cannot_forward(self):
        table = self.table()
        key = next(iter(table))
        table[key][0] = replace(table[key][0], english='Other text')
        changes, _ = collect_changes(self.original, self.prior, self.audit(), table)
        self.assertEqual(changes, {})
        table = self.table()
        table[key][0] = replace(table[key][0], editor_id=b'OtherQuest')
        changes, _ = collect_changes(self.original, self.prior, self.audit(), table)
        self.assertEqual(changes, {})

    def test_latest_direct_source_refinement_matches_main_builder(self):
        table = self.table()
        table[next(iter(table))].append(Translation(self.owner, b'QUST', 0x01001234, b'CNAM',
                                                   'Source', b'Latest\0', 99, b'TestQuest', 0))
        changes, _ = collect_changes(self.original, self.prior, self.audit(), table)
        self.assertEqual(changes[self.key][2][2], b'Latest\0')

    def test_obcjk_direct_patch_location_is_forwarded(self):
        original = self.root / 'Unofficial Oblivion Patch.esp'
        header = record(b'TES4', 0, [(b'MAST', b'Oblivion.esm\0')])
        original.write_bytes(header + record(b'CELL', 0x00001234,
                                             [(b'EDID', b'TestCell\0'), (b'FULL', b'Patch Place\0')]))
        location_table = {(original.name, b'CELL', 0x00001234, b'FULL'): [
            Translation(original.name, b'CELL', 0x00001234, b'FULL',
                        'Patch Place', '패치 장소'.encode('utf-8') + b'\0', 1, b'TestCell', 0)
        ]}
        changes, counts = collect_changes(original, None, location_table=location_table)
        self.assertEqual(changes[(b'CELL', 0x00001234)][1][2],
                         '패치 장소'.encode('utf-8') + b'\0')
        self.assertEqual(counts['canonical_direct_location'], 1)

    def test_obcjk_official_location_normalizes_master_slot(self):
        original = self.root / 'Knights - Unofficial Patch.esp'
        header = record(b'TES4', 0, [(b'MAST', b'Oblivion.esm\0'),
                                     (b'MAST', b'OtherMaster.esm\0'),
                                     (b'MAST', b'Knights.esp\0')])
        original.write_bytes(header + record(b'CELL', 0x020024BE,
                                             [(b'EDID', b'NDVanua01\0'), (b'FULL', b'The Lost Catacombs\0')]))
        location_table = {('Knights.esp', b'CELL', 0x010024BE, b'FULL'): [
            Translation('Knights.esp', b'CELL', 0x010024BE, b'FULL',
                        'The Lost Catacombs', '잃어버린 지하 묘지'.encode('utf-8') + b'\0',
                        1, b'NDVanua01', 0)
        ]}
        changes, counts = collect_changes(original, None, location_table=location_table)
        self.assertEqual(changes[(b'CELL', 0x020024BE)][1][2],
                         '잃어버린 지하 묘지'.encode('utf-8') + b'\0')
        self.assertEqual(counts['canonical_base_location'], 1)

    def arena_fixture(self, *, rank=b'Brawler', editor=b'ArenaCombatants',
                      formid=0x000299B9, masters=(b'Oblivion.esm',),
                      rank_occurrence=1):
        original = self.root / 'Synthetic Unofficial Patch.esp'
        header = record(b'TES4', 0, [(b'MAST', master + b'\0') for master in masters])
        fields = [(b'EDID', editor + b'\0'), (b'FULL', b'Arena\0')]
        for occurrence in range(rank_occurrence + 1):
            # Deliberately use a noncanonical filler so the test isolates the
            # one rank being exercised, instead of translating Pit Dog too.
            name = rank if occurrence == rank_occurrence else b'UnlistedRank'
            fields += [(b'RNAM', struct.pack('<I', occurrence)),
                       (b'MNAM', name + b'\0'), (b'FNAM', name + b'\0')]
        fields += [(b'DATA', b'\x01\x02\x03\x04')]
        original.write_bytes(header + record(b'FACT', formid, fields))
        return original

    @staticmethod
    def arena_audit(source=b'Brawler\0', *, formid='000299B9'):
        return {('Oblivion.esm', 'FACT', formid, field,
                 hashlib.sha256(source).hexdigest())
                for field in ('MNAM', 'FNAM')}

    @staticmethod
    def canonical_rank_table():
        root = Path(__file__).resolve().parents[1]
        return load_translations(
            root / 'canonical_translation_v2.csv',
            extra_paths=(root / 'canonical_ui_supplement_v1.csv',),
            encoded_column='obcjk_utf8_hex')

    @staticmethod
    def supplement_rank_table():
        root = Path(__file__).resolve().parents[1]
        return load_translations(
            root / 'canonical_ui_supplement_v1.csv',
            encoded_column='obcjk_utf8_hex')

    def test_fact_rank_forwarding_is_audited_and_structure_safe(self):
        original = self.arena_fixture()
        table = self.canonical_rank_table()
        changes, counts = collect_changes(original, None, self.arena_audit(), table)
        key = (b'FACT', 0x000299B9)
        self.assertEqual(set(changes), {key})
        self.assertEqual(counts['translated_fields'], 2)
        self.assertEqual(counts['reviewed_base_translation'], 2)
        self.assertEqual([entry[0] for entry in changes[key].values()], [b'MNAM', b'FNAM'])
        rank = '싸움꾼'.encode('utf-8') + b'\0'
        self.assertEqual([entry[2] for entry in changes[key].values()], [rank, rank])
        output = self.root / 'forwarded.esp'
        self.assertEqual(rewrite(original, output, changes), 2)
        self.assertEqual(structure_signature(original), structure_signature(output))
        original_fields = read_records(original)[key]
        result_fields = read_records(output)[key]
        self.assertEqual([f for f, _ in original_fields], [f for f, _ in result_fields])
        for index, ((field, before), (_, after)) in enumerate(zip(original_fields, result_fields)):
            if index in changes[key]:
                self.assertEqual(after, rank)
            else:
                self.assertEqual(after, before)
        self.assertEqual(original_fields[-1], (b'DATA', b'\x01\x02\x03\x04'))

    def test_fact_rank_rejects_source_editor_occurrence_and_owner_mismatch(self):
        table = self.canonical_rank_table()
        supplement = self.supplement_rank_table()
        examples = (
            ('wrong English even with matching audit hash',
             dict(rank=b'Brawlers'), self.arena_audit(b'Brawlers\0')),
            ('wrong editor ID',
             dict(editor=b'ArenaElsewhere'), self.arena_audit()),
            ('wrong rank occurrence',
             dict(rank_occurrence=2), self.arena_audit()),
            ('wrong form ID',
             dict(formid=0x000299BA), self.arena_audit(formid='000299BA')),
            ('foreign master owner',
             dict(masters=(b'OtherMaster.esm', b'Oblivion.esm')), self.arena_audit()),
            ('patch-owned form ID',
             dict(formid=0x010299B9), self.arena_audit()),
        )
        for name, options, audit in examples:
            with self.subTest(name=name):
                original = self.arena_fixture(**options)
                changes, counts = collect_changes(original, None, audit, table)
                self.assertEqual(changes, {})
                self.assertEqual(counts['reviewed_base_translation'], 0)
                # Missing historical audit entries must not weaken strict
                # source, master owner, editor and occurrence checks.
                changes, counts = collect_changes(
                    original, None, set(), table, rank_table=supplement)
                self.assertEqual(changes, {})
                self.assertEqual(counts['supplement_fact_rank_translation'], 0)

        # The audit alone is insufficient: reject missing editor or occurrence
        # constraints, and any row whose source is not the owning master.
        original = self.arena_fixture()
        rank_key = ('Oblivion.esm', b'FACT', 0x000299B9, b'MNAM')
        for edits in (dict(editor_id=None), dict(occurrence=None),
                      dict(source='OtherMaster.esm')):
            with self.subTest(edits=edits):
                altered = dict(table)
                altered[rank_key] = [replace(row, **edits) if row.occurrence == 1 else row
                                     for row in table[rank_key]]
                # FNAM still meets every gate, but MNAM must be rejected.
                changes, _ = collect_changes(original, None, self.arena_audit(), altered)
                fields = [entry[0] for entry in changes[(b'FACT', 0x000299B9)].values()]
                self.assertEqual(fields, [b'FNAM'])

    def test_missing_historical_audit_rank_entries_use_only_reviewed_supplement(self):
        table = self.canonical_rank_table()
        supplement = self.supplement_rank_table()
        for ordinal, english, korean in (
            (1, b'Brawler', '싸움꾼'),
            (4, b'Warrior', '전사'),
            (7, b'Champion', '챔피언'),
            (8, b'Grand Champion', '그랜드 챔피언'),
        ):
            with self.subTest(rank=english):
                original = self.arena_fixture(rank=english, rank_occurrence=ordinal)
                no_fallback, _ = collect_changes(original, None, set(), table)
                self.assertEqual(no_fallback, {})
                changes, counts = collect_changes(
                    original, None, set(), table, rank_table=supplement)
                key = (b'FACT', 0x000299B9)
                self.assertEqual(set(changes), {key})
                self.assertEqual([value[2] for value in changes[key].values()],
                                 [korean.encode('utf-8') + b'\0'] * 2)
                self.assertEqual(counts['supplement_fact_rank_translation'], 2)
                output = self.root / 'missing-audit-output.esp'
                self.assertEqual(rewrite(original, output, changes), 2)
                self.assertEqual(structure_signature(original), structure_signature(output))

    def test_non_fact_mnam_fnam_cannot_forward_even_if_audited(self):
        original = self.root / 'Nonfact Unofficial Patch.esp'
        original.write_bytes(
            record(b'TES4', 0, [(b'MAST', b'Oblivion.esm\0')]) +
            record(b'SKIL', 0x000299B9,
                   [(b'EDID', b'ArenaCombatants\0'),
                    (b'MNAM', b'Brawler\0'), (b'FNAM', b'Brawler\0')]))
        table = {('Oblivion.esm', b'SKIL', 0x000299B9, field): [
            Translation('Oblivion.esm', b'SKIL', 0x000299B9, field,
                        'Brawler', b'Not Allowed\0', 1, b'ArenaCombatants', 0)]
            for field in (b'MNAM', b'FNAM')}
        audit = {('Oblivion.esm', 'SKIL', '000299B9', field,
                  hashlib.sha256(b'Brawler\0').hexdigest())
                 for field in ('MNAM', 'FNAM')}
        changes, _ = collect_changes(original, None, audit, table)
        self.assertEqual(changes, {})
        self.assertFalse(has_localizable_text(original))
        self.assertTrue(has_localizable_text(self.arena_fixture()))

    def test_main_uses_supplement_to_forward_real_rank_rows(self):
        source_root = self.root / 'originals'
        source_dir = source_root / 'UOP'
        source_dir.mkdir(parents=True)
        original = self.arena_fixture()
        original.replace(source_dir / original.name)
        output_root = self.root / 'output'
        audit_path = self.root / 'vanilla_audit.json'
        audit_path.write_text(
            json.dumps({'applied': []}), encoding='utf-8')
        args = ['build_unofficial_release.py', '--source', str(source_root),
                '--output', str(output_root), '--vanilla-audit', str(audit_path)]
        with patch.object(sys, 'argv', args), \
                patch.object(unofficial, 'PAIRS', (('UOP', 'Synthetic-KR'),)), \
                patch.object(unofficial, 'load_patch_canonical', return_value={}), \
                patch.object(unofficial, 'load_restorations', return_value={}):
            unofficial.main()
        destination = output_root / 'Synthetic-KR' / original.name
        self.assertTrue(destination.is_file())
        self.assertEqual(structure_signature(source_dir / original.name),
                         structure_signature(destination))
        self.assertEqual(
            [(field, value) for field, value in read_records(destination)[(b'FACT', 0x000299B9)]
             if field in (b'MNAM', b'FNAM')],
            [(b'MNAM', b'UnlistedRank\0'), (b'FNAM', b'UnlistedRank\0'),
             (b'MNAM', '싸움꾼'.encode('utf-8') + b'\0'),
             (b'FNAM', '싸움꾼'.encode('utf-8') + b'\0')])
        report = json.loads((output_root / 'release_audit.json').read_text(encoding='utf-8'))
        self.assertEqual(report[original.name]['reviewed_base_translation'], 2)
        self.assertEqual(report[original.name]['supplement_fact_rank_translation'], 2)


if __name__ == '__main__':
    unittest.main()
