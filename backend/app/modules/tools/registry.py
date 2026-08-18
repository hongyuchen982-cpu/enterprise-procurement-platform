from app.contracts.agent import RiskLevel, ToolDefinition

_TOOLS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="supplier.get_snapshot",
        version="1.0.0",
        owner_module="suppliers",
        input_schema={
            "type": "object",
            "required": ["supplier_id"],
            "properties": {"supplier_id": {"type": "string", "format": "uuid"}},
        },
        output_schema={"$ref": "SupplierSnapshot"},
        required_permissions=["supplier:read"],
        risk_level=RiskLevel.L0,
        idempotency_required=False,
        timeout_seconds=5,
    ),
    ToolDefinition(
        name="sourcing.create_project",
        version="1.0.0",
        owner_module="sourcing",
        input_schema={
            "type": "object",
            "required": ["procurement_request_id", "procurement_request_version"],
            "properties": {
                "procurement_request_id": {"type": "string", "format": "uuid"},
                "procurement_request_version": {"type": "integer", "minimum": 1},
            },
        },
        output_schema={"$ref": "SourcingProjectSnapshot"},
        required_permissions=["sourcing:create"],
        risk_level=RiskLevel.L2,
        idempotency_required=True,
        timeout_seconds=30,
    ),
)


def list_tool_definitions() -> list[ToolDefinition]:
    return list(_TOOLS)
