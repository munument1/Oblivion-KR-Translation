import configparser
from contextlib import redirect_stdout
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from install_obcjk import main, update_existing_ini
from build_obcjk_release import ORIGINAL_FONT_SETTINGS
from obcjk_fonts import BUNDLE, bundle_manifest, preset_ini


SETTINGS = '[Fonts]\n' + '\n'.join(f'SFontFile_{i}=Data\\Fonts\\Original{i}.fnt' for i in range(1, 6))


class InstallerTests(unittest.TestCase):
    def test_pyinstaller_spec_includes_runtime_dynamic_imports(self):
        spec = (Path(__file__).resolve().parents[1] / 'OblivionKRBuilder.spec').read_text(encoding='utf-8')
        for module in ('build_vanilla_overlay', 'build_obcjk_release', 'build_obcjk_locations',
                       'master_layout', 'build_video_subtitles'):
            self.assertIn(repr(module), spec)

    def test_packaged_fonts_and_verified_control_setting(self):
        manifest = bundle_manifest()
        self.assertEqual({f['id'] for f in manifest['fonts']}, {'source_regular', 'source_medium', 'iropke'})
        ini = configparser.ConfigParser(interpolation=None)
        ini.read_string(preset_ini().decode('utf-8'))
        self.assertEqual(ini['obCJK']['AsciiRenderEnable'], '0')
        self.assertEqual(ini['obCJK']['UILang'], 'ko')
        self.assertEqual(ini['obCJK']['BackgroundOpacity'], '0')
        for slot in (1, 2, 3):
            for half in (1, 2):
                fields = ini['UTF8'][f'FontParam{slot}_{half}'].split(',')
                self.assertEqual((fields[0], fields[6]), ('Source Han Serif KR Medium', '500'))
        for slot in (1, 3, 5, 7, 8):
            self.assertEqual(ini['UTF8'][f'FontParam{slot}_OutlineMode'], '0')
        for slot in (33, 34, 35, 36, 37):
            self.assertEqual(ini['UTF8'][f'FontParam{slot}_OutlineMode'], '2')
            self.assertEqual(ini['UTF8'][f'FontParam{slot}_OutlineSize'], '1')
            self.assertEqual(ini['UTF8'][f'FontParam{slot}_OutlineAlpha'], '100')
        self.assertEqual(ini['UTF8']['FontParam2_OutlineMode'], '2')
        self.assertEqual(ini['UTF8']['FontParam2_OutlineSize'], '2')
        self.assertEqual(ini['UTF8']['FontParam2_OutlineAlpha'], '100')
        self.assertEqual((BUNDLE / 'obCJK.ini').read_bytes(), preset_ini())

    def test_existing_ini_only_fonts_with_bom_and_crlf_and_original_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Oblivion.ini'
            raw = ('\ufeff[General]\r\nSName=제국 감옥\r\n[Fonts]\r\n' +
                   ''.join(f'SFontFile_{i}=Old{i}\r\n' for i in range(1, 6)) +
                   '[Display]\r\niSize W=1920\r\n').encode('utf-8')
            path.write_bytes(raw)
            self.assertTrue(update_existing_ini(path, SETTINGS, dry_run=True))
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(len(list(Path(tmp).iterdir())), 1)
            backup = Path(update_existing_ini(path, SETTINGS))
            self.assertEqual(backup.read_bytes(), raw)
            result = path.read_bytes()
            self.assertTrue(result.startswith(b'\xef\xbb\xbf'))
            self.assertIn('SName=제국 감옥\r\n'.encode('utf-8'), result)
            self.assertIn(b'[Display]\r\niSize W=1920\r\n', result)
            self.assertEqual(update_existing_ini(path, SETTINGS), None)
            self.assertEqual(backup.read_bytes(), raw)

    def test_incomplete_ini_refused_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Oblivion.ini'
            raw = b'[Fonts]\nSFontFile_1=old\n'
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'missing'):
                update_existing_ini(path, SETTINGS, dry_run=True)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(len(list(Path(tmp).iterdir())), 1)

    def test_non_utf8_bytes_and_case_insensitive_font_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Oblivion.ini'
            raw = (b'\xef\xbb\xbf[Fonts]\r\n' +
                   b''.join(f'sfontfile_{i}=Old{i}\r\n'.encode('ascii') for i in range(1, 6)) +
                   b'[General]\r\nSText=\x81\x90\xfd\r\n')
            path.write_bytes(raw)
            backup = Path(update_existing_ini(path, SETTINGS))
            self.assertEqual(backup.read_bytes(), raw)
            self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf[Fonts]\r\n'))
            self.assertTrue(path.read_bytes().endswith(b'[General]\r\nSText=\x81\x90\xfd\r\n'))
            self.assertIn(b'SFontFile_5=Data\\Fonts\\Original5.fnt\r\n', path.read_bytes())

    def test_automatic_ini_and_no_profile_or_missing_ini_creation(self):
        for exists in (True, False):
            with self.subTest(existing_ini=exists), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                ini = root / 'Documents/My Games/Oblivion/Oblivion.ini'
                if exists:
                    ini.parent.mkdir(parents=True)
                    ini.write_text(SETTINGS, encoding='ascii')
                output = root / 'output/Oblivion_KR_Mod'

                def fake_build(args):
                    self.assertEqual(args.video_subtitles, 'off')
                    args.output.mkdir(parents=True)
                    (args.output / 'Oblivion.esm').write_bytes(b'validated test fixture')
                    for name in ('translation_audit.json', 'obcjk_validation.json', 'location_validation.json'):
                        (args.output / name).write_text('{}', encoding='ascii')
                    (args.output / 'FONT_SETTINGS.txt').write_text(ORIGINAL_FONT_SETTINGS, encoding='ascii')

                with patch('install_obcjk.documents_ini', return_value=ini), \
                     patch('install_obcjk.install_fonts', return_value={'fonts': []}), \
                     patch('build_obcjk_release.build', side_effect=fake_build), \
                     patch('sys.argv', ['installer', '--data-dir', str(root / 'Data'), '--output', str(output)]), \
                     redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 0)
                self.assertEqual(ini.exists(), exists)
                self.assertEqual({p.name for p in output.iterdir()}, {'Oblivion.esm'})
                self.assertFalse((root / 'profiles').exists())
                self.assertFalse((root / 'Documents').exists() and not exists)
                self.assertTrue(output.with_name(output.name + '.validation.json').is_file())
                if exists:
                    self.assertEqual(ini.read_text(encoding='ascii').splitlines(), ORIGINAL_FONT_SETTINGS.splitlines())


if __name__ == '__main__':
    unittest.main()
