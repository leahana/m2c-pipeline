import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP_SCRIPT = PROJECT_ROOT / "scripts" / "bootstrap_env.sh"
SUPPORTED_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class BootstrapEnvTests(unittest.TestCase):
    def _create_repo(self, root: Path) -> Path:
        script_path = root / "scripts" / "bootstrap_env.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BOOTSTRAP_SCRIPT, script_path)
        _make_executable(script_path)
        _write_text(root / "requirements.txt", "")
        _write_text(root / ".env.example", "M2C_PROJECT_ID=\n")
        return script_path

    def _run_bootstrap(
        self,
        script_path: Path,
        path_prefix: Path,
        *,
        include_system_path: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if include_system_path:
            env["PATH"] = f"{path_prefix}{os.pathsep}{env['PATH']}"
        else:
            env["PATH"] = str(path_prefix)
        return subprocess.run(
            [str(script_path)],
            cwd=script_path.parent.parent,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_bootstrap_uses_supported_python_when_python3_is_too_old(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            script_path = self._create_repo(repo_root)
            fake_bin = repo_root / "fake-bin"
            fake_bin.mkdir()

            unsupported_python3 = fake_bin / "python3"
            _write_text(
                unsupported_python3,
                "#!/usr/bin/env sh\n"
                "exit 1\n",
            )
            _make_executable(unsupported_python3)

            os.symlink(sys.executable, fake_bin / "python")

            result = self._run_bootstrap(script_path, fake_bin)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Using Python {SUPPORTED_VERSION} from {fake_bin / 'python'}", result.stdout)
            self.assertTrue((repo_root / "venv" / "bin" / "python").exists())

    def test_bootstrap_recreates_unsupported_existing_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            script_path = self._create_repo(repo_root)
            fake_bin = repo_root / "fake-bin"
            fake_bin.mkdir()
            os.symlink(sys.executable, fake_bin / "python3")

            stale_venv_python = repo_root / "venv" / "bin" / "python"
            _write_text(
                stale_venv_python,
                "#!/usr/bin/env sh\n"
                "if [ \"$1\" = \"-c\" ]; then\n"
                "  case \"$2\" in\n"
                "    *\"print(f\"*)\n"
                "      echo \"3.9\"\n"
                "      exit 0\n"
                "      ;;\n"
                "    *\"sys.version_info >= (3, 11)\"*)\n"
                "      exit 1\n"
                "      ;;\n"
                "  esac\n"
                "fi\n"
                "exit 1\n",
            )
            _make_executable(stale_venv_python)

            result = self._run_bootstrap(script_path, fake_bin)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Existing repo-local virtualenv uses unsupported Python 3.9; recreating", result.stdout)

            version_check = subprocess.run(
                [str(stale_venv_python), "-c", "import sys; print(sys.version_info[:2])"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(version_check.returncode, 0, version_check.stderr)
            self.assertIn(str(sys.version_info[:2]), version_check.stdout)

    def test_bootstrap_reuses_existing_supported_venv_without_system_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            script_path = self._create_repo(repo_root)
            fake_bin = repo_root / "fake-bin"
            fake_bin.mkdir()
            _write_text(fake_bin / "python3", "#!/usr/bin/env sh\nexit 1\n")
            _make_executable(fake_bin / "python3")
            _write_text(fake_bin / "python", "#!/usr/bin/env sh\nexit 1\n")
            _make_executable(fake_bin / "python")

            venv_python = repo_root / "venv" / "bin" / "python"
            venv_python.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(sys.executable, venv_python)

            result = self._run_bootstrap(script_path, fake_bin)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Using Python {SUPPORTED_VERSION} from {venv_python}", result.stdout)
            self.assertIn("Reusing existing repo-local virtualenv", result.stdout)
