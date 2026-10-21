import csv
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from build_obcjk_locations import build
from build_obcjk_overlay import records
from build_vanilla_overlay import encode_subrecord


class LocationOverlayTests(unittest.TestCase):
    def test_mages_guild_cell_overrides_match_exact_original_names(self):
        """The original base ESM uses different FULL text from its DLC/UOP overrides."""
        reviewed = {
            0x0002E545: ("CheydinhalMagesGuild", "Mages' Guild", "셰이딘홀 메이지 길드"),
            0x00030534: ("LeyawiinMagesGuild", "Leyawiin Mages' Guild", "레이야윈 메이지 길드"),
        }
        canonical = Path(__file__).resolve().parents[1] / "canonical_locations_v2.csv"
        with canonical.open(encoding="utf-8-sig", newline="") as stream:
            rows = [row for row in csv.DictReader(stream)
                    if row["effective_source"] == "Oblivion.esm"
                    and row["record_type"] == "CELL"
                    and row["raw_formid"] in {f"{fid:08X}" for fid in reviewed}]
        self.assertEqual(len(rows), len(reviewed))
        for row in rows:
            fid = int(row["raw_formid"], 16)
            editor, english, korean = reviewed[fid]
            self.assertEqual((row["field"], row["editor_id"], row["old_english"]),
                             ("FULL", editor, english))
            self.assertEqual((row["obcjk_unicode_text"], row["obcjk_conversion_status"]),
                             (korean, "verified"))
            self.assertEqual(bytes.fromhex(row["obcjk_utf8_hex"]),
                             korean.encode("utf-8") + b"\0")

        # The third original ASCII cell uses a Test* EditorID; preserve it.
        cases = {**reviewed, 0x0005D36A: ("TestParadiseCave", "Paradise Cave", "Paradise Cave")}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, tables, output = root / "source", root / "tables", root / "output"
            source.mkdir()
            tables.mkdir()
            shutil.copyfile(canonical, tables / "canonical_locations_v2.csv")
            chunks = []
            for fid, (editor, english, korean) in cases.items():
                body = (encode_subrecord(b"EDID", editor.encode("ascii") + b"\0")
                        + encode_subrecord(b"FULL", english.encode("cp1252") + b"\0")
                        + encode_subrecord(b"DATA", b"\x21"))
                chunks.append(struct.pack("<4sIIII", b"CELL", len(body), 0, fid, 0) + body)
            (source / "Oblivion.esm").write_bytes(b"".join(chunks))
            report = build([source], tables, output)["Oblivion.esm"]
            self.assertEqual(report["location_counts"], {"CELL": 2})
            self.assertEqual({row["formid"] for row in report["changes"]},
                             {f"{fid:08X}" for fid in reviewed})
            self.assertTrue(all(row["match_kind"] == "record_and_source"
                                for row in report["changes"]))
            self.assertEqual(report["unmatched"], [])
            actual = {fid: parts for (kind, fid), _, parts, _ in records(output / "Oblivion.esm")}
            for fid, (editor, english, korean) in cases.items():
                self.assertEqual(actual[fid][0][1], editor.encode("ascii") + b"\0")
                self.assertEqual(actual[fid][1][1], korean.encode("utf-8") + b"\0")
                self.assertEqual(actual[fid][2][1], b"\x21")

    def test_marker_names_and_region_names_preserve_nonmarker_and_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, tables, output = root/'source', root/'tables', root/'output'
            source.mkdir(); tables.mkdir()
            chunks = []
            for kind, fid, field, marker in [(b'REFR', 1, b'FULL', True), (b'REFR', 2, b'FULL', False), (b'REGN', 3, b'RDMP', False)]:
                body = encode_subrecord(field, b'Matched Hall\0')
                if marker:
                    body += encode_subrecord(b'XMRK', b'')
                body += encode_subrecord(b'DATA', b'\x01\x00\xff')
                chunks.append(struct.pack('<4sIIII', kind, len(body), 0, fid, 9)+body)
            (source/'Oblivion.esm').write_bytes(b''.join(chunks))
            fields = ['effective_source', 'record_type', 'raw_formid', 'field', 'old_english', 'obcjk_conversion_status', 'obcjk_unicode_text', 'obcjk_utf8_hex']
            with (tables/'memory.csv').open('w', encoding='utf-8', newline='') as stream:
                writer = csv.writer(stream); writer.writerow(fields)
                writer.writerow(['Oblivion.esm','CELL','00000009','FULL','Matched Hall','verified','일치하는 전당',('일치하는 전당'.encode()+b'\0').hex()])
            # Release table folders can also contain unrelated CSV schemas
            # such as the injected menu GMST table; those are not locations.
            with (tables/'menu.csv').open('w', encoding='utf-8', newline='') as stream:
                writer = csv.writer(stream); writer.writerow(['formid','edid','english','korean'])
                writer.writerow(['00000010','sExample','Example','예시'])
            report = build([source], tables, output)['Oblivion.esm']
            self.assertEqual(report['location_counts'], {'REFR':1,'REGN':1})
            actual = {key:parts for key,_,parts,_ in records(output/'Oblivion.esm')}
            self.assertEqual(actual[(b'REFR',1)][0][1], '일치하는 전당'.encode()+b'\0')
            self.assertEqual(actual[(b'REFR',2)][0][1], b'Matched Hall\0')
            self.assertEqual(actual[(b'REGN',3)][0][1], '일치하는 전당'.encode()+b'\0')
            self.assertTrue(all(parts[-1][1] == b'\x01\x00\xff' for parts in actual.values()))

    def test_exact_source_matching_ambiguity_and_binary_preservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, tables, output = root / 'source', root / 'tables', root / 'output'
            source.mkdir()
            tables.mkdir()
            chunks = []
            for fid, name in [(1, 'Matched Hall'), (2, 'Changed by upstream'), (3, 'Ambiguous Hall')]:
                body = (encode_subrecord(b'EDID', f'Cell{fid}'.encode() + b'\0') +
                        encode_subrecord(b'FULL', name.encode() + b'\0') +
                        encode_subrecord(b'DATA', b'\x01\x00\xff'))
                chunks.append(struct.pack('<4sIIII', b'CELL', len(body), 0, fid, 9) + body)
            (source / 'Oblivion.esm').write_bytes(b''.join(chunks))
            fields = ['effective_source', 'record_type', 'raw_formid', 'field', 'old_english',
                      'obcjk_conversion_status', 'obcjk_unicode_text', 'obcjk_utf8_hex']
            with (tables / 'memory.csv').open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fields)
                writer.writeheader()
                for fid, english, korean in [(1, 'Matched Hall', '일치하는 전당'),
                                             (2, 'Old name', '옛 이름'),
                                             (3, 'Ambiguous Hall', '전당'),
                                             (3, 'Ambiguous Hall', '홀')]:
                    writer.writerow(dict(zip(fields, ['Oblivion.esm', 'CELL', f'{fid:08X}', 'FULL',
                                                       english, 'verified', korean,
                                                       (korean.encode('utf-8') + b'\0').hex()])))
            report = build([source], tables, output)['Oblivion.esm']
            self.assertEqual(report['location_counts'], {'CELL': 1})
            self.assertEqual(len(report['unmatched']), 2)
            fields_by_id = {key[1]: parts for key, header, parts, groups in records(output / 'Oblivion.esm')}
            self.assertEqual(fields_by_id[1][1][1], '일치하는 전당'.encode('utf-8') + b'\0')
            self.assertEqual(fields_by_id[2][1][1], b'Changed by upstream\0')
            self.assertEqual(fields_by_id[3][1][1], b'Ambiguous Hall\0')
            self.assertTrue(all(parts[2][1] == b'\x01\x00\xff' for parts in fields_by_id.values()))


if __name__ == '__main__':
    unittest.main()
