import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app.core.database import Base

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = BACKEND_ROOT.parent
ALEMBIC_CONFIG = BACKEND_ROOT / "alembic.ini"


def _alembic_environment(database_url: str) -> dict[str, str]:
    allowed_environment = {
        "HOME",
        "LANG",
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "WINDIR",
    }
    environment = {
        key: value for key, value in os.environ.items() if key.upper() in allowed_environment
    }
    environment["DATABASE_URL"] = database_url
    environment["PYTHONUTF8"] = "1"
    return environment


def _run_alembic(database_url: str, *arguments: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_ROOT,
        env=_alembic_environment(database_url),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _render_alembic_sql(database_url: str, *arguments: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments, "--sql"],
        cwd=BACKEND_ROOT,
        env=_alembic_environment(database_url),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_model_registry_contains_identity_tables() -> None:
    import app.models  # noqa: F401

    assert {
        "iam_organizations",
        "iam_users",
        "iam_memberships",
        "iam_roles",
        "iam_permissions",
        "iam_role_permissions",
        "iam_membership_roles",
        "iam_role_scope_grants",
        "iam_user_credentials",
        "iam_auth_sessions",
        "md_categories",
        "md_units",
        "md_materials",
        "procurement_requests",
        "procurement_request_lines",
        "approval_templates",
        "approval_template_steps",
        "approval_instances",
        "approval_nodes",
        "approval_actions",
        "purchase_orders",
        "purchase_order_lines",
        "goods_receipts",
        "goods_receipt_lines",
        "supplier_invoices",
        "supplier_invoice_lines",
        "inventory_balances",
        "inventory_movements",
        "business_audit_log",
        "b_suppliers",
        "b_supplier_risk_reviews",
        "b_sourcing_projects",
        "b_agent_tasks",
        "b_agent_task_events",
        "b_agent_confirmations",
        "b_knowledge_documents",
        "b_supplier_risk_assessments",
    } <= set(Base.metadata.tables)


def test_migration_graph_has_exactly_one_head() -> None:
    script = ScriptDirectory.from_config(Config(ALEMBIC_CONFIG))
    assert script.get_heads() == ["0012_inventory_audit"]


def test_mysql_downgrade_drops_tables_without_dropping_fk_indexes_first() -> None:
    sql = _render_alembic_sql(
        "mysql+pymysql://procurement:password@localhost/procurement",
        "downgrade",
        "0008_approval_workflow:base",
    )

    assert "DROP INDEX" not in sql
    assert sql.index("DROP TABLE iam_auth_sessions") < sql.index("DROP TABLE iam_user_credentials")
    assert sql.index("DROP TABLE iam_memberships") < sql.index("DROP TABLE iam_users")
    assert sql.index("DROP TABLE iam_users") < sql.index("DROP TABLE iam_organizations")


def test_migrations_upgrade_downgrade_and_match_metadata() -> None:
    scratch_root = REPOSITORY_ROOT / "tmp"
    scratch_root.mkdir(exist_ok=True)
    database_name = f"migration-test-{uuid4().hex}.db"
    database_path = scratch_root / database_name
    database_url = f"sqlite+pysqlite:///../tmp/{database_name}"

    try:
        _run_alembic(database_url, "upgrade", "head")
        _run_alembic(database_url, "check")

        engine = create_engine(database_url)
        tables = set(inspect(engine).get_table_names())
        engine.dispose()
        assert "iam_users" in tables
        assert "iam_role_scope_grants" in tables
        assert "iam_user_credentials" in tables
        assert "iam_auth_sessions" in tables
        assert "md_categories" in tables
        assert "md_units" in tables
        assert "md_materials" in tables
        assert "procurement_requests" in tables
        assert "procurement_request_lines" in tables
        assert "approval_templates" in tables
        assert "approval_template_steps" in tables
        assert "approval_instances" in tables
        assert "approval_nodes" in tables
        assert "approval_actions" in tables
        assert "purchase_orders" in tables
        assert "purchase_order_lines" in tables
        assert "goods_receipts" in tables
        assert "goods_receipt_lines" in tables
        assert "supplier_invoices" in tables
        assert "supplier_invoice_lines" in tables
        assert "inventory_balances" in tables
        assert "inventory_movements" in tables
        assert "business_audit_log" in tables
        assert "b_suppliers" in tables
        assert "b_sourcing_projects" in tables
        assert "b_agent_tasks" in tables
        assert "b_knowledge_documents" in tables
        assert "b_supplier_risk_assessments" in tables

        _run_alembic(database_url, "downgrade", "base")
        engine = create_engine(database_url)
        tables_after_downgrade = set(inspect(engine).get_table_names())
        engine.dispose()
        assert not any(table.startswith("iam_") for table in tables_after_downgrade)
        assert not any(table.startswith("b_") for table in tables_after_downgrade)

        _run_alembic(database_url, "upgrade", "head")
    finally:
        database_path.unlink(missing_ok=True)
