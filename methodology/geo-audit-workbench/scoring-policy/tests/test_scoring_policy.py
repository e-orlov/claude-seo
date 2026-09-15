#!/usr/bin/env python3
"""Regression tests for the frozen GEO scoring policy."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


POLICY_DIR = Path(__file__).resolve().parents[1]
BUILDER = POLICY_DIR / "scripts" / "build_scoring_policy.py"
VALIDATOR = POLICY_DIR / "scripts" / "validate_scoring_policy.py"
GENERATED_OUTPUTS = (
    POLICY_DIR / "scoring-matrix.yaml",
    POLICY_DIR / "README.md",
    POLICY_DIR / "fixtures" / "boundary-cases.yaml",
)


def run_script(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(path)],
        check=False,
        capture_output=True,
        text=True,
        cwd=POLICY_DIR,
    )


def load_validator_module():
    spec = importlib.util.spec_from_file_location("geo_scoring_policy_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load policy validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScoringPolicyTests(unittest.TestCase):
    def test_full_policy_validation(self) -> None:
        result = run_script(VALIDATOR)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["rules"], 129)
        self.assertGreaterEqual(payload["factor_boundary_cases"], 3 * 129)
        self.assertGreaterEqual(payload["adversarial_cases"], 10)
        self.assertGreaterEqual(payload["betroffenheit_cases"], 10)
        self.assertGreaterEqual(payload["confidence_cases"], 12)
        self.assertGreaterEqual(payload["priority_cases"], 15)
        self.assertGreaterEqual(payload["rollup_cases"], 50)

    def test_generator_is_byte_stable(self) -> None:
        before = {path: path.read_bytes() for path in GENERATED_OUTPUTS}
        first = run_script(BUILDER)
        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        after_first = {path: path.read_bytes() for path in GENERATED_OUTPUTS}
        second = run_script(BUILDER)
        self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
        after_second = {path: path.read_bytes() for path in GENERATED_OUTPUTS}
        self.assertEqual(before, after_first)
        self.assertEqual(after_first, after_second)

    def test_schema_rejects_unknown_runtime_field(self) -> None:
        validator = load_validator_module()
        policy = validator.load_yaml(validator.POLICY_PATH)
        schema = json.loads(validator.SCHEMA_PATH.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(policy)
        mutated["rules"][0]["runtime_discretion"] = True
        with self.assertRaises(validator.ValidationFailure):
            validator.validate_json_schema_instance(mutated, schema, schema)

    def test_schema_rejects_boolean_as_number(self) -> None:
        validator = load_validator_module()
        policy = validator.load_yaml(validator.POLICY_PATH)
        schema = json.loads(validator.SCHEMA_PATH.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(policy)
        mutated["rules"][0]["coverage_gate"]["minimum_rate"] = True
        with self.assertRaises(validator.ValidationFailure):
            validator.validate_json_schema_instance(mutated, schema, schema)


if __name__ == "__main__":
    unittest.main()
