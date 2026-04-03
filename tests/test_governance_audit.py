import unittest

from scripts.ci.common import GOVERNANCE_CONTRACT, load_json
from scripts.ci.governance_audit import (
    GovernanceAuditError,
    find_matching_tag_rulesets,
    validate_tag_ruleset_payload,
)


class GovernanceAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_json(GOVERNANCE_CONTRACT)
        self.tag_contract = self.contract["tag_ruleset"]

    def _ruleset(self, *, include=None, rules=None, bypass_actors=None, target="tag", enforcement="active"):
        return {
            "target": target,
            "enforcement": enforcement,
            "conditions": {
                "ref_name": {
                    "include": include or ["refs/tags/v*"],
                }
            },
            "rules": [{"type": rule_type} for rule_type in (rules or ["update", "deletion"])],
            "bypass_actors": bypass_actors or [],
        }

    def test_find_matching_tag_rulesets_filters_by_contract(self) -> None:
        rulesets = [
            self._ruleset(),
            self._ruleset(target="branch"),
            self._ruleset(include=["refs/tags/release-*"]),
            self._ruleset(enforcement="evaluate"),
        ]

        matches = find_matching_tag_rulesets(rulesets, self.tag_contract)

        self.assertEqual(matches, [rulesets[0]])

    def test_validate_tag_ruleset_payload_accepts_update_and_deletion(self) -> None:
        validate_tag_ruleset_payload(self._ruleset(), self.tag_contract)

    def test_validate_tag_ruleset_payload_rejects_missing_update(self) -> None:
        with self.assertRaises(GovernanceAuditError):
            validate_tag_ruleset_payload(
                self._ruleset(rules=["deletion"]),
                self.tag_contract,
            )

    def test_validate_tag_ruleset_payload_rejects_missing_deletion(self) -> None:
        with self.assertRaises(GovernanceAuditError):
            validate_tag_ruleset_payload(
                self._ruleset(rules=["update"]),
                self.tag_contract,
            )

    def test_validate_tag_ruleset_payload_rejects_creation_only(self) -> None:
        with self.assertRaises(GovernanceAuditError):
            validate_tag_ruleset_payload(
                self._ruleset(rules=["creation"]),
                self.tag_contract,
            )

    def test_validate_tag_ruleset_payload_rejects_creation_update_deletion_combo(self) -> None:
        with self.assertRaises(GovernanceAuditError):
            validate_tag_ruleset_payload(
                self._ruleset(rules=["creation", "update", "deletion"]),
                self.tag_contract,
            )

    def test_validate_tag_ruleset_payload_rejects_bypass_actors(self) -> None:
        with self.assertRaises(GovernanceAuditError):
            validate_tag_ruleset_payload(
                self._ruleset(bypass_actors=[{"actor_id": 1, "actor_type": "RepositoryRole"}]),
                self.tag_contract,
            )

    def test_tag_contract_declares_expected_required_rules(self) -> None:
        self.assertEqual(
            self.tag_contract["required_tag_rules"],
            ["update", "deletion"],
        )
