from pathlib import Path
import subprocess
import sys
import unittest


PACKAGE_ROOT = Path(__file__).parents[1]


class SelftestEntryPointTests(unittest.TestCase):
    def test_selftest_runs_from_package_root_without_network(self):
        result = subprocess.run(
            [sys.executable, "selftest.py"],
            cwd=PACKAGE_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("validate-ledger", result.stdout)
        self.assertIn("probe-t1", result.stdout)
        self.assertIn("check-8534", result.stdout)
        self.assertIn("detect-echoes", result.stdout)
