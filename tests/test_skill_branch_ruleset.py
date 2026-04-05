import unittest
from unittest.mock import MagicMock

from scripts.ci.common import GOVERNANCE_CONTRACT, load_json
from scripts.ci.governance_audit import GovernanceAuditError, GitHubApi, audit_skill_branch_ruleset


def _ruleset(
    *,
    target="branch",
    enforcement="active",
    include=None,
    rules=None,
    ruleset_id=1,
):
    return {
        "id": ruleset_id,
        "target": target,
        "enforcement": enforcement,
        "conditions": {
            "ref_name": {
                "include": include if include is not None else ["refs/heads/skill"],
            }
        },
        "rules": [{"type": r} for r in (rules if rules is not None else ["deletion"])],
        "bypass_actors": [],
    }


def _make_api(ruleset: dict) -> GitHubApi:
    api = MagicMock(spec=GitHubApi)
    api.get.side_effect = lambda path: (
        [{"id": ruleset["id"]}] if "rulesets?" in path
        else ruleset
    )
    return api


class SkillBranchRulesetAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_json(GOVERNANCE_CONTRACT)

    def test_valid_ruleset_passes(self) -> None:
        api = _make_api(_ruleset())
        audit_skill_branch_ruleset(api, "owner", "repo", self.contract)

    def test_missing_ruleset_raises(self) -> None:
        api = MagicMock(spec=GitHubApi)
        api.get.return_value = []
        with self.assertRaises(GovernanceAuditError):
            audit_skill_branch_ruleset(api, "owner", "repo", self.contract)

    def test_wrong_target_raises(self) -> None:
        api = _make_api(_ruleset(target="tag"))
        api.get.side_effect = lambda path: (
            [{"id": 1}] if "rulesets?" in path else _ruleset(target="tag")
        )
        with self.assertRaises(GovernanceAuditError):
            audit_skill_branch_ruleset(api, "owner", "repo", self.contract)

    def test_wrong_enforcement_raises(self) -> None:
        api = _make_api(_ruleset(enforcement="evaluate"))
        with self.assertRaises(GovernanceAuditError):
            audit_skill_branch_ruleset(api, "owner", "repo", self.contract)

    def test_wrong_branch_pattern_raises(self) -> None:
        api = _make_api(_ruleset(include=["refs/heads/main"]))
        with self.assertRaises(GovernanceAuditError):
            audit_skill_branch_ruleset(api, "owner", "repo", self.contract)

    def test_missing_deletion_rule_raises(self) -> None:
        api = _make_api(_ruleset(rules=[]))
        with self.assertRaises(GovernanceAuditError):
            audit_skill_branch_ruleset(api, "owner", "repo", self.contract)

    def test_skill_contract_declares_expected_rules(self) -> None:
        skill_contract = self.contract["skill_branch_ruleset"]
        self.assertEqual(skill_contract["required_rules"], ["deletion"])
        self.assertEqual(skill_contract["ref_name_include"], ["refs/heads/skill"])
        self.assertEqual(skill_contract["target"], "branch")
