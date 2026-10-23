import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_gate_messages as gates
from build_vanilla_overlay import encode_subrecord, parse_subrecords


class GateMessageTests(unittest.TestCase):
    def fixture(self, texts):
        compiled = b'\x16\x00\x01\x00' + b''.join(
            struct.pack('<H', len(text)) + text.encode() + b'\x19\x00' for text in texts)
        body = (encode_subrecord(b'EDID', b'GateFixture\0') +
                encode_subrecord(b'SCHR', struct.pack('<IIIII', 0, 6, len(compiled), 1, 0)) +
                encode_subrecord(b'SCDA', compiled) +
                encode_subrecord(b'SCTX', '\r\n'.join('Message "'+t+'"' for t in texts).encode()) +
                encode_subrecord(b'SCRO', struct.pack('<I', 0x58)))
        return body, hashlib.sha256(body).hexdigest()

    def test_messages_fit_and_only_literals_change(self):
        for texts in ([next(iter(gates.TRANSLATIONS))], list(gates.TRANSLATIONS)[1:]):
            body, pin = self.fixture(texts)
            result, changes = gates.translate_body(body, 'GateFixture', pin)
            self.assertEqual(len(changes), 2*len(texts))
            reverse = bytearray(result)
            for c in changes:
                at = c['body_offset']
                self.assertEqual(result[at:at+c['bytes']].decode().rstrip(), c['korean'])
                if c['field'] == 'SCDA':
                    self.assertEqual(struct.unpack_from('<H', result, at-2)[0], c['bytes'])
                reverse[at:at+c['bytes']] = c['english'].encode()
            self.assertEqual(reverse, body)
            for (field, _, old), (_, _, new) in zip(parse_subrecords(body), parse_subrecords(result)):
                if field not in (b'SCDA', b'SCTX'):
                    self.assertEqual(old, new)

    def test_changed_identity_source_and_lengths_reject(self):
        body, pin = self.fixture([next(iter(gates.TRANSLATIONS))])
        with self.assertRaisesRegex(ValueError, 'verified original'):
            gates.translate_body(body+b'\0', 'GateFixture', pin)
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            gates.translate_body(body, 'WrongGate', pin)
        en = next(iter(gates.TRANSLATIONS)).encode()
        broken = body.replace(struct.pack('<H',len(en))+en, b'\xff\x00'+en, 1)
        with self.assertRaisesRegex(ValueError, 'Compiled string length'):
            gates.translate_body(broken, 'GateFixture', hashlib.sha256(broken).hexdigest())

    def test_base_gate_writer_requires_both_exact_scripts(self):
        body,pin=self.fixture([next(iter(gates.TRANSLATIONS))])
        pins={('Oblivion.esm',fid):('GateFixture',pin) for fid in (0x4CAEE,0x947B3)}
        raw=b''.join(struct.pack('<4sIIII',b'SCPT',len(body),0,fid,7)+body for _,fid in pins)
        with tempfile.TemporaryDirectory() as temp, patch.object(gates,'PINS',pins):
            source,output=Path(temp)/'Oblivion.esm',Path(temp)/'output.esm'
            source.write_bytes(raw)
            report=gates.build(source,output)
            self.assertEqual(report['script_count'],2)
            self.assertEqual(report['display_strings'],2)
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(len(output.read_bytes()),len(raw))

    def test_writer_preserves_all_other_bytes_and_rejects_missing_duplicate(self):
        body, pin = self.fixture(list(gates.TRANSLATIONS)[1:])
        def record(fid):
            return struct.pack('<4sIIII',b'SCPT',len(body),0,fid,7)+body
        unrelated = struct.pack('<4sIIII',b'BOOK',0,0,55,9)
        raw = b''.join(record(fid) for fid in range(1,4))+unrelated
        pins = {('fixture.esp',fid):('GateFixture',pin) for fid in range(1,4)}
        with tempfile.TemporaryDirectory() as temp, patch.object(gates,'PINS',pins):
            source,output = Path(temp)/'fixture.esp',Path(temp)/'out.esp'
            source.write_bytes(raw)
            report=gates.build(source,output)
            self.assertEqual(report['script_count'],3)
            self.assertEqual(report['display_strings'],9)
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(output.stat().st_size,len(raw))
            self.assertTrue(output.read_bytes().endswith(unrelated))
            source.write_bytes(record(1))
            with self.assertRaisesRegex(ValueError,'Missing'):
                gates.build(source,Path(temp)/'missing.esp')
            source.write_bytes(raw+record(1))
            with self.assertRaisesRegex(ValueError,'Duplicate'):
                gates.build(source,Path(temp)/'duplicate.esp')
