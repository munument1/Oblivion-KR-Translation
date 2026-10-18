import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_shrine_messages as shrines
from build_vanilla_overlay import encode_subrecord, parse_subrecords


class ShrineMessageTests(unittest.TestCase):
    def fixture(self, knights=False, unofficial=False):
        en = list(shrines.TRANSLATIONS)
        texts = [en[0], en[1], en[2], en[3], en[4]] if knights else [en[1], en[-1], en[3]]
        if unofficial:
            texts = [en[0], en[1], en[3], en[4], en[2], en[1], en[3], en[-1]]
        scda = b'\x16\x00\x01\x00' + b''.join(
            struct.pack('<H', len(text)) + text.encode() + b'\x19\x00' for text in texts)
        body = (encode_subrecord(b'EDID', b'ShrineFixture\0') +
                encode_subrecord(b'SCHR', struct.pack('<IIIII', 0, 6, len(scda), 1, 0)) +
                encode_subrecord(b'SCDA', scda) +
                encode_subrecord(b'SCTX', ('\r\n'.join('MessageBox "' + t + '"' for t in texts)).encode()) +
                encode_subrecord(b'SCRO', struct.pack('<I', 0x58)))
        return body, hashlib.sha256(body).hexdigest()

    def test_every_translation_fits_original_utf8_budget(self):
        self.assertEqual(len(shrines.TRANSLATIONS), 14)
        for en, ko in shrines.TRANSLATIONS.items():
            self.assertLessEqual(len(ko.encode('utf-8')), len(en))
        self.assertEqual(len(shrines.PINS), 27)

    def test_base_and_knights_preserve_all_nonliteral_bytes(self):
        for knights in (False, True):
            body, pin = self.fixture(knights)
            result, changes = shrines.translate_body(body, 'ShrineFixture', pin)
            self.assertEqual(len(changes), 10 if knights else 6)
            restored = bytearray(result)
            for c in changes:
                at = c['body_offset']
                restored[at:at+c['bytes']] = c['english'].encode()
                self.assertEqual(result[at:at+c['bytes']].decode('utf-8').rstrip(), c['korean'])
                if c['field'] == 'SCDA':
                    self.assertEqual(struct.unpack_from('<H', result, at-2)[0], c['bytes'])
            self.assertEqual(restored, body)
            for (field, _, old), (_, _, new) in zip(parse_subrecords(body), parse_subrecords(result)):
                if field not in (b'SCDA', b'SCTX'):
                    self.assertEqual(old, new)

    def test_source_identity_and_compiled_length_fail_closed(self):
        body, pin = self.fixture()
        with self.assertRaisesRegex(ValueError, 'verified original'):
            shrines.translate_body(body + b'\0', 'ShrineFixture', pin)
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            shrines.translate_body(body, 'Other', pin)
        english = list(shrines.TRANSLATIONS)[1].encode()
        broken = body.replace(struct.pack('<H', len(english)) + english, b'\xff\x00' + english, 1)
        with self.assertRaisesRegex(ValueError, 'Compiled string length'):
            shrines.translate_body(broken, 'ShrineFixture', hashlib.sha256(broken).hexdigest())

    def test_unofficial_repeated_messages_are_all_translated(self):
        body, pin = self.fixture(unofficial=True)
        result, changes = shrines.translate_body(body, 'ShrineFixture', pin)
        self.assertEqual(len(changes), 16)
        english = list(shrines.TRANSLATIONS)[1]
        korean = shrines.TRANSLATIONS[english].encode('utf-8')
        fields = {k: v for k, v, _ in parse_subrecords(result)}
        for key in (b'SCDA', b'SCTX'):
            self.assertNotIn(english.encode(), fields[key])
            self.assertEqual(fields[key].count(korean), 2)

    def test_writer_requires_all_nine_and_preserves_other_records(self):
        body, pin = self.fixture()
        pins = {('fixture.esm', fid): ('ShrineFixture', pin) for fid in range(1, 10)}
        def record(fid):
            return struct.pack('<4sIIII', b'SCPT', len(body), 0, fid, 7) + body
        records = b''.join(record(fid) for fid in range(1, 10))
        unrelated = struct.pack('<4sIIII', b'BOOK', 0, 0, 55, 9)
        raw = struct.pack('<4sI4sII', b'GRUP', 20 + len(records), b'SCPT', 0, 0) + records + unrelated
        with tempfile.TemporaryDirectory() as temp, patch.object(shrines, 'PINS', pins):
            source, target = Path(temp)/'fixture.esm', Path(temp)/'output.esm'
            source.write_bytes(raw)
            report = shrines.build(source, target)
            self.assertEqual(report['script_count'], 9)
            self.assertEqual(report['display_strings'], 27)
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(target.stat().st_size, len(raw))
            self.assertTrue(target.read_bytes().endswith(unrelated))
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), report['output_sha256'])
            with self.assertRaisesRegex(ValueError, 'new and separate'):
                shrines.build(source, target)
            source.write_bytes(record(1))
            with self.assertRaisesRegex(ValueError, 'Missing wayshrine'):
                shrines.build(source, Path(temp)/'missing.esm')
            source.write_bytes(raw + record(1))
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                shrines.build(source, Path(temp)/'duplicate.esm')


if __name__ == '__main__':
    unittest.main()
