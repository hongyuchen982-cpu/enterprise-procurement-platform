import ast
from pathlib import Path

MODULES_ROOT = Path(__file__).resolve().parents[2] / "app" / "modules"
RESTRICTED_AGENT_MODULES = {"agents", "tools", "rag"}
FORBIDDEN_INTERNAL_PARTS = {"models", "repository"}


def _python_files() -> list[Path]:
    if not MODULES_ROOT.exists():
        return []
    return [path for path in MODULES_ROOT.rglob("*.py") if path.name != "__init__.py"]


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _is_cross_module_internal_import(source_module: str, imported: str) -> bool:
    parts = imported.split(".")
    if len(parts) < 4 or parts[:2] != ["app", "modules"]:
        return False
    target_module = parts[2]
    return source_module != target_module and bool(FORBIDDEN_INTERNAL_PARTS.intersection(parts))


def test_modules_do_not_import_other_module_internals() -> None:
    violations: list[str] = []
    for path in _python_files():
        source_module = path.relative_to(MODULES_ROOT).parts[0]
        for imported in _imports(path):
            if _is_cross_module_internal_import(source_module, imported):
                violations.append(f"{path}: forbidden import {imported}")
    assert not violations, "\n".join(violations)


def test_facade_and_contract_imports_are_allowed() -> None:
    allowed_imports = (
        "app.modules.suppliers.facade",
        "app.modules.procurement.facade",
        "app.contracts.supplier",
        "app.contracts.procurement",
    )
    assert not any(
        _is_cross_module_internal_import("orders", imported) for imported in allowed_imports
    )


def test_agent_tool_and_rag_modules_do_not_import_database_or_repositories() -> None:
    violations: list[str] = []
    for path in _python_files():
        source_module = path.relative_to(MODULES_ROOT).parts[0]
        if source_module not in RESTRICTED_AGENT_MODULES:
            continue
        for imported in _imports(path):
            parts = set(imported.split("."))
            if imported == "app.core.database" or {"repository", "models"}.intersection(parts):
                violations.append(f"{path}: Agent boundary violation {imported}")
    assert not violations, "\n".join(violations)
