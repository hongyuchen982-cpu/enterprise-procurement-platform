from datetime import UTC, datetime

from app.contracts.agent import AgentTaskStatus, ConfirmationStatus
from app.contracts.rag import KnowledgeDocumentStatus
from app.contracts.reporting import (
    ActionItemPriority,
    OperationsReport,
    PlatformCapability,
    ReportMetric,
    ReportNextAction,
    SupplierRiskHotspot,
    WorkbenchActionItem,
)
from app.contracts.sourcing import SourcingStatus
from app.contracts.supplier import RiskLevel, SupplierStatus
from app.modules.agents.facade import list_agent_tasks, list_confirmation_requests
from app.modules.rag.facade import list_knowledge_documents
from app.modules.risk.facade import list_supplier_risk_assessments
from app.modules.sourcing.facade import list_sourcing_projects
from app.modules.suppliers.facade import list_supplier_summaries
from app.modules.tools.facade import list_tool_definitions


def _metric(key: str, label: str, value: int, description: str) -> ReportMetric:
    return ReportMetric(key=key, label=label, value=value, description=description)


def _action(
    key: str,
    label: str,
    description: str,
    target_module: str,
) -> ReportNextAction:
    return ReportNextAction(
        key=key,
        label=label,
        description=description,
        target_module=target_module,
    )


def _platform_capabilities() -> list[PlatformCapability]:
    return [
        PlatformCapability(
            key="identity-access",
            label="身份与权限",
            description="A 成员提供认证、成员上下文和权限评估，B 模块后续可接入真实登录态。",
            status="READY_FOR_INTEGRATION",
            owner_module="identity",
            endpoint="/api/v1/access/evaluate",
        ),
        PlatformCapability(
            key="organization-tree",
            label="组织架构",
            description="组织树可用于限定供应商、寻源项目和主数据的业务归属范围。",
            status="READY_FOR_INTEGRATION",
            owner_module="organizations",
            endpoint="/api/v1/organizations/{organization_id}/tree",
        ),
        PlatformCapability(
            key="master-data",
            label="品类与物料主数据",
            description="品类、单位、物料接口可承接 B 成员供应商品类和寻源候选范围。",
            status="READY_FOR_INTEGRATION",
            owner_module="master_data",
            endpoint="/api/v1/master-data",
        ),
    ]


def _priority_rank(priority: ActionItemPriority) -> int:
    return {
        ActionItemPriority.CRITICAL: 0,
        ActionItemPriority.HIGH: 1,
        ActionItemPriority.MEDIUM: 2,
        ActionItemPriority.LOW: 3,
    }[priority]


def get_operations_report() -> OperationsReport:
    suppliers = list_supplier_summaries()
    risk_assessments = list_supplier_risk_assessments()
    sourcing_projects = list_sourcing_projects()
    knowledge_documents = list_knowledge_documents()
    tools = list_tool_definitions()
    pending_confirmations = list_confirmation_requests(
        confirmation_status=ConfirmationStatus.PENDING
    )
    queued_agent_tasks = list_agent_tasks(task_status=AgentTaskStatus.QUEUED)

    high_risk_count = sum(
        1 for supplier in suppliers if supplier.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
    )
    active_supplier_count = sum(
        1 for supplier in suppliers if supplier.status == SupplierStatus.ACTIVE
    )
    active_sourcing_count = sum(
        1 for project in sourcing_projects if project.status == SourcingStatus.ACTIVE
    )
    indexed_document_count = sum(
        1 for document in knowledge_documents if document.status == KnowledgeDocumentStatus.INDEXED
    )
    enabled_tool_count = sum(1 for tool in tools if tool.enabled)

    metrics = [
        _metric("suppliers.total", "供应商总数", len(suppliers), "来自供应商主数据快照。"),
        _metric("suppliers.active", "活跃供应商", active_supplier_count, "状态为 ACTIVE。"),
        _metric("suppliers.high_risk", "高风险供应商", high_risk_count, "HIGH 或 CRITICAL。"),
        _metric("sourcing.active", "进行中寻源", active_sourcing_count, "状态为 ACTIVE。"),
        _metric(
            "agent.pending_confirmations",
            "待确认动作",
            len(pending_confirmations),
            "等待人工确认的 Agent 高风险动作。",
        ),
        _metric(
            "agent.queued_tasks",
            "排队任务",
            len(queued_agent_tasks),
            "状态为 QUEUED 的 Agent 任务。",
        ),
        _metric(
            "rag.indexed_documents",
            "已索引文档",
            indexed_document_count,
            "可参与 RAG 检索的知识文档。",
        ),
        _metric("tools.enabled", "启用工具", enabled_tool_count, "Agent 可调用工具数量。"),
    ]

    top_risk_suppliers = [
        SupplierRiskHotspot(
            supplier_id=assessment.supplier_id,
            supplier_name=assessment.supplier_name,
            score=assessment.score,
            risk_level=assessment.risk_level,
            recommended_action=assessment.recommended_action,
        )
        for assessment in risk_assessments[:3]
    ]

    next_actions: list[ReportNextAction] = []
    if high_risk_count:
        next_actions.append(
            _action(
                "review-high-risk-suppliers",
                "处理高风险供应商",
                "优先打开风险最高的供应商，查看评分原因并提交复核意见。",
                "suppliers",
            )
        )
    if pending_confirmations:
        next_actions.append(
            _action(
                "clear-agent-confirmations",
                "清理 Agent 待确认动作",
                "查看等待人工确认的高风险动作，决定通过或驳回。",
                "confirmations",
            )
        )
    if indexed_document_count < len(knowledge_documents):
        next_actions.append(
            _action(
                "index-knowledge-documents",
                "推进知识文档索引",
                "处理未索引的知识文档，提升 RAG 检索覆盖。",
                "rag",
            )
        )
    if not next_actions:
        next_actions.append(
            _action(
                "keep-data-fresh",
                "维护业务数据新鲜度",
                "当前关键运营指标稳定，建议继续补充真实业务数据。",
                "overview",
            )
        )

    return OperationsReport(
        generated_at=datetime.now(UTC),
        metrics=metrics,
        platform_capabilities=_platform_capabilities(),
        top_risk_suppliers=top_risk_suppliers,
        next_actions=next_actions,
    )


