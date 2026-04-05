"""Validate the frozen required-check contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import GOVERNANCE_CONTRACT, REPO_ROOT, load_json

EXPECTED_REQUIRED_CHECKS = [
    "policy-pr-head",
    "skill-spec",
    "repo-policy",
    "unit-tests",
    "offline-smoke",
    "skill-bootstrap-smoke",
    "package-dryrun",
    "published-artifact-isomorphism",
    "required-job-contract",
]


def validate_required_job_contract() -> None:
    governance = load_json(GOVERNANCE_CONTRACT)
    configured = governance.get("required_checks", [])
    if configured != EXPECTED_REQUIRED_CHECKS:
        raise ValueError(
            f"governance.json required_checks must be exactly {EXPECTED_REQUIRED_CHECKS!r}, "
            f"got {configured!r}"
        )

    ci_workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job_names = re.findall(r"^ {4}name:\s*(.+?)\s*$", ci_workflow, flags=re.MULTILINE)
    if sorted(job_names) != sorted(EXPECTED_REQUIRED_CHECKS):
        raise ValueError(
            f"ci.yml job names must be exactly {EXPECTED_REQUIRED_CHECKS!r}, got {job_names!r}"
        )


def main() -> int:
    validate_required_job_contract()
    print("Required job contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
