from app.modules.risk.models import SupplierRiskAssessmentRecord


def test_risk_orm_table_has_expected_name_and_columns() -> None:
    columns = set(SupplierRiskAssessmentRecord.__table__.columns.keys())

    assert SupplierRiskAssessmentRecord.__tablename__ == "b_supplier_risk_assessments"
    assert {
        "assessment_id",
        "supplier_id",
        "org_id",
        "supplier_name",
        "score",
        "risk_level",
        "recommended_action",
        "factors",
        "summary",
        "assessed_by",
        "created_at",
        "updated_at",
    }.issubset(columns)


def test_risk_orm_table_keeps_query_indexes() -> None:
    indexes = {index.name for index in SupplierRiskAssessmentRecord.__table__.indexes}

    assert "ix_b_supplier_risk_assessments_supplier_updated" in indexes
    assert "ix_b_supplier_risk_assessments_org_risk" in indexes
    assert "ix_b_supplier_risk_assessments_score" in indexes
