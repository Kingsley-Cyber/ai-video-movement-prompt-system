"""Versioned gap-evidence packing preserves captured context compatibility."""
import copy
import unittest

from lab.second_brain.src.context import build_context_bundle
from lab.second_brain.src.validate import validate_instance


class ContextPolicyUpgradeTests(unittest.TestCase):
    def test_current_and_prior_captured_policy_versions_validate(self):
        bundle = build_context_bundle('Laban effort', token_budget=12000)
        self.assertEqual(bundle['policy_versions']['context'], 'cpcs-context/1.3')
        validate_instance('context_bundle', bundle)
        prior = copy.deepcopy(bundle)
        prior['policy_versions']['context'] = 'cpcs-context/1.2'
        validate_instance('context_bundle', prior)

