from app.contracts.agent import ToolDefinition
from app.modules.tools.registry import list_tool_definitions as registry_list_tool_definitions


def list_tool_definitions() -> list[ToolDefinition]:
    return registry_list_tool_definitions()
