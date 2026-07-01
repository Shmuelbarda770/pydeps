import tempfile
import unittest
from pathlib import Path

from depvex.cli import DepvexCLI


class DepvexCLITests(unittest.TestCase):
    def test_scan_updates_requirements_for_a_single_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_file = Path(tmpdir) / "sample.py"
            sample_file.write_text("import flet\n", encoding="utf-8")

            cli = DepvexCLI()
            exit_code = cli.scan(tmpdir)

            self.assertEqual(exit_code, 0)
            requirements_path = Path(tmpdir) / "requirements.txt"
            self.assertTrue(requirements_path.exists())
            self.assertTrue(any(line.startswith("flet") for line in requirements_path.read_text(encoding="utf-8").splitlines()))

    def test_check_returns_non_zero_when_requirements_are_outdated(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_file = Path(tmpdir) / "sample.py"
            sample_file.write_text("import requests\n", encoding="utf-8")

            requirements_path = Path(tmpdir) / "requirements.txt"
            requirements_path.write_text("old-package==1.0\n", encoding="utf-8")

            cli = DepvexCLI()
            exit_code = cli.check(tmpdir)

            self.assertNotEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
