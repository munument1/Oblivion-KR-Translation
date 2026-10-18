import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from package_obcjk_unofficial import PATCHES, package


class UnofficialPackageTests(unittest.TestCase):
    def test_all_plugins_are_at_root_including_citadel_and_sssb(self):
        for patch in ('UOP', 'USIP', 'UODP'):
            with self.subTest(patch=patch), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                folder = root / 'plugins'
                folder.mkdir()
                audit = {}
                for name in PATCHES[patch]:
                    content = b'synthetic-' + name.encode('ascii')
                    (folder/name).write_bytes(content)
                    audit[name] = dict(source_sha256='source', output_sha256=hashlib.sha256(content).hexdigest(),
                                       translated_fields=1, shrine_messages={'script_count': 9, 'display_strings': 72})
                (root/'release_audit.json').write_text(json.dumps(audit), encoding='utf-8')
                output = root/'package.zip'
                with contextlib.redirect_stdout(io.StringIO()):
                    package([folder], output, patch)
                with ZipFile(output) as archive:
                    self.assertEqual({n for n in archive.namelist() if n.endswith('.esp')}, PATCHES[patch])
                    self.assertFalse(any(n.startswith('Optional/') for n in archive.namelist()))
                    manifest = json.loads(archive.read('validation.json'))
                    for name in PATCHES[patch]:
                        self.assertEqual(manifest[name]['archive_path'], name)
                        self.assertEqual(manifest[name]['validation']['shrine_messages']['display_strings'], 72)
                        self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), manifest[name]['output_sha256'])
                    self.assertIsNone(archive.testzip())


if __name__ == '__main__':
    unittest.main()
