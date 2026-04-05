import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.ci.check_published_artifact_isomorphism import (
    IsomorphismError,
    _extract_archive_root,
    assert_isomorphic_trees,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class PublishedArtifactIsomorphismTests(unittest.TestCase):
    def test_extract_archive_root_rejects_top_level_file_beside_root_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive_path = base / "artifact.zip"
            destination = base / "extract"
            destination.mkdir()
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("bundle/README.md", "ok\n")
                archive.writestr("LEAK.txt", "unexpected\n")

            with self.assertRaisesRegex(
                IsomorphismError, "Expected exactly one top-level directory and no top-level files"
            ):
                _extract_archive_root(archive_path=archive_path, destination=destination)

    def test_assert_isomorphic_trees_accepts_identical_layout_and_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive_tree = base / "archive"
            staged_tree = base / "staged"
            _write(archive_tree / "README.md", "same\n")
            _write(archive_tree / "m2c-pipeline" / "SKILL.md", "skill\n")
            _write(staged_tree / "README.md", "same\n")
            _write(staged_tree / "m2c-pipeline" / "SKILL.md", "skill\n")

            assert_isomorphic_trees(archive_tree=archive_tree, staged_tree=staged_tree)

    def test_assert_isomorphic_trees_rejects_path_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive_tree = base / "archive"
            staged_tree = base / "staged"
            _write(archive_tree / "README.md", "same\n")
            _write(staged_tree / "README.md", "same\n")
            _write(staged_tree / "m2c-pipeline" / "EXTRA.md", "extra\n")

            with self.assertRaisesRegex(IsomorphismError, "Published path mismatch"):
                assert_isomorphic_trees(archive_tree=archive_tree, staged_tree=staged_tree)

    def test_assert_isomorphic_trees_rejects_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive_tree = base / "archive"
            staged_tree = base / "staged"
            _write(archive_tree / "README.md", "archive\n")
            _write(staged_tree / "README.md", "staged\n")

            with self.assertRaisesRegex(IsomorphismError, "Published content hash mismatch"):
                assert_isomorphic_trees(archive_tree=archive_tree, staged_tree=staged_tree)