def get_workbench_action_items(limit: int | None = None) -> list[WorkbenchActionItem]:
    risk_assessments = list_supplier_risk_assessments()
    pending_confirmations = list_confirmation_requests(
        confirmation_status=ConfirmationStatus.PENDING
    )
    queued_agent_tasks = list_agent_tasks(task_status=AgentTaskStatus.QUEUED)
    knowledge_documents = list_knowledge_documents()

    items: list[WorkbenchActionItem] = []
    for assessment in risk_assessments:
        if assessment.risk_level not in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            continue
        priority = (
            ActionItemPriority.CRITICAL
            if assessment.risk_level == RiskLevel.CRITICAL
            else ActionItemPriority.HIGH
        )
        items.append(
            WorkbenchActionItem(
                item_id=f"supplier-risk:{assessment.supplier_id}",
                item_type="SUPPLIER_RISK",
                title=f"复核供应商风险：{assessment.supplier_name}",
                description=assessment.summary,
                priority=priority,
                target_module="suppliers",
                target_id=str(assessment.supplier_id),
                status_label=assessment.recommended_action,
                created_at=assessment.updated_at,
            )
        )

    for confirmation in pending_confirmations:
        items.append(
            WorkbenchActionItem(
                item_id=f"confirmation:{confirmation.confirmation_id}",
                item_type="AGENT_CONFIRMATION",
                title="处理 Agent 人工确认",
                description=confirmation.proposed_action,
                priority=ActionItemPriority.HIGH,
                target_module="confirmations",
                target_id=str(confirmation.confirmation_id),
                status_label=confirmation.status,
                created_at=confirmation.expires_at,
                due_at=confirmation.expires_at,
            )
        )

    for task in queued_agent_tasks:
        items.append(
            WorkbenchActionItem(
                item_id=f"agent-task:{task.task_id}",
                item_type="AGENT_TASK",
                title=f"推进 Agent 任务：{task.agent_type}",
                description=task.goal,
                priority=ActionItemPriority.MEDIUM,
                target_module="agents",
                target_id=str(task.task_id),
                status_label=task.status,
                created_at=task.created_at,
            )
        )

    for document in knowledge_documents:
        if document.status in {KnowledgeDocumentStatus.INDEXED, KnowledgeDocumentStatus.ARCHIVED}:
            continue
        priority = (
            ActionItemPriority.HIGH
            if document.status == KnowledgeDocumentStatus.FAILED
            else ActionItemPriority.LOW
        )
        items.append(
            WorkbenchActionItem(
                item_id=f"knowledge-document:{document.document_id}",
                item_type="KNOWLEDGE_DOCUMENT",
                title=f"处理知识文档：{document.title}",
                description=f"{document.owner_module} 模块文档当前状态为 {document.status}。",
                priority=priority,
                target_module="rag",
                target_id=str(document.document_id),
                status_label=document.status,
                created_at=document.updated_at,
            )
        )

    sorted_items = sorted(
        items,
        key=lambda item: (_priority_rank(item.priority), item.created_at),
    )
    if limit is not None:
        return sorted_items[:limit]
    return sorted_items
