from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parents[3] / "frontend" / "src"


def _source_files(root: Path) -> list[Path]:
    return [*root.rglob("*.ts"), *root.rglob("*.vue")]


def test_frontend_features_do_not_import_the_other_delivery_lane() -> None:
    violations: list[str] = []
    for lane, other_lane in (("a", "b"), ("b", "a")):
        root = FRONTEND_SRC / "features" / lane
        for path in _source_files(root):
            source = path.read_text(encoding="utf-8")
            forbidden_markers = (f"features/{other_lane}", f"features\\{other_lane}")
            if any(marker in source for marker in forbidden_markers):
                violations.append(f"{path}: imports frontend lane {other_lane}")
    assert not violations, "\n".join(violations)
