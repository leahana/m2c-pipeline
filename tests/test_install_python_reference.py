import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSTALL_REFERENCE = PROJECT_ROOT / "references" / "install-python.md"
SKILL_PATH = PROJECT_ROOT / "SKILL.md"
RUNTIME_COMMANDS = PROJECT_ROOT / "references" / "runtime-commands.md"


class InstallPythonReferenceTests(unittest.TestCase):
    def test_install_reference_covers_supported_platform_paths(self) -> None:
        text = INSTALL_REFERENCE.read_text(encoding="utf-8")
        cases = [
            (
                "pyenv",
                [
                    "### pyenv",
                    "`command -v pyenv`",
                    "`pyenv install 3.12.13`",
                ],
            ),
            (
                "uv",
                [
                    "### uv",
                    "`command -v uv`",
                    "`uv python install 3.12`",
                    "`uv python find 3.12`",
                ],
            ),
            (
                "conda",
                [
                    "### Conda",
                    "`echo \"$CONDA_DEFAULT_ENV\"`",
                    "`conda base`",
                ],
            ),
            ("macos-brew", ["## macOS", "`brew install python`", "`command -v brew`"]),
            (
                "ubuntu-apt",
                [
                    "## Debian/Ubuntu",
                    "`sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv`",
                    "`test -f /etc/debian_version`",
                ],
            ),
            (
                "windows-winget",
                [
                    "## Windows",
                    "`winget install -e --id Python.Python.3.12`",
                    "`Get-Command winget -ErrorAction SilentlyContinue`",
                ],
            ),
            (
                "unsupported",
                [
                    "## Unsupported Hosts",
                    "Do not invent a new install flow from scratch.",
                    "Ask the user to install any Python `>= 3.11` manually.",
                ],
            ),
        ]

        for name, fragments in cases:
            for fragment in fragments:
                with self.subTest(case=name, fragment=fragment):
                    self.assertIn(fragment, text)

    def test_skill_and_runtime_docs_point_to_install_reference(self) -> None:
        skill_text = SKILL_PATH.read_text(encoding="utf-8")
        runtime_text = RUNTIME_COMMANDS.read_text(encoding="utf-8")
        install_text = INSTALL_REFERENCE.read_text(encoding="utf-8")

        self.assertIn("references/install-python.md", skill_text)
        self.assertIn("permission plus network/admin confirmation", skill_text)
        self.assertIn("`pyenv`", skill_text)
        self.assertIn("`uv`", skill_text)
        self.assertIn("`conda base`", skill_text)
        self.assertIn("references/install-python.md", runtime_text)
        self.assertIn("`pyenv`", runtime_text)
        self.assertIn("`uv`", runtime_text)
        self.assertIn("conda base", runtime_text)
        self.assertIn("Windows repo-local bootstrap", runtime_text)
        self.assertIn("pyenv install 3.12.13", install_text)
        self.assertIn("uv python install 3.12", install_text)
        self.assertIn("brew install python", install_text)
        self.assertIn("apt-get install -y python3.11 python3.11-venv", install_text)
        self.assertIn("winget install -e --id Python.Python.3.12", install_text)

    def test_install_evals_match_documented_platforms(self) -> None:
        cases = [
            (
                PROJECT_ROOT / "evals" / "install-python-pyenv.md",
                ["`pyenv install 3.12.13`", "permission plus network/admin confirmation"],
            ),
            (
                PROJECT_ROOT / "evals" / "install-python-uv.md",
                ["`uv python install 3.12`", "`uv python find 3.12`"],
            ),
            (
                PROJECT_ROOT / "evals" / "install-python-macos.md",
                ["`brew install python`", "permission plus network/admin confirmation"],
            ),
            (
                PROJECT_ROOT / "evals" / "install-python-ubuntu.md",
                [
                    "`sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv`",
                    "permission plus network/admin confirmation",
                ],
            ),
            (
                PROJECT_ROOT / "evals" / "install-python-windows.md",
                [
                    "`winget install -e --id Python.Python.3.12`",
                    r"`.\venv\Scripts\python.exe -m pip install -r requirements.txt`",
                ],
            ),
            (
                PROJECT_ROOT / "evals" / "avoid-conda-base.md",
                ["`CONDA_DEFAULT_ENV=base`", "`conda base`", "repo-local `./venv`"],
            ),
        ]

        for path, fragments in cases:
            text = path.read_text(encoding="utf-8")
            for fragment in fragments:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertIn(fragment, text)
