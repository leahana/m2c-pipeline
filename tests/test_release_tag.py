import unittest

from scripts.ci.check_release_tag import validate_release_tag


class ReleaseTagTests(unittest.TestCase):
    def test_validate_release_tag_accepts_matching_tag_and_version(self) -> None:
        validate_release_tag("v1.2.3", r"^v\d+\.\d+\.\d+$", "1.2.3")

    def test_validate_release_tag_rejects_non_matching_regex(self) -> None:
        with self.assertRaises(ValueError):
            validate_release_tag("release-1.2.3", r"^v\d+\.\d+\.\d+$", "1.2.3")

    def test_validate_release_tag_rejects_mismatched_version(self) -> None:
        with self.assertRaises(ValueError):
            validate_release_tag("v1.2.4", r"^v\d+\.\d+\.\d+$", "1.2.3")
