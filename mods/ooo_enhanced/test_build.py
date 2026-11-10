import importlib.util
from pathlib import Path
import struct, tempfile, unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ooo_build',HERE/'build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class BuildTests(unittest.TestCase):
    def test_extended_subrecord_roundtrip(self):
        data=b'x'*70000
        packed=build.pack(b'DESC',data)
        self.assertEqual(list(build.fields(packed)),[(b'DESC',data,packed)])

    def test_truncated_subrecord_is_rejected(self):
        with self.assertRaises(ValueError):list(build.fields(b'FULL\x05\x00abc'))

    def test_script_relocates_block_and_preserves_arguments(self):
        literal=b'Hello'
        message=struct.pack('<HHH',0x1000,len(literal)+2,len(literal))+literal
        old=struct.pack('<HHHI',0x10,6,0,len(message))+message
        new,edits=build.replace_strings(old,{'Hello':'안녕하세요'})
        self.assertEqual(len(edits),1)
        build.verify_script(old,new,{'Hello':'안녕하세요'})
        damaged=new[:-1]+b'!'
        with self.assertRaises(AssertionError):build.verify_script(old,damaged,{'Hello':'안녕하세요'})

    def test_wrong_source_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';source.mkdir();output=Path(temp)/'output'
            manifest=__import__('json').loads((HERE/'sources_6.9a.json').read_text(encoding='utf8'))
            for name in manifest['plugins']:
                p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'wrong version')
            with self.assertRaises(AssertionError):build.build(source,output)
            self.assertFalse(output.exists())

if __name__=='__main__':unittest.main()
