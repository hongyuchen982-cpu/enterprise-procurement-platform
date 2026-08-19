import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / ".github" / "scripts" / "validate_branch_flow.py"


@pytest.mark.parametrize(
    ("base_ref", "head_ref"),
    [
        ("develop", "feature/a-procurement"),
        ("develop", "fix/b-worker-retry"),
        ("main", "develop"),
        ("main", "hotfix/a-invoice-total"),
    ],
)
def test_allowed_branch_flows(base_ref: str, head_ref: str) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), base_ref, head_ref],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("base_ref", "head_ref"),
    [
        ("develop", "feature/procurement"),
        ("develop", "feature/c-unknown"),
        ("main", "feature/a-procurement"),
        ("main", "fix/a-production"),
        ("release", "develop"),
    ],
)
def test_disallowed_branch_flows(base_ref: str, head_ref: str) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), base_ref, head_ref],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
