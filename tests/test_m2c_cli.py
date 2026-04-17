import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from m2c_pipeline.__main__ import main
from m2c_pipeline.version import __version__

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_INPUT = PROJECT_ROOT / "tests" / "fixtures" / "test_input.md"


class CliTests(unittest.TestCase):
    def test_version_flag_prints_package_version(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "m2c_pipeline", "--version"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), __version__)

    def test_runtime_python_311_plus_is_required(self) -> None:
        stderr = io.StringIO()
        with patch("m2c_pipeline.__main__._runtime_python_version", return_value=(3, 10)):
            with redirect_stderr(stderr):
                code = main([str(FIXTURE_INPUT), "--dry-run", "--translation-mode", "fallback"])

        self.assertEqual(code, 1)
        self.assertIn("Python 3.11+", stderr.getvalue())

    def test_fallback_requires_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("m2c_pipeline.config.load_local_env", return_value=None):
                with patch.dict(os.environ, {}, clear=True):
                    code = main(
                        [
                            str(FIXTURE_INPUT),
                            "--translation-mode",
                            "fallback",
                            "--output-dir",
                            tmpdir,
                        ]
                    )

        self.assertEqual(code, 1)

    def test_fallback_dry_run_succeeds_without_project_id(self) -> None:
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("m2c_pipeline.config.load_local_env", return_value=None):
                with patch.dict(os.environ, {}, clear=True):
                    with redirect_stdout(stdout):
                        code = main(
                            [
                                str(FIXTURE_INPUT),
                                "--dry-run",
                                "--translation-mode",
                                "fallback",
                                "--log-level",
                                "ERROR",
                                "--output-dir",
                                tmpdir,
                            ]
                        )

                    self.assertEqual(code, 0)
                    self.assertIn("Dry run completed successfully.", stdout.getvalue())

                    runs_root = Path(tmpdir) / "_runs"
                    run_dirs = sorted(runs_root.iterdir())
                    self.assertEqual(len(run_dirs), 1)
                    run_dir = run_dirs[0]
                    self.assertTrue((run_dir / "run.json").exists())
                    self.assertTrue((run_dir / "logs" / "run.log").exists())

                    manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
                    self.assertEqual(manifest["status"], "completed")
                    self.assertTrue(manifest["dry_run"])
                    self.assertEqual(manifest["summary"]["dry_run_count"], 2)
                    self.assertEqual(manifest["config"]["output_format"], "webp")
                    self.assertEqual(manifest["config"]["webp_quality"], 85)
                    self.assertEqual(manifest["config"]["translation_seed"], 7)

    def test_output_flags_override_config_in_run_manifest(self) -> None:
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("m2c_pipeline.config.load_local_env", return_value=None):
                with patch.dict(os.environ, {}, clear=True):
                    with redirect_stdout(stdout):
                        code = main(
                            [
                                str(FIXTURE_INPUT),
                                "--dry-run",
                                "--translation-mode",
                                "fallback",
                                "--log-level",
                                "ERROR",
                                "--output-dir",
                                tmpdir,
                                "--output-format",
                                "png",
                                "--translation-seed",
                                "random",
                                "--translation-temperature",
                                "0.15",
                                "--translation-top-p",
                                "0.25",
                                "--webp-quality",
                                "91",
                            ]
                        )

                    self.assertEqual(code, 0)
                    run_dir = next((Path(tmpdir) / "_runs").iterdir())
                    manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
                    self.assertEqual(manifest["config"]["output_format"], "png")
                    self.assertEqual(manifest["config"]["webp_quality"], 91)
                    self.assertIsNone(manifest["config"]["translation_seed"])
                    self.assertEqual(manifest["config"]["translation_temperature"], 0.15)
                    self.assertEqual(manifest["config"]["translation_top_p"], 0.25)
