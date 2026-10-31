"""Release packaging must never silently reuse an obsolete installer version."""
import inspect
import subprocess
import sys
import unittest
from pathlib import Path

from package_obcjk_installer import package

ROOT = Path(__file__).resolve().parents[1]


class InstallerExplicitVersionTests(unittest.TestCase):
    def test_package_function_requires_version_argument(self):
        parameter = inspect.signature(package).parameters["version"]
        self.assertIs(parameter.default, inspect.Parameter.empty)

    def test_cli_rejects_missing_version_before_any_file_io(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "package_obcjk_installer.py"),
             "--exe", "does-not-exist.exe", "--output", "does-not-exist.zip"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("--version", result.stderr)
        self.assertIn("required", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
