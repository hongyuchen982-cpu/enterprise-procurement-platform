from app.modules.suppliers.models import SupplierRecord, SupplierRiskReviewRecord


def test_supplier_orm_tables_have_expected_names_and_columns() -> None:
    supplier_columns = set(SupplierRecord.__table__.columns.keys())
    review_columns = set(SupplierRiskReviewRecord.__table__.columns.keys())

    assert SupplierRecord.__tablename__ == "b_suppliers"
    assert SupplierRiskReviewRecord.__tablename__ == "b_supplier_risk_reviews"
    assert {
        "supplier_id",
        "org_id",
        "legal_name",
        "status",
        "qualification_status",
        "category_ids",
        "risk_level",
        "is_frozen",
        "version",
        "updated_at",
    }.issubset(supplier_columns)
    assert {
        "review_id",
        "supplier_id",
        "conclusion",
        "note",
        "reviewed_by",
        "created_at",
    }.issubset(review_columns)


def test_supplier_orm_tables_keep_query_indexes() -> None:
    supplier_indexes = {index.name for index in SupplierRecord.__table__.indexes}
    review_indexes = {index.name for index in SupplierRiskReviewRecord.__table__.indexes}

    assert "ix_b_suppliers_org_risk" in supplier_indexes
    assert "ix_b_suppliers_org_status" in supplier_indexes
    assert "ix_b_supplier_risk_reviews_supplier_created" in review_indexes
