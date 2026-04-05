"""Audit repository governance settings against the frozen policy contract."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.common import GOVERNANCE_CONTRACT, load_json


class GovernanceAuditError(RuntimeError):
    """Raised when governance settings drift from policy."""


class GitHubApi:
    def __init__(self, token: str, api_url: str) -> None:
        self._token = token
        self._api_url = api_url.rstrip("/")

    def get(self, path: str) -> dict | list:
        request = urllib.request.Request(
            url=f"{self._api_url}{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise GovernanceAuditError(
                f"GitHub API request failed for {path}: {exc.code} {body}"
            ) from exc


def _parse_repo() -> tuple[str, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repository:
        raise GovernanceAuditError("GITHUB_REPOSITORY must be set to <owner>/<repo>.")
    owner, repo = repository.split("/", 1)
    return owner, repo


def audit_branch_protection(api: GitHubApi, owner: str, repo: str, contract: dict) -> None:
    branch = contract["default_branch"]
    protection = api.get(f"/repos/{owner}/{repo}/branches/{branch}/protection")
    enforce_admins = api.get(f"/repos/{owner}/{repo}/branches/{branch}/protection/enforce_admins")
    required_checks = api.get(
        f"/repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks"
    )

    contexts = sorted(required_checks.get("contexts", []))
    expected_contexts = sorted(contract["required_checks"])
    if contexts != expected_contexts:
        raise GovernanceAuditError(
            f"Branch protection required checks mismatch: expected {expected_contexts!r}, got {contexts!r}"
        )

    if not enforce_admins.get("enabled", False):
        raise GovernanceAuditError("Branch protection must enforce administrators.")

    bypass_allowances = (
        protection.get("required_pull_request_reviews", {}) or {}
    ).get("bypass_pull_request_allowances", {}) or {}
    if any(bypass_allowances.get(key) for key in ("users", "teams", "apps")):
        raise GovernanceAuditError("Branch protection bypass allowances must be empty.")


def find_matching_tag_rulesets(rulesets: list[dict], tag_contract: dict) -> list[dict]:
    expected_target = tag_contract["target"]
    expected_enforcement = tag_contract["enforcement"]
    expected_patterns = set(tag_contract["ref_name_include"])

    matches = []
    for ruleset in rulesets:
        include_patterns = set(
            ((ruleset.get("conditions", {}) or {}).get("ref_name", {}) or {}).get("include", [])
        )
        if ruleset.get("target") != expected_target:
            continue
        if ruleset.get("enforcement") != expected_enforcement:
            continue
        if not expected_patterns.issubset(include_patterns):
            continue
        matches.append(ruleset)
    return matches


def validate_tag_ruleset_payload(ruleset: dict, tag_contract: dict) -> None:
    bypass_actors = ruleset.get("bypass_actors", []) or []
    if bypass_actors:
        raise GovernanceAuditError("Tag ruleset bypass actors must be empty.")

    rule_types = {rule.get("type") for rule in ruleset.get("rules", []) if rule.get("type")}
    required_rule_types = set(tag_contract["required_tag_rules"])
    if rule_types != required_rule_types:
        raise GovernanceAuditError(
            f"Tag ruleset must contain exactly {sorted(required_rule_types)!r}, got {sorted(rule_types)!r}"
        )


def audit_skill_branch_ruleset(api: GitHubApi, owner: str, repo: str, contract: dict) -> None:
    rulesets_summary = api.get(f"/repos/{owner}/{repo}/rulesets?per_page=100")
    rulesets = [
        api.get(f"/repos/{owner}/{repo}/rulesets/{rs['id']}")
        for rs in rulesets_summary
    ]
    skill_contract = contract["skill_branch_ruleset"]
    expected_target = skill_contract["target"]
    expected_enforcement = skill_contract["enforcement"]
    expected_patterns = set(skill_contract["ref_name_include"])

    matches = [
        rs for rs in rulesets
        if rs.get("target") == expected_target
        and rs.get("enforcement") == expected_enforcement
        and expected_patterns.issubset(
            set(
                ((rs.get("conditions", {}) or {}).get("ref_name", {}) or {}).get("include", [])
            )
        )
    ]

    if not matches:
        raise GovernanceAuditError(
            f"No matching active skill branch ruleset found for "
            f"{skill_contract['ref_name_include']!r}."
        )
    if len(matches) > 1:
        raise GovernanceAuditError(
            f"Expected exactly one matching skill branch ruleset, found {len(matches)}."
        )

    ruleset = matches[0]
    rule_types = {rule.get("type") for rule in ruleset.get("rules", []) if rule.get("type")}
    required_rules = set(skill_contract["required_rules"])
    if not required_rules.issubset(rule_types):
        missing = required_rules - rule_types
        raise GovernanceAuditError(
            f"Skill branch ruleset is missing required rules: {sorted(missing)!r}."
        )


def audit_tag_ruleset(api: GitHubApi, owner: str, repo: str, contract: dict) -> None:
    rulesets_summary = api.get(f"/repos/{owner}/{repo}/rulesets?per_page=100")
    # List endpoint omits conditions/rules; fetch each ruleset individually.
    rulesets = [
        api.get(f"/repos/{owner}/{repo}/rulesets/{rs['id']}")
        for rs in rulesets_summary
    ]
    tag_contract = contract["tag_ruleset"]
    matches = find_matching_tag_rulesets(rulesets, tag_contract)
    if not matches:
        raise GovernanceAuditError(
            f"No matching active tag ruleset found for include patterns {tag_contract['ref_name_include']!r}."
        )

    if len(matches) > 1:
        raise GovernanceAuditError(
            "Expected exactly one matching active tag ruleset for "
            f"{tag_contract['ref_name_include']!r}, found {len(matches)}."
        )

    validate_tag_ruleset_payload(matches[0], tag_contract)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit repository governance settings.")
    parser.add_argument(
        "--mode",
        choices=["all", "branch-protection", "tag-ruleset", "skill-branch-ruleset"],
        default="all",
        help="Subset of audits to run.",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN must be set for governance audit.")

    owner, repo = _parse_repo()
    api = GitHubApi(token=token, api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    contract = load_json(GOVERNANCE_CONTRACT)

    if args.mode in {"all", "branch-protection"}:
        audit_branch_protection(api, owner, repo, contract)
        print("Branch protection audit passed.")
    if args.mode in {"all", "tag-ruleset"}:
        audit_tag_ruleset(api, owner, repo, contract)
        print("Tag ruleset audit passed.")
    if args.mode in {"all", "skill-branch-ruleset"}:
        audit_skill_branch_ruleset(api, owner, repo, contract)
        print("Skill branch ruleset audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
