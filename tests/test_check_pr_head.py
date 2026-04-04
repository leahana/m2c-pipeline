import unittest

from scripts.ci.check_pr_head import validate_pr_naming


class CheckPrHeadTests(unittest.TestCase):
    def test_validate_pr_naming_accepts_dev_branch(self) -> None:
        validate_pr_naming(
            "docs: sync README with CI/governance additions and 4:3 aspect ratio",
            "dev",
        )

    def test_validate_pr_naming_accepts_prefixed_branch(self) -> None:
        validate_pr_naming(
            "fix: tighten release tag guard",
            "fix/release-tag-guard",
        )

    def test_validate_pr_naming_rejects_codex_branch(self) -> None:
        with self.assertRaisesRegex(ValueError, "PR head branch does not match policy"):
            validate_pr_naming(
                "ci: harden generic skill release and governance gates",
                "codex/dev",
            )
