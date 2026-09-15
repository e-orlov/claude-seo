#!/usr/bin/env python3
"""Regression tests for the standalone GEO contract layer."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GEO_DIR = REPO_ROOT / ".claude" / "geo-audit"
VALIDATOR = GEO_DIR / "scripts" / "validate_contracts.py"
BUILDER = REPO_ROOT / "methodology" / "geo-audit-workbench" / "scripts" / "build_stage1_contracts.py"
WORKBENCH_POLICY = REPO_ROOT / "methodology" / "geo-audit-workbench" / "scoring-policy"
GENERATED = (
    GEO_DIR / "contracts" / "source-catalog.yaml",
    GEO_DIR / "contracts" / "factor-catalog.yaml",
    GEO_DIR / "contracts" / "scoring-matrix.yaml",
    GEO_DIR / "contracts" / "scoring-rule.schema.json",
    GEO_DIR / "fixtures" / "minimal-complete" / "audit-config.json",
    GEO_DIR / "fixtures" / "minimal-complete" / "analysis-package.json",
    GEO_DIR / "fixtures" / "minimal-complete" / "report-package.json",
    GEO_DIR / "fixtures" / "negative" / "contract-mutations.yaml",
    GEO_DIR / "fixtures" / "over-2000-urls" / "gsc-selection-case.yaml",
    REPO_ROOT / ".claude" / "skills" / "seo-geo-report-generator" / "README.md",
)


def run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(path)], cwd=REPO_ROOT, capture_output=True, text=True, check=False)


class ContractTests(unittest.TestCase):
    def test_all_contracts_and_negative_fixtures(self) -> None:
        result = run(VALIDATOR)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["sources"], 18)
        self.assertEqual(payload["factors"], 129)
        self.assertEqual(payload["ddl_tables"], 41)
        self.assertEqual(payload["negative_fixtures_rejected"], 11)

    def test_contract_generation_is_byte_stable(self) -> None:
        before = {path: path.read_bytes() for path in GENERATED}
        first = run(BUILDER)
        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        after_first = {path: path.read_bytes() for path in GENERATED}
        second = run(BUILDER)
        self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
        after_second = {path: path.read_bytes() for path in GENERATED}
        self.assertEqual(before, after_first)
        self.assertEqual(after_first, after_second)

    def test_frozen_policy_migration_is_byte_exact(self) -> None:
        self.assertEqual(
            (GEO_DIR / "contracts" / "scoring-matrix.yaml").read_bytes(),
            (WORKBENCH_POLICY / "scoring-matrix.yaml").read_bytes(),
        )
        self.assertEqual(
            (REPO_ROOT / ".claude" / "skills" / "seo-geo-report-generator" / "README.md").read_bytes(),
            (WORKBENCH_POLICY / "README.md").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
