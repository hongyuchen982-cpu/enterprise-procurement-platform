from app.modules.sourcing.models import SourcingProjectRecord


def test_sourcing_orm_table_has_expected_name_and_columns() -> None:
    columns = set(SourcingProjectRecord.__table__.columns.keys())

    assert SourcingProjectRecord.__tablename__ == "b_sourcing_projects"
    assert {
        "sourcing_project_id",
        "org_id",
        "procurement_request_id",
        "procurement_request_version",
        "title",
        "category_id",
        "candidate_supplier_ids",
        "created_by",
        "status",
        "version",
        "created_at",
        "updated_at",
        "cancellation_reason",
    }.issubset(columns)


def test_sourcing_orm_table_keeps_query_indexes() -> None:
    indexes = {index.name for index in SourcingProjectRecord.__table__.indexes}

    assert "ix_b_sourcing_projects_org_status" in indexes
    assert "ix_b_sourcing_projects_status_updated" in indexes
    assert "ix_b_sourcing_projects_procurement_request" in indexes
