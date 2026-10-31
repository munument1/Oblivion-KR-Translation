"""Regression checks for NorthernUI Full's obCJK Korean text outline preset."""

import configparser
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "assets" / "obcjk_fonts" / "obCJK.ini"


class NorthernUIFullOutlinePresetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = PRESET.read_bytes()
        cls.config = configparser.ConfigParser(interpolation=None)
        cls.config.read_string(cls.raw.decode("utf-8-sig"))

    def test_bridge_targets_unmodified_northernui(self):
        # Official NorthernUI.dll uses direct FontInfo rawID; mode 2 needs a
        # separately rebuilt, OBSE-messaging-enabled NorthernUI.dll.
        self.assertEqual(self.config.getint("obCJK", "NorthernUIEnable"), 1)
        self.assertEqual(self.config.get("obCJK", "ActiveCodePage"), "UTF8")

    def test_northernui_roles_have_readable_korean_outline(self):
        for slot in range(33, 38):
            with self.subTest(slot=slot):
                prefix = f"FontParam{slot}_"
                self.assertEqual(self.config.getint("UTF8", prefix + "OutlineMode"), 2)
                self.assertEqual(self.config.getint("UTF8", prefix + "OutlineSize"), 1)
                self.assertEqual(self.config.getint("UTF8", prefix + "OutlineAlpha"), 100)
                for region in (1, 2):
                    self.assertTrue(
                        self.config.get("UTF8", prefix + str(region))
                        .startswith("Source Han Serif KR,")
                    )

    def test_vanilla_subtitle_and_other_slots_unchanged(self):
        self.assertEqual(self.config.getint("obCJK", "AsciiRenderEnable"), 0)
        self.assertEqual(self.config.getint("UTF8", "FontParam2_OutlineMode"), 2)
        self.assertEqual(self.config.getint("UTF8", "FontParam2_OutlineSize"), 2)
        self.assertEqual(self.config.getint("UTF8", "FontParam2_OutlineAlpha"), 100)
        for slot in (1, 3, 5, 7, 8):
            with self.subTest(slot=slot):
                self.assertEqual(
                    self.config.getint("UTF8", f"FontParam{slot}_OutlineMode"), 0
                )

    def test_installer_preserves_bundled_preset(self):
        # install_obcjk.py rejects any mismatch between the bundle and this
        # generated preset; changing the source INI must not break the guard.
        from obcjk_fonts import preset_ini

        self.assertEqual(preset_ini(), self.raw)


if __name__ == "__main__":
    unittest.main()
