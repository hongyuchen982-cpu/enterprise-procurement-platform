from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CODEOWNERS = REPOSITORY_ROOT / ".github" / "CODEOWNERS"
A_OWNER = "@hongyuchen982-cpu"
B_OWNER = "@cannjin197-netizen"
KNOWN_OWNERS = {A_OWNER, B_OWNER}


def _rules() -> dict[str, tuple[str, ...]]:
    rules: dict[str, tuple[str, ...]] = {}
    for raw_line in CODEOWNERS.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        pattern, *owners = line.split()
        rules[pattern] = tuple(owners)
    return rules


def test_codeowners_uses_real_known_accounts_and_one_owner_per_rule() -> None:
    rules = _rules()
    assert rules
    assert rules["*"] == (A_OWNER,)
    assert all(len(owners) == 1 for owners in rules.values())
    assert {owner for owners in rules.values() for owner in owners} == KNOWN_OWNERS


def test_member_entrypoints_and_contracts_have_expected_owners() -> None:
    rules = _rules()
    expected = {
        "/backend/app/api/routes_a.py": A_OWNER,
        "/backend/app/api/routes_b.py": B_OWNER,
        "/backend/app/contracts/identity.py": A_OWNER,
        "/backend/app/contracts/organizations.py": A_OWNER,
        "/backend/app/contracts/master_data.py": A_OWNER,
        "/backend/app/contracts/procurement.py": A_OWNER,
        "/backend/app/contracts/supplier.py": B_OWNER,
        "/backend/app/contracts/sourcing.py": B_OWNER,
        "/frontend/src/features/a/": A_OWNER,
        "/frontend/src/features/b/": B_OWNER,
    }
    for pattern, owner in expected.items():
        assert rules.get(pattern) == (owner,), f"incorrect CODEOWNER for {pattern}"


def test_all_declared_business_modules_have_an_owner() -> None:
    rules = _rules()
    a_modules = {
        "identity",
        "organizations",
        "master_data",
        "procurement",
        "approval",
        "orders",
        "receiving",
        "inventory",
        "invoices",
        "audit",
    }
    b_modules = {
        "suppliers",
        "sourcing",
        "agents",
        "tools",
        "rag",
        "risk",
        "reporting",
    }
    for module in a_modules:
        assert rules.get(f"/backend/app/modules/{module}/") == (A_OWNER,)
    for module in b_modules:
        assert rules.get(f"/backend/app/modules/{module}/") == (B_OWNER,)
