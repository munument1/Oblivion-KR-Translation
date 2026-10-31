"""Verify the exact tested runtime reaches builds and installer packages."""
import configparser
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from zipfile import ZipFile

from build_obcjk_release import default_ini
from obcjk_runtime import BUNDLE, VERIFIED_SHA256, bundle_manifest, install_runtime
from package_obcjk_installer import package


class ObCJKRuntimeTests(unittest.TestCase):
    def test_tested_dll_and_enabled_preset(self):
        manifest = bundle_manifest()
        self.assertTrue(manifest['game_verified'])
        self.assertFalse(manifest['save_reload_verified'])
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(default_ini().decode('utf-8'))
        self.assertEqual(config['obCJK']['ActiveCodePage'], 'UTF8')
        self.assertEqual(config['obCJK']['XOBSEStringUtf8Enable'], '1')

    def test_install_exact_bytes_without_overwriting_existing_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            report = install_runtime(folder)
            target = Path(folder) / report['file']
            self.assertEqual(target.read_bytes(), (BUNDLE / 'obCJK.dll').read_bytes())
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), VERIFIED_SHA256)
            target.write_bytes(b'existing runtime')
            with self.assertRaises(FileExistsError):
                install_runtime(folder)
            self.assertEqual(target.read_bytes(), b'existing runtime')

    def test_modified_bundle_is_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bundle = root / 'bundle'
            shutil.copytree(BUNDLE, bundle)
            (bundle / 'obCJK.dll').write_bytes(b'wrong DLL')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                install_runtime(root / 'output', bundle)
            self.assertFalse((root / 'output').exists())

    def test_installer_package_preserves_runtime_provenance_and_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            exe = root / 'fixture.exe'
            exe.write_bytes(b'MZ test packaging fixture')
            output = root / 'installer.zip'
            with redirect_stdout(io.StringIO()):
                package(exe, output, version='1.1.9')
            with ZipFile(output) as archive:
                manifest = json.loads(archive.read('obcjk_runtime/manifest.json'))
                self.assertEqual(manifest['sha256'], VERIFIED_SHA256)
                self.assertIn('obcjk_runtime/source_changes/obCJK_XOBSEStringUtf8.h', archive.namelist())
                self.assertIn('obcjk_runtime/NOTICE_KO.txt', archive.namelist())
                self.assertFalse(any(Path(name).suffix in {'.esm', '.esp', '.dll'}
                                     for name in archive.namelist()))


if __name__ == '__main__':
    unittest.main()
