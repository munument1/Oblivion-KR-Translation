"""The installer must also start on a non-Korean Windows code page."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class InstallerConsoleTests(unittest.TestCase):
    def test_help_on_western_console(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / 'install_obcjk.py'), '--help'],
            env={**os.environ, 'PYTHONIOENCODING': 'cp1252'},
            capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'--data-dir', result.stdout)
        self.assertNotIn(b'UnicodeEncodeError', result.stderr)
