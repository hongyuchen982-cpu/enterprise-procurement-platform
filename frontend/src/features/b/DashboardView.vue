<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

import { apiClient } from '../../shared/api/client'

interface ApiEnvelope<T> {
  data: T
}

interface SupplierSummary {
  supplier_id: string
  legal_name: string
  status: SupplierStatus
  qualification_status: QualificationStatus
  risk_level: SupplierRiskLevel
  is_frozen: boolean
  updated_at: string
}

interface SupplierSnapshot extends SupplierSummary {
  org_id: string
  category_ids: string[]
  version: number
}

interface ToolDefinition {
  name: string
  version: string
  owner_module: string
  input_schema: Record<string, unknown>
  output_schema: Record<string, unknown>
  required_permissions: string[]
  risk_level: ToolRiskLevel
  idempotency_required: boolean
  timeout_seconds: number
  enabled: boolean
}

interface BusinessObjectRef {
  object_type: string
  object_id: string
  version?: number
}

interface AgentTask {
  task_id: string
  agent_type: string
  org_id: string
  requested_by: string
  goal: string
  subject_refs: BusinessObjectRef[]
  status: AgentTaskStatus
  trace_id: string
  created_at: string
  updated_at: string
  error_code?: string | null
}

interface AgentTaskEvent {
  event_id: string
  task_id: string
  event_type: string
  from_status?: AgentTaskStatus | null
  to_status: AgentTaskStatus
  message: string
  created_at: string
}

interface AgentTaskAction {
  label: string
  status: AgentTaskStatus
  errorCode?: string
}

interface ConfirmationRequest {
  confirmation_id: string
  task_id: string
  tool_call_id: string
  risk_level: ToolRiskLevel
  proposed_action: string
  target_refs: BusinessObjectRef[]
  target_versions: Record<string, number>
  input_digest: string
  required_permission: string
  status: ConfirmationStatus
  expires_at: string
  confirmed_by?: string | null
  confirmed_at?: string | null
  rejection_reason?: string | null
}

interface SourcingProject {
  sourcing_project_id: string
  org_id: string
  procurement_request_id: string
  procurement_request_version: number
  title: string
  category_id: string
  candidate_supplier_ids: string[]
  created_by: string
  status: SourcingStatus
  version: number
  created_at: string
  updated_at: string
}

interface KnowledgeDocument {
  document_id: string
  org_id: string
  title: string
  owner_module: string
  source_type: string
  content_digest: string
  status: KnowledgeDocumentStatus
  chunk_count: number
  tags: string[]
  created_by: string
  indexed_at?: string | null
  version: number
  created_at: string
  updated_at: string
}

interface RagSearchMatch {
  document_id: string
  title: string
  owner_module: string
  score: number
  snippet: string
  status: KnowledgeDocumentStatus
  updated_at: string
}

interface RagSearchResponse {
  query: string
  matches: RagSearchMatch[]
}

interface RiskFactor {
  code: string
  label: string
  impact_score: number
}

interface SupplierRiskAssessment {
  assessment_id: string
  supplier_id: string
  org_id: string
  supplier_name: string
  score: number
  risk_level: SupplierRiskLevel
  recommended_action: SupplierRiskAction
  factors: RiskFactor[]
  summary: string
  assessed_by: string
  created_at: string
  updated_at: string
}

interface ReportMetric {
  key: string
  label: string
  value: number
  description: string
}

interface SupplierRiskHotspot {
  supplier_id: string
  supplier_name: string
  score: number
  risk_level: SupplierRiskLevel
  recommended_action: SupplierRiskAction
}

interface ReportNextAction {
  key: string
  label: string
  description: string
  target_module: 'suppliers' | 'confirmations' | 'rag' | 'overview'
}

interface PlatformCapability {
  key: string
  label: string
  description: string
  status: string
  owner_module: string
  endpoint: string
}

interface OperationsReport {
  generated_at: string
  metrics: ReportMetric[]
  platform_capabilities: PlatformCapability[]
  top_risk_suppliers: SupplierRiskHotspot[]
  next_actions: ReportNextAction[]
}

interface WorkbenchActionItem {
  item_id: string
  item_type: string
  title: string
  description: string
  priority: ActionItemPriority
  target_module: 'suppliers' | 'confirmations' | 'agents' | 'rag'
  target_id: string
  status_label: string
  created_at: string
  due_at?: string | null
}

type AgentTaskStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'WAITING_CONFIRMATION'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'HANDOFF'
type ConfirmationStatus =
  | 'PENDING'
  | 'CONFIRMED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'INVALIDATED'
type SourcingStatus = 'DRAFT' | 'ACTIVE' | 'AWARDED' | 'CLOSED' | 'CANCELLED'
type KnowledgeDocumentStatus = 'UPLOADED' | 'INDEXING' | 'INDEXED' | 'FAILED' | 'ARCHIVED'
type SupplierRiskAction = 'APPROVE' | 'MONITOR' | 'ESCALATE' | 'FREEZE'
type QualificationStatus = 'INCOMPLETE' | 'REVIEWING' | 'QUALIFIED' | 'EXPIRED' | 'REJECTED'
type RiskReviewConclusion = 'ACCEPTABLE' | 'MONITOR' | 'ESCALATE' | 'FREEZE_RECOMMENDED'
type SupplierRiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
type SupplierStatus = 'DRAFT' | 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'BLOCKED' | 'EXITED'
type TagType = 'primary' | 'success' | 'info' | 'warning' | 'danger'
type ToolRiskLevel = 'L0' | 'L1' | 'L2' | 'L3'
type ActionItemPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

interface SupplierRiskReview {
  review_id: string
  supplier_id: string
  conclusion: RiskReviewConclusion
  note: string
  reviewed_by: string
  created_at: string
}

const loading = ref(true)
const detailLoading = ref(false)
const reviewSubmitting = ref(false)
const agentTaskSubmitting = ref(false)
const quickScenarioSubmitting = ref(false)
const sourcingSubmitting = ref(false)
const ragDocumentSubmitting = ref(false)
const ragSearchLoading = ref(false)
const riskAssessmentRefreshing = ref(false)
const taskDetailLoading = ref(false)
const confirmationDetailLoading = ref(false)
const confirmationDecisionSubmittingId = ref<string | null>(null)
const error = ref<string | null>(null)
const supplierKeyword = ref('')
const riskFilter = ref<SupplierRiskLevel | 'ALL' | 'HIGH_OR_CRITICAL'>('ALL')
const supplierStatusFilter = ref<SupplierStatus | 'ALL'>('ALL')
const taskStatusFilter = ref<AgentTaskStatus | 'ALL'>('ALL')
const drawerVisible = ref(false)
const riskReviewVisible = ref(false)
const taskDetailVisible = ref(false)
const confirmationDetailVisible = ref(false)
const toolDetailVisible = ref(false)
const ragDocumentDialogVisible = ref(false)
const selectedSupplier = ref<SupplierSnapshot | null>(null)
const selectedAgentTask = ref<AgentTask | null>(null)
const selectedConfirmation = ref<ConfirmationRequest | null>(null)
const selectedTool = ref<ToolDefinition | null>(null)
const selectedRiskAssessment = ref<SupplierRiskAssessment | null>(null)
const operationsReport = ref<OperationsReport | null>(null)
const actionItems = ref<WorkbenchActionItem[]>([])
const selectedAgentTaskEvents = ref<AgentTaskEvent[]>([])
const selectedAgentTaskConfirmations = ref<ConfirmationRequest[]>([])
const riskReviews = ref<SupplierRiskReview[]>([])
const recentAgentTasks = ref<AgentTask[]>([])
const supplierAgentTasks = ref<AgentTask[]>([])
const sourcingProjects = ref<SourcingProject[]>([])
const knowledgeDocuments = ref<KnowledgeDocument[]>([])
const supplierRiskAssessments = ref<SupplierRiskAssessment[]>([])
const ragSearchQuery = ref('风险 供应商')
const ragSearchResults = ref<RagSearchMatch[]>([])
const confirmationRequests = ref<ConfirmationRequest[]>([])
const suppliers = ref<SupplierSummary[]>([])
const tools = ref<ToolDefinition[]>([])
const riskReviewForm = ref<{
  conclusion: RiskReviewConclusion
  note: string
}>({
  conclusion: 'MONITOR',
  note: '',
})
const ragDocumentForm = ref({
  title: '',
  owner_module: 'suppliers',
  content: '',
  tags: 'supplier,risk',
})

const enabledToolCount = computed(() => tools.value.filter((tool) => tool.enabled).length)
const activeSupplierCount = computed(
  () => suppliers.value.filter((supplier) => supplier.status === 'ACTIVE').length,
)
const highRiskSupplierCount = computed(
  () => suppliers.value.filter((supplier) => ['HIGH', 'CRITICAL'].includes(supplier.risk_level)).length,
)
const activeSourcingProjectCount = computed(
  () => sourcingProjects.value.filter((project) => project.status === 'ACTIVE').length,
)
const indexedKnowledgeDocumentCount = computed(
  () => knowledgeDocuments.value.filter((document) => document.status === 'INDEXED').length,
)
const queuedAgentTaskCount = computed(
  () => recentAgentTasks.value.filter((task) => task.status === 'QUEUED').length,
)
const pendingConfirmationCount = computed(
  () => confirmationRequests.value.filter((request) => request.status === 'PENDING').length,
)
const selectedCategoryCount = computed(() => selectedSupplier.value?.category_ids.length ?? 0)
const latestRiskReview = computed(() => riskReviews.value[0] ?? null)
const selectedGovernanceState = computed(() => {
  const supplier = selectedSupplier.value
  if (!supplier) return '-'
  if (supplier.is_frozen) return '已冻结'
  if (['HIGH', 'CRITICAL'].includes(supplier.risk_level)) return '需要复核'
  if (supplier.qualification_status === 'REVIEWING') return '资质审核中'
  if (supplier.status === 'ACTIVE' && supplier.qualification_status === 'QUALIFIED') return '可协作'
  return '待完善'
})
const supplierFilterSummary = computed(() => {
  const summary: string[] = []
  const keyword = supplierKeyword.value.trim()
  if (keyword) {
    summary.push(`名称包含「${keyword}」`)
  }
  if (riskFilter.value !== 'ALL') {
    summary.push(`风险：${riskOptions.find((option) => option.value === riskFilter.value)?.label ?? riskFilter.value}`)
  }
  if (supplierStatusFilter.value !== 'ALL') {
    summary.push(
      `状态：${supplierStatusOptions.find((option) => option.value === supplierStatusFilter.value)?.label ?? supplierStatusFilter.value}`,
    )
  }
  return summary
})

const riskOptions: Array<{ label: string; value: SupplierRiskLevel | 'ALL' | 'HIGH_OR_CRITICAL' }> = [
  { label: '全部风险', value: 'ALL' },
  { label: '低风险', value: 'LOW' },
  { label: '中风险', value: 'MEDIUM' },
  { label: '高危风险', value: 'HIGH_OR_CRITICAL' },
  { label: '高风险', value: 'HIGH' },
  { label: '严重风险', value: 'CRITICAL' },
]
const supplierStatusOptions: Array<{ label: string; value: SupplierStatus | 'ALL' }> = [
  { label: '全部状态', value: 'ALL' },
  { label: '草稿', value: 'DRAFT' },
  { label: '待处理', value: 'PENDING' },
  { label: '活跃', value: 'ACTIVE' },
  { label: '暂停', value: 'SUSPENDED' },
  { label: '阻断', value: 'BLOCKED' },
  { label: '退出', value: 'EXITED' },
]
const conclusionOptions: Array<{ label: string; value: RiskReviewConclusion }> = [
  { label: '风险可接受', value: 'ACCEPTABLE' },
  { label: '持续观察', value: 'MONITOR' },
  { label: '升级处理', value: 'ESCALATE' },
  { label: '建议冻结', value: 'FREEZE_RECOMMENDED' },
]
const taskStatusOptions: Array<{ label: string; value: AgentTaskStatus | 'ALL' }> = [
  { label: '全部状态', value: 'ALL' },
  { label: '排队中', value: 'QUEUED' },
  { label: '执行中', value: 'RUNNING' },
  { label: '等待确认', value: 'WAITING_CONFIRMATION' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '已失败', value: 'FAILED' },
  { label: '已取消', value: 'CANCELLED' },
  { label: '已移交', value: 'HANDOFF' },
]

function formatTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

function openToolDetail(tool: ToolDefinition): void {
  selectedTool.value = tool
  toolDetailVisible.value = true
}

function riskTagType(level: SupplierRiskLevel | ToolRiskLevel): TagType {
  const types: Record<SupplierRiskLevel | ToolRiskLevel, TagType> = {
    LOW: 'success',
    MEDIUM: 'warning',
    HIGH: 'danger',
    CRITICAL: 'danger',
    L0: 'info',
    L1: 'success',
    L2: 'warning',
    L3: 'danger',
  }
  return types[level]
}

function statusTagType(status: SupplierStatus): TagType {
  const types: Record<SupplierStatus, TagType> = {
    DRAFT: 'info',
    PENDING: 'warning',
    ACTIVE: 'success',
    SUSPENDED: 'danger',
    BLOCKED: 'danger',
    EXITED: 'info',
  }
  return types[status]
}

function qualificationTagType(status: QualificationStatus): TagType {
  const types: Record<QualificationStatus, TagType> = {
    INCOMPLETE: 'info',
    REVIEWING: 'warning',
    QUALIFIED: 'success',
    EXPIRED: 'danger',
    REJECTED: 'danger',
  }
  return types[status]
}

function conclusionLabel(conclusion: RiskReviewConclusion): string {
  return conclusionOptions.find((option) => option.value === conclusion)?.label ?? conclusion
}

function conclusionTagType(conclusion: RiskReviewConclusion): TagType {
  const types: Record<RiskReviewConclusion, TagType> = {
    ACCEPTABLE: 'success',
    MONITOR: 'warning',
    ESCALATE: 'danger',
    FREEZE_RECOMMENDED: 'danger',
  }
  return types[conclusion]
}

function agentTaskStatusTagType(status: AgentTaskStatus): TagType {
  const types: Record<AgentTaskStatus, TagType> = {
    QUEUED: 'info',
    RUNNING: 'primary',
    WAITING_CONFIRMATION: 'warning',
    COMPLETED: 'success',
    FAILED: 'danger',
    CANCELLED: 'info',
    HANDOFF: 'warning',
  }
  return types[status]
}

function confirmationStatusTagType(status: ConfirmationStatus): TagType {
  const types: Record<ConfirmationStatus, TagType> = {
    PENDING: 'warning',
    CONFIRMED: 'success',
    REJECTED: 'danger',
    EXPIRED: 'info',
    INVALIDATED: 'info',
  }
  return types[status]
}

function sourcingStatusTagType(status: SourcingStatus): TagType {
  const types: Record<SourcingStatus, TagType> = {
    DRAFT: 'info',
    ACTIVE: 'primary',
    AWARDED: 'success',
    CLOSED: 'info',
    CANCELLED: 'danger',
  }
  return types[status]
}

function knowledgeDocumentStatusTagType(status: KnowledgeDocumentStatus): TagType {
  const types: Record<KnowledgeDocumentStatus, TagType> = {
    UPLOADED: 'info',
    INDEXING: 'primary',
    INDEXED: 'success',
    FAILED: 'danger',
    ARCHIVED: 'info',
  }
  return types[status]
}

function supplierRiskActionTagType(action: SupplierRiskAction): TagType {
  const types: Record<SupplierRiskAction, TagType> = {
    APPROVE: 'success',
    MONITOR: 'warning',
    ESCALATE: 'danger',
    FREEZE: 'danger',
  }
  return types[action]
}

function actionPriorityTagType(priority: ActionItemPriority): TagType {
  const types: Record<ActionItemPriority, TagType> = {
    LOW: 'info',
    MEDIUM: 'warning',
    HIGH: 'danger',
    CRITICAL: 'danger',
  }
  return types[priority]
}

function riskFactorCodes(assessment: SupplierRiskAssessment): string {
  return assessment.factors.map((factor) => factor.code).join(', ')
}

function reportMetricValue(key: string, fallback: number): number {
  return operationsReport.value?.metrics.find((metric) => metric.key === key)?.value ?? fallback
}

function agentTaskEventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    TASK_CREATED: '任务创建',
    STATUS_CHANGED: '状态变更',
    CONFIRMATION_CONFIRMED: '人工确认通过',
    CONFIRMATION_REJECTED: '人工确认驳回',
  }
  return labels[eventType] ?? eventType
}

function availableAgentTaskActions(task: AgentTask | null): AgentTaskAction[] {
  if (!task) return []

  const actions: Record<AgentTaskStatus, AgentTaskAction[]> = {
    QUEUED: [
      { label: '标记执行中', status: 'RUNNING' },
      { label: '取消任务', status: 'CANCELLED' },
    ],
    RUNNING: [
      { label: '等待确认', status: 'WAITING_CONFIRMATION' },
      { label: '标记完成', status: 'COMPLETED' },
      { label: '标记失败', status: 'FAILED', errorCode: 'DEMO_TOOL_TIMEOUT' },
      { label: '移交处理', status: 'HANDOFF' },
      { label: '取消任务', status: 'CANCELLED' },
    ],
    WAITING_CONFIRMATION: [
      { label: '继续执行', status: 'RUNNING' },
      { label: '移交处理', status: 'HANDOFF' },
      { label: '取消任务', status: 'CANCELLED' },
    ],
    COMPLETED: [],
    FAILED: [],
    CANCELLED: [],
    HANDOFF: [],
  }
  return actions[task.status]
}

function agentTaskActionType(action: AgentTaskAction): TagType {
  if (action.status === 'COMPLETED') return 'success'
  if (['FAILED', 'CANCELLED'].includes(action.status)) return 'danger'
  if (['WAITING_CONFIRMATION', 'HANDOFF'].includes(action.status)) return 'warning'
  return 'primary'
}

function availableSourcingStatusActions(project: SourcingProject): SourcingStatus[] {
  const actions: Record<SourcingStatus, SourcingStatus[]> = {
    DRAFT: ['ACTIVE', 'CANCELLED'],
    ACTIVE: ['AWARDED', 'CLOSED', 'CANCELLED'],
    AWARDED: ['CLOSED'],
    CLOSED: [],
    CANCELLED: [],
  }
  return actions[project.status]
}

function availableKnowledgeDocumentStatusActions(
  document: KnowledgeDocument,
): KnowledgeDocumentStatus[] {
  const actions: Record<KnowledgeDocumentStatus, KnowledgeDocumentStatus[]> = {
    UPLOADED: ['INDEXING', 'ARCHIVED'],
    INDEXING: ['INDEXED', 'FAILED'],
    INDEXED: ['INDEXING', 'ARCHIVED'],
    FAILED: ['INDEXING', 'ARCHIVED'],
    ARCHIVED: [],
  }
  return actions[document.status]
}

function supplierQueryParams(): Record<string, string> {
  const params: Record<string, string> = {}
  const keyword = supplierKeyword.value.trim()
  if (keyword.length > 0) {
    params.keyword = keyword
  }
  if (riskFilter.value === 'HIGH_OR_CRITICAL') {
    params.high_risk_only = 'true'
  } else if (riskFilter.value !== 'ALL') {
    params.risk_level = riskFilter.value
  }
  if (supplierStatusFilter.value !== 'ALL') {
    params.status = supplierStatusFilter.value
  }
  return params
}

function taskQueryParams(): Record<string, string> {
  const params: Record<string, string> = {
    limit: '50',
  }

  if (taskStatusFilter.value === 'ALL') {
    return params
  }

  params.task_status = taskStatusFilter.value
  return params
}

async function loadSuppliers(): Promise<void> {
  error.value = null

  try {
    const supplierResponse = await apiClient.get<ApiEnvelope<SupplierSummary[]>>('/suppliers', {
      params: supplierQueryParams(),
    })
    suppliers.value = supplierResponse.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载供应商列表失败'
  }
}

async function loadRecentAgentTasks(): Promise<void> {
  error.value = null

  try {
    const taskResponse = await apiClient.get<ApiEnvelope<AgentTask[]>>('/agent/tasks', {
      params: taskQueryParams(),
    })
    recentAgentTasks.value = taskResponse.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载 Agent 任务队列失败'
  }
}

async function loadConfirmationRequests(): Promise<void> {
  error.value = null

  try {
    const response = await apiClient.get<ApiEnvelope<ConfirmationRequest[]>>(
      '/agent/confirmations',
      {
        params: {
          confirmation_status: 'PENDING',
          limit: 50,
        },
      },
    )
    confirmationRequests.value = response.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载人工确认队列失败'
  }
}

async function loadSourcingProjects(): Promise<void> {
  error.value = null

  try {
    const response = await apiClient.get<ApiEnvelope<SourcingProject[]>>('/sourcing/projects')
    sourcingProjects.value = response.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载寻源项目失败'
  }
}

async function loadKnowledgeDocuments(): Promise<void> {
  error.value = null

  try {
    const response = await apiClient.get<ApiEnvelope<KnowledgeDocument[]>>('/rag/documents')
    knowledgeDocuments.value = response.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载知识库文档失败'
  }
}

async function loadSupplierRiskAssessments(): Promise<void> {
  error.value = null

  try {
    const response = await apiClient.get<ApiEnvelope<SupplierRiskAssessment[]>>(
      '/risk/supplier-assessments',
    )
    supplierRiskAssessments.value = response.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载供应商风险评分失败'
  }
}

async function loadOperationsReport(): Promise<void> {
  error.value = null

  try {
    const response = await apiClient.get<ApiEnvelope<OperationsReport>>('/reporting/operations')
    operationsReport.value = response.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载运营总览失败'
  }
}

async function loadActionItems(): Promise<void> {
  error.value = null

  try {
    const response = await apiClient.get<ApiEnvelope<WorkbenchActionItem[]>>(
      '/reporting/action-items',
      {
        params: {
          limit: 20,
        },
      },
    )
    actionItems.value = response.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载行动中心失败'
  }
}

function scrollToSection(sectionId: string): void {
  document.getElementById(sectionId)?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

async function handleReportAction(action: ReportNextAction): Promise<void> {
  if (action.target_module === 'suppliers') {
    const topRiskSupplier = operationsReport.value?.top_risk_suppliers[0]
    if (topRiskSupplier) {
      await openSupplierDetail(topRiskSupplier.supplier_id)
      return
    }

    await resetSupplierFilters()
    scrollToSection('supplier-ledger')
    return
  }

  if (action.target_module === 'confirmations') {
    await loadConfirmationRequests()
    scrollToSection('confirmation-queue')
    return
  }

  if (action.target_module === 'rag') {
    await loadKnowledgeDocuments()
    scrollToSection('rag-workbench')
    return
  }

  scrollToSection('operations-report')
}

async function handleActionItem(item: WorkbenchActionItem): Promise<void> {
  if (item.target_module === 'suppliers') {
    await openSupplierDetail(item.target_id)
    return
  }

  if (item.target_module === 'confirmations') {
    await openConfirmationDetail(item.target_id)
    return
  }

  if (item.target_module === 'agents') {
    await openAgentTaskDetail(item.target_id)
    return
  }

  if (item.target_module === 'rag') {
    await loadKnowledgeDocuments()
    scrollToSection('rag-workbench')
  }
}

async function handleMetricDrilldown(metricKey: string): Promise<void> {
  if (metricKey === 'suppliers.total') {
    await resetSupplierFilters()
    scrollToSection('supplier-ledger')
    return
  }

  if (metricKey === 'suppliers.active') {
    supplierKeyword.value = ''
    riskFilter.value = 'ALL'
    supplierStatusFilter.value = 'ACTIVE'
    await applySupplierFilters()
    scrollToSection('supplier-ledger')
    return
  }

  if (metricKey === 'suppliers.high_risk') {
    supplierKeyword.value = ''
    riskFilter.value = 'HIGH_OR_CRITICAL'
    supplierStatusFilter.value = 'ALL'
    await applySupplierFilters()
    scrollToSection('supplier-ledger')
    return
  }

  if (metricKey === 'sourcing.active') {
    await loadSourcingProjects()
    scrollToSection('sourcing-workbench')
    return
  }

  if (metricKey === 'agent.pending_confirmations') {
    await loadConfirmationRequests()
    scrollToSection('confirmation-queue')
    return
  }

  if (metricKey === 'agent.queued_tasks') {
    taskStatusFilter.value = 'QUEUED'
    await loadRecentAgentTasks()
    scrollToSection('agent-task-queue')
    return
  }

  if (metricKey === 'rag.indexed_documents') {
    await loadKnowledgeDocuments()
    scrollToSection('rag-workbench')
    return
  }

  if (metricKey === 'tools.enabled') {
    scrollToSection('tool-registry')
  }
}

async function refreshSupplierRiskAssessment(supplierId: string): Promise<void> {
  riskAssessmentRefreshing.value = true
  try {
    const response = await apiClient.post<ApiEnvelope<SupplierRiskAssessment>>(
      `/risk/supplier-assessments/${supplierId}/refresh`,
      {
        assessed_by: 'Member B Risk Analyst',
      },
    )
    selectedRiskAssessment.value = response.data.data
    supplierRiskAssessments.value = supplierRiskAssessments.value
      .filter((assessment) => assessment.supplier_id !== supplierId)
      .concat(response.data.data)
      .sort((left, right) => right.score - left.score)
    await Promise.all([loadActionItems(), loadOperationsReport()])
    ElMessage.success('风险评分已刷新')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '刷新风险评分失败'
  } finally {
    riskAssessmentRefreshing.value = false
  }
}

async function createKnowledgeDocument(): Promise<void> {
  const content = ragDocumentForm.value.content.trim()
  if (!ragDocumentForm.value.title.trim() || !content) {
    ElMessage.warning('请填写文档标题和内容')
    return
  }

  ragDocumentSubmitting.value = true
  try {
    const response = await apiClient.post<ApiEnvelope<KnowledgeDocument>>('/rag/documents', {
      org_id: '22222222-2222-4222-8222-222222222222',
      title: ragDocumentForm.value.title.trim(),
      owner_module: ragDocumentForm.value.owner_module.trim(),
      source_type: 'TEXT',
      content,
      tags: ragDocumentForm.value.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      created_by: '44444444-4444-4444-8444-444444444444',
    })
    knowledgeDocuments.value = [response.data.data, ...knowledgeDocuments.value]
    ragDocumentDialogVisible.value = false
    ragDocumentForm.value = {
      title: '',
      owner_module: 'suppliers',
      content: '',
      tags: 'supplier,risk',
    }
    await Promise.all([loadActionItems(), loadOperationsReport()])
    ElMessage.success('知识文档已创建')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '创建知识文档失败'
  } finally {
    ragDocumentSubmitting.value = false
  }
}

async function updateKnowledgeDocumentStatus(
  document: KnowledgeDocument,
  status: KnowledgeDocumentStatus,
): Promise<void> {
  try {
    const response = await apiClient.patch<ApiEnvelope<KnowledgeDocument>>(
      `/rag/documents/${document.document_id}/status`,
      { status },
    )
    knowledgeDocuments.value = knowledgeDocuments.value.map((item) =>
      item.document_id === document.document_id ? response.data.data : item,
    )
    await Promise.all([loadActionItems(), loadOperationsReport()])
    ElMessage.success('知识文档状态已更新')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '更新知识文档状态失败'
  }
}

async function searchKnowledge(): Promise<void> {
  const query = ragSearchQuery.value.trim()
  if (!query) {
    ElMessage.warning('请输入检索问题')
    return
  }

  ragSearchLoading.value = true
  try {
    const response = await apiClient.post<ApiEnvelope<RagSearchResponse>>('/rag/search', {
      org_id: '22222222-2222-4222-8222-222222222222',
      query,
      top_k: 5,
    })
    ragSearchResults.value = response.data.data.matches
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '知识库检索失败'
  } finally {
    ragSearchLoading.value = false
  }
}

async function decideConfirmationRequest(
  confirmation: ConfirmationRequest,
  status: 'CONFIRMED' | 'REJECTED',
): Promise<void> {
  confirmationDecisionSubmittingId.value = confirmation.confirmation_id
  try {
    await apiClient.patch<ApiEnvelope<ConfirmationRequest>>(
      `/agent/confirmations/${confirmation.confirmation_id}`,
      {
        status,
        confirmed_by: '44444444-4444-4444-8444-444444444444',
        rejection_reason: status === 'REJECTED' ? 'Demo operator rejected this action.' : null,
      },
    )
    ElMessage.success(status === 'CONFIRMED' ? '确认已通过' : '确认已驳回')
    confirmationDetailVisible.value = false
    selectedConfirmation.value = null
    await Promise.all([
      loadConfirmationRequests(),
      loadRecentAgentTasks(),
      loadActionItems(),
      loadOperationsReport(),
    ])
    if (taskDetailVisible.value && selectedAgentTask.value?.task_id === confirmation.task_id) {
      await openAgentTaskDetail(confirmation.task_id)
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '处理人工确认失败'
  } finally {
    confirmationDecisionSubmittingId.value = null
  }
}

async function openConfirmationDetail(confirmationId: string): Promise<void> {
  confirmationDetailVisible.value = true
  confirmationDetailLoading.value = true
  selectedConfirmation.value = null

  try {
    const response = await apiClient.get<ApiEnvelope<ConfirmationRequest>>(
      `/agent/confirmations/${confirmationId}`,
    )
    selectedConfirmation.value = response.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载人工确认详情失败'
  } finally {
    confirmationDetailLoading.value = false
  }
}

async function loadDashboard(): Promise<void> {
  loading.value = true
  error.value = null

  try {
    const [
      supplierResponse,
      toolResponse,
      taskResponse,
      confirmationResponse,
      sourcingResponse,
      knowledgeResponse,
      riskAssessmentResponse,
      operationsReportResponse,
      actionItemsResponse,
    ] = await Promise.all([
      apiClient.get<ApiEnvelope<SupplierSummary[]>>('/suppliers', {
        params: supplierQueryParams(),
      }),
      apiClient.get<ApiEnvelope<ToolDefinition[]>>('/tools'),
      apiClient.get<ApiEnvelope<AgentTask[]>>('/agent/tasks', {
        params: taskQueryParams(),
      }),
      apiClient.get<ApiEnvelope<ConfirmationRequest[]>>('/agent/confirmations', {
        params: {
          confirmation_status: 'PENDING',
          limit: 50,
        },
      }),
      apiClient.get<ApiEnvelope<SourcingProject[]>>('/sourcing/projects'),
      apiClient.get<ApiEnvelope<KnowledgeDocument[]>>('/rag/documents'),
      apiClient.get<ApiEnvelope<SupplierRiskAssessment[]>>('/risk/supplier-assessments'),
      apiClient.get<ApiEnvelope<OperationsReport>>('/reporting/operations'),
      apiClient.get<ApiEnvelope<WorkbenchActionItem[]>>('/reporting/action-items', {
        params: {
          limit: 20,
        },
      }),
    ])
    suppliers.value = supplierResponse.data.data
    tools.value = toolResponse.data.data
    recentAgentTasks.value = taskResponse.data.data
    confirmationRequests.value = confirmationResponse.data.data
    sourcingProjects.value = sourcingResponse.data.data
    knowledgeDocuments.value = knowledgeResponse.data.data
    supplierRiskAssessments.value = riskAssessmentResponse.data.data
    operationsReport.value = operationsReportResponse.data.data
    actionItems.value = actionItemsResponse.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载 B 工作台失败'
  } finally {
    loading.value = false
  }
}

async function applySupplierFilters(): Promise<void> {
  loading.value = true
  try {
    await loadSuppliers()
  } finally {
    loading.value = false
  }
}

async function resetSupplierFilters(): Promise<void> {
  supplierKeyword.value = ''
  riskFilter.value = 'ALL'
  supplierStatusFilter.value = 'ALL'
  await applySupplierFilters()
}

async function openSupplierDetail(supplierId: string): Promise<void> {
  drawerVisible.value = true
  detailLoading.value = true
  selectedSupplier.value = null
  selectedRiskAssessment.value = null
  riskReviews.value = []
  supplierAgentTasks.value = []

  try {
    const [snapshotResponse, reviewResponse, taskResponse, riskAssessmentResponse] = await Promise.all([
      apiClient.get<ApiEnvelope<SupplierSnapshot>>(`/suppliers/${supplierId}/snapshot`),
      apiClient.get<ApiEnvelope<SupplierRiskReview[]>>(
        `/suppliers/${supplierId}/risk-reviews`,
      ),
      apiClient.get<ApiEnvelope<AgentTask[]>>('/agent/tasks', {
        params: {
          subject_type: 'supplier',
          subject_id: supplierId,
          limit: 50,
        },
      }),
      apiClient.get<ApiEnvelope<SupplierRiskAssessment>>(
        `/risk/supplier-assessments/${supplierId}`,
      ),
    ])
    selectedSupplier.value = snapshotResponse.data.data
    riskReviews.value = reviewResponse.data.data
    supplierAgentTasks.value = taskResponse.data.data
    selectedRiskAssessment.value = riskAssessmentResponse.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载供应商详情失败'
  } finally {
    detailLoading.value = false
  }
}

async function submitAgentTask(agentType: 'sourcing_assistant' | 'supplier_risk_analyzer'): Promise<void> {
  if (!selectedSupplier.value) return

  const goal =
    agentType === 'sourcing_assistant'
      ? `为供应商 ${selectedSupplier.value.legal_name} 发起寻源协同，检查可合作品类和下一步采购动作。`
      : `分析供应商 ${selectedSupplier.value.legal_name} 的风险状态，给出复核建议和需要人工确认的动作。`

  agentTaskSubmitting.value = true
  try {
    const response = await apiClient.post<ApiEnvelope<AgentTask>>('/agent/tasks', {
      agent_type: agentType,
      org_id: selectedSupplier.value.org_id,
      requested_by: '44444444-4444-4444-8444-444444444444',
      goal,
      subject_refs: [
        {
          object_type: 'supplier',
          object_id: selectedSupplier.value.supplier_id,
          version: selectedSupplier.value.version,
        },
      ],
    })
    supplierAgentTasks.value = [response.data.data, ...supplierAgentTasks.value]
    recentAgentTasks.value = [response.data.data, ...recentAgentTasks.value]
    ElMessage.success('Agent 任务已进入队列')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '创建 Agent 任务失败'
  } finally {
    agentTaskSubmitting.value = false
  }
}

async function createPendingConfirmationScenario(): Promise<void> {
  const supplier =
    suppliers.value.find((item) => ['HIGH', 'CRITICAL'].includes(item.risk_level)) ??
    suppliers.value[0]

  if (!supplier) {
    ElMessage.warning('暂无可用于生成 Agent 流程的供应商')
    return
  }

  quickScenarioSubmitting.value = true
  error.value = null

  try {
    const snapshotResponse = await apiClient.get<ApiEnvelope<SupplierSnapshot>>(
      `/suppliers/${supplier.supplier_id}/snapshot`,
    )
    const snapshot = snapshotResponse.data.data
    const createdResponse = await apiClient.post<ApiEnvelope<AgentTask>>('/agent/tasks', {
      agent_type: 'supplier_risk_analyzer',
      org_id: snapshot.org_id,
      requested_by: '44444444-4444-4444-8444-444444444444',
      goal: `对高风险供应商 ${snapshot.legal_name} 执行风险分析，并生成需要人工确认的后续动作。`,
      subject_refs: [
        {
          object_type: 'supplier',
          object_id: snapshot.supplier_id,
          version: snapshot.version,
        },
      ],
    })
    const taskId = createdResponse.data.data.task_id
    await apiClient.patch<ApiEnvelope<AgentTask>>(`/agent/tasks/${taskId}/status`, {
      status: 'RUNNING',
    })
    const waitingResponse = await apiClient.patch<ApiEnvelope<AgentTask>>(
      `/agent/tasks/${taskId}/status`,
      {
        status: 'WAITING_CONFIRMATION',
      },
    )

    taskStatusFilter.value = 'ALL'
    recentAgentTasks.value = [waitingResponse.data.data, ...recentAgentTasks.value]
    await Promise.all([
      loadRecentAgentTasks(),
      loadConfirmationRequests(),
      loadActionItems(),
      loadOperationsReport(),
    ])
    ElMessage.success('已生成待人工确认的 Agent 流程')
    await openAgentTaskDetail(taskId)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '生成 Agent 待确认流程失败'
  } finally {
    quickScenarioSubmitting.value = false
  }
}

async function createSourcingProjectFromSupplier(): Promise<void> {
  if (!selectedSupplier.value) return
  const categoryId = selectedSupplier.value.category_ids[0]
  if (!categoryId) {
    ElMessage.warning('当前供应商没有可用于寻源的品类')
    return
  }

  sourcingSubmitting.value = true
  try {
    const response = await apiClient.post<ApiEnvelope<SourcingProject>>('/sourcing/projects', {
      org_id: selectedSupplier.value.org_id,
      procurement_request_id: crypto.randomUUID(),
      procurement_request_version: 1,
      title: `${selectedSupplier.value.legal_name} 寻源项目`,
      category_id: categoryId,
      candidate_supplier_ids: [selectedSupplier.value.supplier_id],
      created_by: '44444444-4444-4444-8444-444444444444',
    })
    sourcingProjects.value = [response.data.data, ...sourcingProjects.value]
    ElMessage.success('寻源项目已创建')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '创建寻源项目失败'
  } finally {
    sourcingSubmitting.value = false
  }
}

async function updateSourcingProjectStatus(
  project: SourcingProject,
  status: SourcingStatus,
): Promise<void> {
  try {
    const response = await apiClient.patch<ApiEnvelope<SourcingProject>>(
      `/sourcing/projects/${project.sourcing_project_id}/status`,
      { status },
    )
    sourcingProjects.value = sourcingProjects.value.map((item) =>
      item.sourcing_project_id === project.sourcing_project_id ? response.data.data : item,
    )
    ElMessage.success('寻源项目状态已更新')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '更新寻源项目状态失败'
  }
}

async function openAgentTaskDetail(taskId: string): Promise<void> {
  taskDetailVisible.value = true
  taskDetailLoading.value = true
  selectedAgentTask.value = null
  selectedAgentTaskEvents.value = []
  selectedAgentTaskConfirmations.value = []

  try {
    const [taskResponse, eventResponse, confirmationResponse] = await Promise.all([
      apiClient.get<ApiEnvelope<AgentTask>>(`/agent/tasks/${taskId}`),
      apiClient.get<ApiEnvelope<AgentTaskEvent[]>>(`/agent/tasks/${taskId}/events`),
      apiClient.get<ApiEnvelope<ConfirmationRequest[]>>('/agent/confirmations', {
        params: {
          task_id: taskId,
          limit: 50,
        },
      }),
    ])
    selectedAgentTask.value = taskResponse.data.data
    selectedAgentTaskEvents.value = eventResponse.data.data
    selectedAgentTaskConfirmations.value = confirmationResponse.data.data
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '加载 Agent 任务详情失败'
  } finally {
    taskDetailLoading.value = false
  }
}

function replaceAgentTask(task: AgentTask): void {
  const shouldKeepInRecent =
    taskStatusFilter.value === 'ALL' || task.status === taskStatusFilter.value
  recentAgentTasks.value = recentAgentTasks.value
    .map((item) => (item.task_id === task.task_id ? task : item))
    .filter((item) => item.task_id !== task.task_id || shouldKeepInRecent)
  supplierAgentTasks.value = supplierAgentTasks.value.map((item) =>
    item.task_id === task.task_id ? task : item,
  )
}

async function updateSelectedAgentTaskStatus(
  status: AgentTaskStatus,
  errorCode: string | null = null,
): Promise<void> {
  if (!selectedAgentTask.value) return

  const taskId = selectedAgentTask.value.task_id
  taskDetailLoading.value = true
  try {
    const response = await apiClient.patch<ApiEnvelope<AgentTask>>(
      `/agent/tasks/${taskId}/status`,
      {
        status,
        error_code: errorCode,
      },
    )
    const [eventResponse, confirmationResponse] = await Promise.all([
      apiClient.get<ApiEnvelope<AgentTaskEvent[]>>(`/agent/tasks/${taskId}/events`),
      apiClient.get<ApiEnvelope<ConfirmationRequest[]>>('/agent/confirmations', {
        params: {
          task_id: taskId,
          limit: 50,
        },
      }),
    ])
    selectedAgentTask.value = response.data.data
    selectedAgentTaskEvents.value = eventResponse.data.data
    selectedAgentTaskConfirmations.value = confirmationResponse.data.data
    replaceAgentTask(response.data.data)
    if (status === 'WAITING_CONFIRMATION') {
      await loadConfirmationRequests()
    }
    await Promise.all([loadActionItems(), loadOperationsReport()])
    ElMessage.success('任务状态已更新')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '更新任务状态失败'
  } finally {
    taskDetailLoading.value = false
  }
}

function openRiskReviewDialog(): void {
  riskReviewForm.value = {
    conclusion: selectedSupplier.value?.risk_level === 'HIGH' ? 'ESCALATE' : 'MONITOR',
    note: '',
  }
  riskReviewVisible.value = true
}

async function submitRiskReview(): Promise<void> {
  if (!selectedSupplier.value) return
  const note = riskReviewForm.value.note.trim()
  if (note.length === 0) {
    ElMessage.warning('请填写复核备注')
    return
  }

  reviewSubmitting.value = true
  try {
    const response = await apiClient.post<ApiEnvelope<SupplierRiskReview>>(
      `/suppliers/${selectedSupplier.value.supplier_id}/risk-reviews`,
      {
        conclusion: riskReviewForm.value.conclusion,
        note,
        reviewed_by: 'Member B Demo Operator',
      },
    )
    riskReviews.value = [response.data.data, ...riskReviews.value]
    riskReviewVisible.value = false
    ElMessage.success('风险复核已提交')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '提交风险复核失败'
  } finally {
    reviewSubmitting.value = false
  }
}

onMounted(() => {
  void loadDashboard()
})
</script>

<template>
  <section
    v-loading="loading"
    class="b-dashboard"
  >
    <div class="b-dashboard__header">
      <div>
        <p class="eyebrow">
          Member B Workspace
        </p>
        <h1>供应商与智能协同工作台</h1>
        <p>
          当前先管理供应商风险、资质状态和 Agent 可调用工具，后续再接寻源、RAG 和风险分析。
        </p>
      </div>
      <el-button
        type="primary"
        @click="loadDashboard"
      >
        刷新
      </el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="b-dashboard__alert"
    />

    <el-row :gutter="16">
      <el-col
        :xs="24"
        :md="6"
      >
        <button
          type="button"
          class="metric"
          @click="handleMetricDrilldown('suppliers.total')"
        >
          <span class="metric__label">供应商总数</span>
          <strong>{{ reportMetricValue('suppliers.total', suppliers.length) }}</strong>
          <small>来自 /suppliers</small>
        </button>
      </el-col>
      <el-col
        :xs="24"
        :md="6"
      >
        <button
          type="button"
          class="metric"
          @click="handleMetricDrilldown('suppliers.active')"
        >
          <span class="metric__label">活跃供应商</span>
          <strong>{{ reportMetricValue('suppliers.active', activeSupplierCount) }}</strong>
          <small>状态为 ACTIVE</small>
        </button>
      </el-col>
      <el-col
        :xs="24"
        :md="6"
      >
        <button
          type="button"
          class="metric metric--risk"
          @click="handleMetricDrilldown('suppliers.high_risk')"
        >
          <span class="metric__label">高风险供应商</span>
          <strong>{{ reportMetricValue('suppliers.high_risk', highRiskSupplierCount) }}</strong>
          <small>HIGH 或 CRITICAL</small>
        </button>
      </el-col>
      <el-col
        :xs="24"
        :md="6"
      >
        <button
          type="button"
          class="metric"
          @click="handleMetricDrilldown('agent.pending_confirmations')"
        >
          <span class="metric__label">待确认请求</span>
          <strong>{{ reportMetricValue('agent.pending_confirmations', pendingConfirmationCount) }}</strong>
          <small>状态为 PENDING</small>
        </button>
      </el-col>
    </el-row>

    <el-card
      v-if="operationsReport"
      id="operations-report"
      class="b-dashboard__panel operations-report"
    >
      <template #header>
        <div class="card-header">
          <div>
            <span class="panel-title">运营总览</span>
            <p class="panel-subtitle">
              汇总供应商、寻源、Agent、RAG 和风险评分，给成员 B 一个可执行的工作看板。
            </p>
          </div>
          <div class="card-header__actions">
            <span class="operations-report__generated">
              生成时间 {{ formatTime(operationsReport.generated_at) }}
            </span>
            <el-tag type="primary">
              /reporting/operations
            </el-tag>
            <el-button
              link
              type="primary"
              @click="loadOperationsReport"
            >
              刷新总览
            </el-button>
          </div>
        </div>
      </template>

      <div class="operations-report__layout">
        <div class="operations-report__metrics">
          <button
            v-for="metric in operationsReport.metrics"
            :key="metric.key"
            type="button"
            class="operations-report__metric"
            @click="handleMetricDrilldown(metric.key)"
          >
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
            <small>{{ metric.description }}</small>
          </button>
        </div>

        <div class="operations-report__side">
          <h3>平台基础能力</h3>
          <div class="platform-capabilities">
            <div
              v-for="capability in operationsReport.platform_capabilities"
              :key="capability.key"
              class="platform-capability"
            >
              <div>
                <strong>{{ capability.label }}</strong>
                <small>{{ capability.description }}</small>
              </div>
              <div>
                <el-tag type="success">
                  {{ capability.status }}
                </el-tag>
                <code>{{ capability.endpoint }}</code>
              </div>
            </div>
          </div>

          <h3>高风险关注</h3>
          <div
            v-for="supplier in operationsReport.top_risk_suppliers"
            :key="supplier.supplier_id"
            class="operations-report__hotspot"
          >
            <div>
              <strong>{{ supplier.supplier_name }}</strong>
              <small>{{ supplier.score }} 分</small>
            </div>
            <div>
              <el-tag :type="riskTagType(supplier.risk_level)">
                {{ supplier.risk_level }}
              </el-tag>
              <el-tag :type="supplierRiskActionTagType(supplier.recommended_action)">
                {{ supplier.recommended_action }}
              </el-tag>
              <el-button
                link
                type="primary"
                @click="openSupplierDetail(supplier.supplier_id)"
              >
                打开详情
              </el-button>
            </div>
          </div>

          <h3>下一步动作</h3>
          <ul class="operations-report__actions">
            <li
              v-for="action in operationsReport.next_actions"
              :key="action.key"
            >
              <button
                type="button"
                class="operations-report__action"
                @click="handleReportAction(action)"
              >
                <span>{{ action.label }}</span>
                <small>{{ action.description }}</small>
              </button>
            </li>
          </ul>
        </div>
      </div>
    </el-card>

    <el-card class="b-dashboard__panel action-center">
      <template #header>
        <div class="card-header">
          <div>
            <span class="panel-title">行动中心</span>
            <p class="panel-subtitle">
              汇总高风险供应商、Agent 待办和知识库处理项，优先处理最关键的工作。
            </p>
          </div>
          <div class="card-header__actions">
            <el-tag type="danger">
              {{ actionItems.length }} 个待办
            </el-tag>
            <el-button
              link
              type="primary"
              @click="loadActionItems"
            >
              刷新待办
            </el-button>
          </div>
        </div>
      </template>

      <div
        v-if="actionItems.length > 0"
        class="action-center__list"
      >
        <button
          v-for="item in actionItems"
          :key="item.item_id"
          type="button"
          class="action-center__item"
          @click="handleActionItem(item)"
        >
          <div class="action-center__main">
            <div class="action-center__title">
              <el-tag
                size="small"
                :type="actionPriorityTagType(item.priority)"
              >
                {{ item.priority }}
              </el-tag>
              <strong>{{ item.title }}</strong>
            </div>
            <p>{{ item.description }}</p>
          </div>
          <div class="action-center__meta">
            <el-tag type="info">
              {{ item.status_label }}
            </el-tag>
            <small>{{ item.due_at ? `到期 ${formatTime(item.due_at)}` : formatTime(item.created_at) }}</small>
          </div>
        </button>
      </div>
      <el-empty
        v-else
        description="暂无待办"
        :image-size="64"
      />
    </el-card>

    <div class="b-dashboard__grid">
      <el-card
        id="supplier-ledger"
        class="b-dashboard__panel"
      >
        <template #header>
          <div class="card-header">
            <div>
              <span class="panel-title">供应商风险台账</span>
              <p class="panel-subtitle">
                先用 demo 数据熟悉企业后台的查询、筛选和详情查看。
              </p>
            </div>
            <el-tag type="success">
              /suppliers
            </el-tag>
          </div>
        </template>

        <div class="table-toolbar">
          <el-input
            v-model="supplierKeyword"
            clearable
            placeholder="搜索供应商名称"
            class="table-toolbar__search"
            @clear="applySupplierFilters"
            @keyup.enter="applySupplierFilters"
          />
          <el-select
            v-model="riskFilter"
            class="table-toolbar__select"
            @change="applySupplierFilters"
          >
            <el-option
              v-for="option in riskOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-select
            v-model="supplierStatusFilter"
            class="table-toolbar__select"
            @change="applySupplierFilters"
          >
            <el-option
              v-for="option in supplierStatusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-button
            type="primary"
            @click="applySupplierFilters"
          >
            查询
          </el-button>
          <el-button @click="resetSupplierFilters">
            重置
          </el-button>
        </div>

        <div class="filter-summary">
          <span>当前显示 {{ suppliers.length }} 家供应商</span>
          <div
            v-if="supplierFilterSummary.length > 0"
            class="filter-summary__tags"
          >
            <el-tag
              v-for="item in supplierFilterSummary"
              :key="item"
              type="info"
            >
              {{ item }}
            </el-tag>
          </div>
          <el-tag
            v-else
            type="success"
          >
            未启用筛选
          </el-tag>
        </div>

        <el-table
          :data="suppliers"
          stripe
          empty-text="暂无匹配供应商"
        >
          <el-table-column
            prop="legal_name"
            label="供应商"
            min-width="260"
          />
          <el-table-column
            label="状态"
            width="120"
          >
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.status)">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="资质"
            width="140"
          >
            <template #default="scope">
              <el-tag :type="qualificationTagType(scope.row.qualification_status)">
                {{ scope.row.qualification_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="风险"
            width="110"
          >
            <template #default="scope">
              <el-tag :type="riskTagType(scope.row.risk_level)">
                {{ scope.row.risk_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="冻结"
            width="90"
          >
            <template #default="scope">
              {{ scope.row.is_frozen ? '是' : '否' }}
            </template>
          </el-table-column>
          <el-table-column
            label="更新时间"
            min-width="170"
          >
            <template #default="scope">
              {{ formatTime(scope.row.updated_at) }}
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="190"
            fixed="right"
          >
            <template #default="scope">
              <el-button
                link
                type="primary"
                @click="openSupplierDetail(scope.row.supplier_id)"
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card
        id="confirmation-queue"
        class="b-dashboard__panel"
      >
        <template #header>
          <div class="card-header">
            <div>
              <span class="panel-title">供应商风险评分</span>
              <p class="panel-subtitle">
                基于供应商状态、资质、冻结状态和风险等级生成可解释评分。
              </p>
            </div>
            <div class="card-header__actions">
              <el-tag type="danger">
                /risk/supplier-assessments
              </el-tag>
              <el-button
                link
                type="primary"
                @click="loadSupplierRiskAssessments"
              >
                刷新评分
              </el-button>
            </div>
          </div>
        </template>

        <el-table
          :data="supplierRiskAssessments"
          stripe
          empty-text="暂无风险评分"
        >
          <el-table-column
            prop="supplier_name"
            label="供应商"
            min-width="260"
            show-overflow-tooltip
          />
          <el-table-column
            prop="score"
            label="分数"
            width="90"
          />
          <el-table-column
            label="风险"
            width="120"
          >
            <template #default="scope">
              <el-tag :type="riskTagType(scope.row.risk_level)">
                {{ scope.row.risk_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="建议动作"
            width="130"
          >
            <template #default="scope">
              <el-tag :type="supplierRiskActionTagType(scope.row.recommended_action)">
                {{ scope.row.recommended_action }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="因子"
            min-width="180"
          >
            <template #default="scope">
              {{ riskFactorCodes(scope.row) }}
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="130"
            fixed="right"
          >
            <template #default="scope">
              <el-button
                link
                type="primary"
                :loading="riskAssessmentRefreshing"
                @click="refreshSupplierRiskAssessment(scope.row.supplier_id)"
              >
                重新评分
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card
        id="agent-task-queue"
        class="b-dashboard__panel"
      >
        <template #header>
          <div class="card-header">
            <div>
              <span class="panel-title">Agent 任务队列</span>
              <p class="panel-subtitle">
                从供应商详情发起的寻源和风险分析任务会进入这里，当前 {{ queuedAgentTaskCount }} 个排队中。
              </p>
            </div>
            <div class="card-header__actions">
              <el-button
                type="primary"
                plain
                :loading="quickScenarioSubmitting"
                @click="createPendingConfirmationScenario"
              >
                生成待确认流程
              </el-button>
              <el-select
                v-model="taskStatusFilter"
                class="task-status-filter"
                @change="loadRecentAgentTasks"
              >
                <el-option
                  v-for="option in taskStatusOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
              <el-tag type="primary">
                /agent/tasks
              </el-tag>
              <el-button
                link
                type="primary"
                @click="loadRecentAgentTasks"
              >
                刷新队列
              </el-button>
            </div>
          </div>
        </template>

        <el-table
          :data="recentAgentTasks"
          stripe
          empty-text="暂无 Agent 任务"
        >
          <el-table-column
            prop="agent_type"
            label="任务类型"
            width="180"
          />
          <el-table-column
            prop="goal"
            label="目标"
            min-width="360"
            show-overflow-tooltip
          />
          <el-table-column
            label="状态"
            width="130"
          >
            <template #default="scope">
              <el-tag :type="agentTaskStatusTagType(scope.row.status)">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="创建时间"
            width="170"
          >
            <template #default="scope">
              {{ formatTime(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="90"
            fixed="right"
          >
            <template #default="scope">
              <el-button
                link
                type="primary"
                @click="openAgentTaskDetail(scope.row.task_id)"
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="b-dashboard__panel">
        <template #header>
          <div class="card-header">
            <div>
              <span class="panel-title">人工确认队列</span>
              <p class="panel-subtitle">
                Agent 高风险动作进入等待确认后，会在这里形成待办。
              </p>
            </div>
            <div class="card-header__actions">
              <el-tag type="danger">
                /agent/confirmations
              </el-tag>
              <el-button
                link
                type="primary"
                @click="loadConfirmationRequests"
              >
                刷新确认
              </el-button>
            </div>
          </div>
        </template>

        <el-table
          :data="confirmationRequests"
          stripe
          empty-text="暂无待确认请求"
        >
          <el-table-column
            prop="proposed_action"
            label="建议动作"
            min-width="320"
            show-overflow-tooltip
          />
          <el-table-column
            label="风险"
            width="100"
          >
            <template #default="scope">
              <el-tag :type="riskTagType(scope.row.risk_level)">
                {{ scope.row.risk_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="required_permission"
            label="所需权限"
            min-width="220"
            show-overflow-tooltip
          />
          <el-table-column
            label="过期时间"
            width="170"
          >
            <template #default="scope">
              {{ formatTime(scope.row.expires_at) }}
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="250"
            fixed="right"
          >
            <template #default="scope">
              <el-button
                link
                type="success"
                :loading="confirmationDecisionSubmittingId === scope.row.confirmation_id"
                @click="decideConfirmationRequest(scope.row, 'CONFIRMED')"
              >
                通过
              </el-button>
              <el-button
                link
                type="danger"
                :loading="confirmationDecisionSubmittingId === scope.row.confirmation_id"
                @click="decideConfirmationRequest(scope.row, 'REJECTED')"
              >
                驳回
              </el-button>
              <el-button
                link
                type="primary"
                @click="openConfirmationDetail(scope.row.confirmation_id)"
              >
                查看
              </el-button>
              <el-button
                link
                type="primary"
                @click="openAgentTaskDetail(scope.row.task_id)"
              >
                查看任务
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card
        id="tool-registry"
        class="b-dashboard__panel"
      >
        <template #header>
          <div class="card-header">
            <div>
              <span class="panel-title">Agent 工具注册表</span>
              <p class="panel-subtitle">
                当前已启用 {{ enabledToolCount }} 个工具，Agent 只能通过这里登记过的工具访问业务能力。
              </p>
            </div>
            <el-tag type="warning">
              /tools
            </el-tag>
          </div>
        </template>

        <el-table
          :data="tools"
          class="tool-table"
          stripe
          empty-text="暂无工具"
          @row-click="openToolDetail"
        >
          <el-table-column
            prop="name"
            label="工具名"
            min-width="260"
          />
          <el-table-column
            prop="owner_module"
            label="归属模块"
            width="130"
          />
          <el-table-column
            label="风险等级"
            width="120"
          >
            <template #default="scope">
              <el-tag :type="riskTagType(scope.row.risk_level)">
                {{ scope.row.risk_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="需要幂等"
            width="110"
          >
            <template #default="scope">
              <el-tag :type="scope.row.idempotency_required ? 'warning' : 'info'">
                {{ scope.row.idempotency_required ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="权限"
            min-width="180"
          >
            <template #default="scope">
              {{ scope.row.required_permissions.join(', ') }}
            </template>
          </el-table-column>
          <el-table-column
            prop="timeout_seconds"
            label="超时秒数"
            width="110"
          />
        </el-table>
      </el-card>
    </div>

    <el-card
      id="sourcing-workbench"
      class="b-dashboard__panel sourcing-panel"
    >
      <template #header>
        <div class="card-header">
          <div>
            <span class="panel-title">寻源项目</span>
            <p class="panel-subtitle">
              当前 {{ activeSourcingProjectCount }} 个项目进行中，可从供应商详情创建候选供应商寻源项目。
            </p>
          </div>
          <div class="card-header__actions">
            <el-tag type="primary">
              /sourcing/projects
            </el-tag>
            <el-button
              link
              type="primary"
              @click="loadSourcingProjects"
            >
              刷新项目
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="sourcingProjects"
        stripe
        empty-text="暂无寻源项目"
      >
        <el-table-column
          prop="title"
          label="项目"
          min-width="260"
          show-overflow-tooltip
        />
        <el-table-column
          label="状态"
          width="120"
        >
          <template #default="scope">
            <el-tag :type="sourcingStatusTagType(scope.row.status)">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="候选供应商"
          width="120"
        >
          <template #default="scope">
            {{ scope.row.candidate_supplier_ids.length }}
          </template>
        </el-table-column>
        <el-table-column
          label="采购申请"
          min-width="180"
          show-overflow-tooltip
        >
          <template #default="scope">
            {{ scope.row.procurement_request_id }} · v{{ scope.row.procurement_request_version }}
          </template>
        </el-table-column>
        <el-table-column
          label="更新时间"
          width="170"
        >
          <template #default="scope">
            {{ formatTime(scope.row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="240"
          fixed="right"
        >
          <template #default="scope">
            <el-button
              v-for="status in availableSourcingStatusActions(scope.row)"
              :key="status"
              link
              :type="sourcingStatusTagType(status)"
              @click="updateSourcingProjectStatus(scope.row, status)"
            >
              {{ status }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card
      id="rag-workbench"
      class="b-dashboard__panel rag-panel"
    >
      <template #header>
        <div class="card-header">
          <div>
            <span class="panel-title">RAG 知识库</span>
            <p class="panel-subtitle">
              当前 {{ indexedKnowledgeDocumentCount }} 篇文档已索引，可用于供应商风险、寻源规则等场景的检索测试。
            </p>
          </div>
          <div class="card-header__actions">
            <el-tag type="success">
              /rag
            </el-tag>
            <el-button
              link
              type="primary"
              @click="loadKnowledgeDocuments"
            >
              刷新文档
            </el-button>
            <el-button
              type="primary"
              @click="ragDocumentDialogVisible = true"
            >
              新增文档
            </el-button>
          </div>
        </div>
      </template>

      <div class="rag-layout">
        <div>
          <el-table
            :data="knowledgeDocuments"
            stripe
            empty-text="暂无知识文档"
          >
            <el-table-column
              prop="title"
              label="文档"
              min-width="220"
              show-overflow-tooltip
            />
            <el-table-column
              prop="owner_module"
              label="模块"
              width="110"
            />
            <el-table-column
              label="状态"
              width="120"
            >
              <template #default="scope">
                <el-tag :type="knowledgeDocumentStatusTagType(scope.row.status)">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="chunk_count"
              label="分块"
              width="80"
            />
            <el-table-column
              label="操作"
              width="210"
              fixed="right"
            >
              <template #default="scope">
                <el-button
                  v-for="status in availableKnowledgeDocumentStatusActions(scope.row)"
                  :key="status"
                  link
                  :type="knowledgeDocumentStatusTagType(status)"
                  @click="updateKnowledgeDocumentStatus(scope.row, status)"
                >
                  {{ status }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="rag-search">
          <div class="rag-search__bar">
            <el-input
              v-model="ragSearchQuery"
              clearable
              placeholder="输入检索问题"
              @keyup.enter="searchKnowledge"
            />
            <el-button
              type="primary"
              :loading="ragSearchLoading"
              @click="searchKnowledge"
            >
              检索
            </el-button>
          </div>
          <div class="rag-search__results">
            <div
              v-for="match in ragSearchResults"
              :key="match.document_id"
              class="rag-search-result"
            >
              <div class="rag-search-result__header">
                <strong>{{ match.title }}</strong>
                <el-tag type="success">
                  {{ match.score }}
                </el-tag>
              </div>
              <p>{{ match.snippet }}</p>
              <small>{{ match.owner_module }} · {{ formatTime(match.updated_at) }}</small>
            </div>
            <el-empty
              v-if="ragSearchResults.length === 0"
              description="暂无检索结果"
              :image-size="64"
            />
          </div>
        </div>
      </div>
    </el-card>

    <el-dialog
      v-model="ragDocumentDialogVisible"
      title="新增知识文档"
      width="620px"
    >
      <el-form
        label-position="top"
        class="rag-document-form"
      >
        <el-form-item label="文档标题">
          <el-input
            v-model="ragDocumentForm.title"
            maxlength="200"
            show-word-limit
            placeholder="例如：供应商风险复核规则"
          />
        </el-form-item>
        <el-form-item label="归属模块">
          <el-select
            v-model="ragDocumentForm.owner_module"
            class="rag-document-form__select"
          >
            <el-option
              label="suppliers"
              value="suppliers"
            />
            <el-option
              label="sourcing"
              value="sourcing"
            />
            <el-option
              label="risk"
              value="risk"
            />
            <el-option
              label="rag"
              value="rag"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input
            v-model="ragDocumentForm.tags"
            placeholder="用英文逗号分隔，例如 supplier,risk"
          />
        </el-form-item>
        <el-form-item label="文档内容">
          <el-input
            v-model="ragDocumentForm.content"
            type="textarea"
            :rows="7"
            maxlength="20000"
            show-word-limit
            placeholder="粘贴制度、规则、知识片段或供应商协作说明"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ragDocumentDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="ragDocumentSubmitting"
          @click="createKnowledgeDocument"
        >
          创建文档
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="toolDetailVisible"
      title="工具详情"
      width="760px"
    >
      <div
        v-if="selectedTool"
        class="tool-detail"
      >
        <div class="tool-detail__summary">
          <div>
            <span>工具名称</span>
            <strong>{{ selectedTool.name }}</strong>
          </div>
          <div>
            <span>版本</span>
            <strong>{{ selectedTool.version }}</strong>
          </div>
          <div>
            <span>归属模块</span>
            <strong>{{ selectedTool.owner_module }}</strong>
          </div>
          <div>
            <span>风险等级</span>
            <el-tag :type="riskTagType(selectedTool.risk_level)">
              {{ selectedTool.risk_level }}
            </el-tag>
          </div>
        </div>

        <el-descriptions
          :column="2"
          border
        >
          <el-descriptions-item label="是否启用">
            <el-tag :type="selectedTool.enabled ? 'success' : 'info'">
              {{ selectedTool.enabled ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="幂等要求">
            <el-tag :type="selectedTool.idempotency_required ? 'warning' : 'info'">
              {{ selectedTool.idempotency_required ? '需要' : '不需要' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="超时秒数">
            {{ selectedTool.timeout_seconds }}
          </el-descriptions-item>
          <el-descriptions-item label="所需权限">
            {{ selectedTool.required_permissions.join(', ') }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="tool-detail__schemas">
          <div>
            <h3>输入 Schema</h3>
            <pre>{{ formatJson(selectedTool.input_schema) }}</pre>
          </div>
          <div>
            <h3>输出 Schema</h3>
            <pre>{{ formatJson(selectedTool.output_schema) }}</pre>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="toolDetailVisible = false">
          关闭
        </el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="drawerVisible"
      title="供应商详情"
      size="560px"
    >
      <div
        v-loading="detailLoading"
        class="supplier-detail"
      >
        <template v-if="selectedSupplier">
          <header class="supplier-detail__hero">
            <div>
              <h2>{{ selectedSupplier.legal_name }}</h2>
              <p>{{ selectedSupplier.supplier_id }}</p>
            </div>
            <div class="supplier-detail__tags">
              <el-tag :type="statusTagType(selectedSupplier.status)">
                {{ selectedSupplier.status }}
              </el-tag>
              <el-tag :type="riskTagType(selectedSupplier.risk_level)">
                {{ selectedSupplier.risk_level }}
              </el-tag>
            </div>
          </header>

          <div class="supplier-detail__actions">
            <el-button
              :loading="agentTaskSubmitting"
              @click="submitAgentTask('sourcing_assistant')"
            >
              发起寻源
            </el-button>
            <el-button
              type="success"
              plain
              :loading="sourcingSubmitting"
              @click="createSourcingProjectFromSupplier"
            >
              创建寻源项目
            </el-button>
            <el-button
              type="primary"
              @click="openRiskReviewDialog"
            >
              风险复核
            </el-button>
            <el-button
              :loading="agentTaskSubmitting"
              @click="submitAgentTask('supplier_risk_analyzer')"
            >
              风险分析
            </el-button>
          </div>

          <div class="supplier-detail__metrics">
            <div class="detail-metric">
              <span>治理状态</span>
              <strong>{{ selectedGovernanceState }}</strong>
            </div>
            <div class="detail-metric">
              <span>覆盖品类</span>
              <strong>{{ selectedCategoryCount }}</strong>
            </div>
            <div class="detail-metric">
              <span>数据版本</span>
              <strong>v{{ selectedSupplier.version }}</strong>
            </div>
          </div>

          <el-tabs class="supplier-detail__tabs">
            <el-tab-pane label="基础信息">
              <el-descriptions
                :column="1"
                border
              >
                <el-descriptions-item label="供应商名称">
                  {{ selectedSupplier.legal_name }}
                </el-descriptions-item>
                <el-descriptions-item label="供应商 ID">
                  {{ selectedSupplier.supplier_id }}
                </el-descriptions-item>
                <el-descriptions-item label="组织 ID">
                  {{ selectedSupplier.org_id }}
                </el-descriptions-item>
                <el-descriptions-item label="更新时间">
                  {{ formatTime(selectedSupplier.updated_at) }}
                </el-descriptions-item>
              </el-descriptions>
            </el-tab-pane>

            <el-tab-pane label="治理状态">
              <el-descriptions
                :column="1"
                border
              >
                <el-descriptions-item label="供应商状态">
                  <el-tag :type="statusTagType(selectedSupplier.status)">
                    {{ selectedSupplier.status }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="资质状态">
                  <el-tag :type="qualificationTagType(selectedSupplier.qualification_status)">
                    {{ selectedSupplier.qualification_status }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="风险等级">
                  <el-tag :type="riskTagType(selectedSupplier.risk_level)">
                    {{ selectedSupplier.risk_level }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="是否冻结">
                  {{ selectedSupplier.is_frozen ? '是' : '否' }}
                </el-descriptions-item>
                <el-descriptions-item label="治理状态">
                  {{ selectedGovernanceState }}
                </el-descriptions-item>
              </el-descriptions>
              <div
                v-if="selectedRiskAssessment"
                class="risk-assessment-card"
              >
                <div class="risk-assessment-card__header">
                  <div>
                    <span>自动风险评分</span>
                    <strong>{{ selectedRiskAssessment.score }}</strong>
                  </div>
                  <div class="risk-assessment-card__tags">
                    <el-tag :type="riskTagType(selectedRiskAssessment.risk_level)">
                      {{ selectedRiskAssessment.risk_level }}
                    </el-tag>
                    <el-tag :type="supplierRiskActionTagType(selectedRiskAssessment.recommended_action)">
                      {{ selectedRiskAssessment.recommended_action }}
                    </el-tag>
                  </div>
                </div>
                <p>{{ selectedRiskAssessment.summary }}</p>
                <div class="risk-assessment-card__factors">
                  <el-tag
                    v-for="factor in selectedRiskAssessment.factors"
                    :key="factor.code"
                    type="info"
                  >
                    {{ factor.code }} +{{ factor.impact_score }}
                  </el-tag>
                </div>
                <el-button
                  link
                  type="primary"
                  :loading="riskAssessmentRefreshing"
                  @click="refreshSupplierRiskAssessment(selectedSupplier.supplier_id)"
                >
                  重新评分
                </el-button>
              </div>
              <div class="risk-review-card">
                <div class="risk-review-card__header">
                  <span>最近复核</span>
                  <el-tag
                    v-if="latestRiskReview"
                    :type="conclusionTagType(latestRiskReview.conclusion)"
                  >
                    {{ conclusionLabel(latestRiskReview.conclusion) }}
                  </el-tag>
                </div>
                <template v-if="latestRiskReview">
                  <p>{{ latestRiskReview.note }}</p>
                  <small>
                    {{ latestRiskReview.reviewed_by }} · {{ formatTime(latestRiskReview.created_at) }}
                  </small>
                </template>
                <el-empty
                  v-else
                  description="暂无复核记录"
                  :image-size="64"
                />
              </div>
              <div class="risk-review-history">
                <h3>复核历史</h3>
                <el-timeline v-if="riskReviews.length > 0">
                  <el-timeline-item
                    v-for="review in riskReviews"
                    :key="review.review_id"
                    :timestamp="formatTime(review.created_at)"
                    placement="top"
                  >
                    <div class="risk-review-history__item">
                      <div class="risk-review-history__title">
                        <el-tag :type="conclusionTagType(review.conclusion)">
                          {{ conclusionLabel(review.conclusion) }}
                        </el-tag>
                        <span>{{ review.reviewed_by }}</span>
                      </div>
                      <p>{{ review.note }}</p>
                    </div>
                  </el-timeline-item>
                </el-timeline>
                <el-empty
                  v-else
                  description="暂无复核历史"
                  :image-size="64"
                />
              </div>
            </el-tab-pane>

            <el-tab-pane label="关联品类">
              <div class="category-list">
                <div
                  v-for="categoryId in selectedSupplier.category_ids"
                  :key="categoryId"
                  class="category-list__item"
                >
                  <span>品类 ID</span>
                  <strong>{{ categoryId }}</strong>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane label="任务追踪">
              <el-timeline v-if="supplierAgentTasks.length > 0">
                <el-timeline-item
                  v-for="task in supplierAgentTasks"
                  :key="task.task_id"
                  :timestamp="formatTime(task.created_at)"
                  placement="top"
                >
                  <div class="agent-task-card">
                    <div class="agent-task-card__header">
                      <span>{{ task.agent_type }}</span>
                      <el-tag :type="agentTaskStatusTagType(task.status)">
                        {{ task.status }}
                      </el-tag>
                    </div>
                    <p>{{ task.goal }}</p>
                    <dl>
                      <div>
                        <dt>任务 ID</dt>
                        <dd>{{ task.task_id }}</dd>
                      </div>
                      <div>
                        <dt>Trace ID</dt>
                        <dd>{{ task.trace_id }}</dd>
                      </div>
                    </dl>
                    <el-button
                      link
                      type="primary"
                      class="agent-task-card__action"
                      @click="openAgentTaskDetail(task.task_id)"
                    >
                      查看任务详情
                    </el-button>
                  </div>
                </el-timeline-item>
              </el-timeline>
              <el-empty
                v-else
                description="暂无本次发起的 Agent 任务"
                :image-size="64"
              />
            </el-tab-pane>
          </el-tabs>
        </template>
      </div>
    </el-drawer>

    <el-dialog
      v-model="riskReviewVisible"
      title="风险复核"
      width="520px"
    >
      <el-form
        label-position="top"
        class="risk-review-form"
      >
        <el-form-item label="供应商">
          <el-input
            :model-value="selectedSupplier?.legal_name"
            disabled
          />
        </el-form-item>
        <el-form-item label="复核结论">
          <el-select
            v-model="riskReviewForm.conclusion"
            class="risk-review-form__select"
          >
            <el-option
              v-for="option in conclusionOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="复核备注">
          <el-input
            v-model="riskReviewForm.note"
            type="textarea"
            :rows="5"
            maxlength="1000"
            show-word-limit
            placeholder="填写风险判断依据、建议动作或需要升级处理的原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="riskReviewVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="reviewSubmitting"
          @click="submitRiskReview"
        >
          提交复核
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="taskDetailVisible"
      title="Agent 任务详情"
      width="680px"
    >
      <div
        v-loading="taskDetailLoading"
        class="agent-task-detail"
      >
        <template v-if="selectedAgentTask">
          <div class="agent-task-detail__summary">
            <div>
              <span>任务类型</span>
              <strong>{{ selectedAgentTask.agent_type }}</strong>
            </div>
            <div>
              <span>任务状态</span>
              <el-tag :type="agentTaskStatusTagType(selectedAgentTask.status)">
                {{ selectedAgentTask.status }}
              </el-tag>
            </div>
          </div>

          <el-descriptions
            :column="1"
            border
          >
            <el-descriptions-item label="任务目标">
              {{ selectedAgentTask.goal }}
            </el-descriptions-item>
            <el-descriptions-item label="任务 ID">
              {{ selectedAgentTask.task_id }}
            </el-descriptions-item>
            <el-descriptions-item label="组织 ID">
              {{ selectedAgentTask.org_id }}
            </el-descriptions-item>
            <el-descriptions-item label="发起人 ID">
              {{ selectedAgentTask.requested_by }}
            </el-descriptions-item>
            <el-descriptions-item label="Trace ID">
              {{ selectedAgentTask.trace_id }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatTime(selectedAgentTask.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">
              {{ formatTime(selectedAgentTask.updated_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="错误码">
              {{ selectedAgentTask.error_code ?? '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="关联对象">
              <div class="agent-task-detail__refs">
                <el-tag
                  v-for="subjectRef in selectedAgentTask.subject_refs"
                  :key="`${subjectRef.object_type}-${subjectRef.object_id}`"
                  type="info"
                >
                  {{ subjectRef.object_type }} · {{ subjectRef.object_id }} · v{{ subjectRef.version ?? '-' }}
                </el-tag>
              </div>
            </el-descriptions-item>
          </el-descriptions>

          <div class="agent-task-confirmations">
            <h3>关联确认单</h3>
            <div
              v-if="selectedAgentTaskConfirmations.length > 0"
              class="agent-task-confirmations__list"
            >
              <div
                v-for="confirmation in selectedAgentTaskConfirmations"
                :key="confirmation.confirmation_id"
                class="agent-task-confirmation"
              >
                <div class="agent-task-confirmation__header">
                  <div>
                    <strong>{{ confirmation.proposed_action }}</strong>
                    <small>{{ formatTime(confirmation.expires_at) }}</small>
                  </div>
                  <div class="agent-task-confirmation__tags">
                    <el-tag :type="riskTagType(confirmation.risk_level)">
                      {{ confirmation.risk_level }}
                    </el-tag>
                    <el-tag :type="confirmationStatusTagType(confirmation.status)">
                      {{ confirmation.status }}
                    </el-tag>
                  </div>
                </div>
                <div class="agent-task-confirmation__meta">
                  <span>{{ confirmation.required_permission }}</span>
                  <el-button
                    link
                    type="primary"
                    @click="openConfirmationDetail(confirmation.confirmation_id)"
                  >
                    查看确认单
                  </el-button>
                </div>
              </div>
            </div>
            <el-empty
              v-else
              description="暂无关联确认单"
              :image-size="64"
            />
          </div>

          <div class="agent-task-events">
            <h3>执行日志</h3>
            <el-timeline v-if="selectedAgentTaskEvents.length > 0">
              <el-timeline-item
                v-for="event in selectedAgentTaskEvents"
                :key="event.event_id"
                :timestamp="formatTime(event.created_at)"
                placement="top"
              >
                <div class="agent-task-event">
                  <div class="agent-task-event__header">
                    <span>{{ agentTaskEventLabel(event.event_type) }}</span>
                    <el-tag :type="agentTaskStatusTagType(event.to_status)">
                      {{ event.to_status }}
                    </el-tag>
                  </div>
                  <p>{{ event.message }}</p>
                  <small>
                    {{ event.from_status ?? '-' }} → {{ event.to_status }}
                  </small>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty
              v-else
              description="暂无执行日志"
              :image-size="64"
            />
          </div>
        </template>
      </div>
      <template #footer>
        <el-button @click="taskDetailVisible = false">
          关闭
        </el-button>
        <el-button
          v-for="action in availableAgentTaskActions(selectedAgentTask)"
          :key="action.status"
          :type="agentTaskActionType(action)"
          :loading="taskDetailLoading"
          @click="updateSelectedAgentTaskStatus(action.status, action.errorCode ?? null)"
        >
          {{ action.label }}
        </el-button>
        <el-button
          v-if="selectedAgentTask"
          type="primary"
          plain
          :loading="taskDetailLoading"
          @click="openAgentTaskDetail(selectedAgentTask.task_id)"
        >
          刷新状态
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="confirmationDetailVisible"
      title="人工确认详情"
      width="680px"
    >
      <div
        v-loading="confirmationDetailLoading"
        class="confirmation-detail"
      >
        <template v-if="selectedConfirmation">
          <div class="confirmation-detail__summary">
            <div>
              <span>确认状态</span>
              <el-tag :type="confirmationStatusTagType(selectedConfirmation.status)">
                {{ selectedConfirmation.status }}
              </el-tag>
            </div>
            <div>
              <span>风险等级</span>
              <el-tag :type="riskTagType(selectedConfirmation.risk_level)">
                {{ selectedConfirmation.risk_level }}
              </el-tag>
            </div>
          </div>

          <el-descriptions
            :column="1"
            border
          >
            <el-descriptions-item label="建议动作">
              {{ selectedConfirmation.proposed_action }}
            </el-descriptions-item>
            <el-descriptions-item label="确认 ID">
              {{ selectedConfirmation.confirmation_id }}
            </el-descriptions-item>
            <el-descriptions-item label="任务 ID">
              {{ selectedConfirmation.task_id }}
            </el-descriptions-item>
            <el-descriptions-item label="工具调用 ID">
              {{ selectedConfirmation.tool_call_id }}
            </el-descriptions-item>
            <el-descriptions-item label="所需权限">
              {{ selectedConfirmation.required_permission }}
            </el-descriptions-item>
            <el-descriptions-item label="输入摘要">
              {{ selectedConfirmation.input_digest }}
            </el-descriptions-item>
            <el-descriptions-item label="过期时间">
              {{ formatTime(selectedConfirmation.expires_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="关联对象">
              <div class="confirmation-detail__refs">
                <el-tag
                  v-for="targetRef in selectedConfirmation.target_refs"
                  :key="`${targetRef.object_type}-${targetRef.object_id}`"
                  type="info"
                >
                  {{ targetRef.object_type }} · {{ targetRef.object_id }} · v{{ targetRef.version ?? '-' }}
                </el-tag>
              </div>
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </div>
      <template #footer>
        <el-button @click="confirmationDetailVisible = false">
          关闭
        </el-button>
        <el-button
          v-if="selectedConfirmation?.status === 'PENDING'"
          type="danger"
          :loading="
            confirmationDetailLoading ||
              confirmationDecisionSubmittingId === selectedConfirmation.confirmation_id
          "
          @click="decideConfirmationRequest(selectedConfirmation, 'REJECTED')"
        >
          驳回
        </el-button>
        <el-button
          v-if="selectedConfirmation?.status === 'PENDING'"
          type="primary"
          :loading="
            confirmationDetailLoading ||
              confirmationDecisionSubmittingId === selectedConfirmation.confirmation_id
          "
          @click="decideConfirmationRequest(selectedConfirmation, 'CONFIRMED')"
        >
          确认通过
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.b-dashboard {
  max-width: 1280px;
  margin: 24px auto 48px;
}

.b-dashboard__header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.b-dashboard__header h1 {
  margin: 4px 0 8px;
  font-size: 28px;
}

.b-dashboard__header p {
  max-width: 780px;
  color: #475569;
}

.eyebrow {
  margin: 0;
  color: #0f766e;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}

.metric {
  display: block;
  width: 100%;
  min-height: 112px;
  padding: 18px;
  margin-bottom: 16px;
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.metric:hover,
.metric:focus-visible,
.operations-report__metric:hover,
.operations-report__metric:focus-visible {
  border-color: #93c5fd;
  outline: none;
}

.metric strong {
  display: block;
  margin: 8px 0 6px;
  color: #111827;
  font-size: 30px;
  line-height: 1;
}

.metric small,
.metric__label,
.panel-subtitle {
  color: #64748b;
}

.metric__label {
  font-size: 14px;
  font-weight: 600;
}

.metric--risk {
  border-color: #fed7aa;
}

.b-dashboard__alert {
  margin-bottom: 16px;
}

.b-dashboard__grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.b-dashboard__panel {
  overflow: hidden;
}

.operations-report {
  margin-bottom: 16px;
}

.operations-report__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.9fr);
  gap: 16px;
}

.operations-report__metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.operations-report__metric {
  min-height: 96px;
  padding: 14px;
  text-align: left;
  cursor: pointer;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.operations-report__metric span,
.operations-report__metric small {
  color: #64748b;
}

.operations-report__metric span {
  display: block;
  font-size: 12px;
}

.operations-report__metric strong {
  display: block;
  margin: 6px 0;
  color: #111827;
  font-size: 24px;
}

.operations-report__metric small {
  line-height: 1.5;
}

.operations-report__generated {
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}

.operations-report__side {
  min-width: 0;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
}

.operations-report__side h3 {
  margin: 14px 0 10px;
  color: #111827;
  font-size: 15px;
}

.operations-report__side h3:first-child {
  margin-top: 0;
}

.platform-capabilities {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
}

.platform-capability {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 0.45fr);
  gap: 10px;
  padding: 10px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.platform-capability strong,
.platform-capability small,
.platform-capability code {
  display: block;
}

.platform-capability strong {
  color: #111827;
  font-size: 14px;
}

.platform-capability small {
  margin-top: 4px;
  color: #64748b;
  line-height: 1.5;
}

.platform-capability code {
  margin-top: 6px;
  overflow-wrap: anywhere;
  color: #334155;
  font-size: 12px;
}

.operations-report__hotspot {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #e5e7eb;
}

.operations-report__hotspot strong {
  display: block;
  color: #111827;
  font-size: 14px;
}

.operations-report__hotspot small {
  display: block;
  margin-top: 4px;
  color: #64748b;
}

.operations-report__hotspot > div:last-child {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}

.operations-report__actions {
  display: grid;
  gap: 8px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.operations-report__action {
  display: block;
  width: 100%;
  padding: 10px 12px;
  text-align: left;
  color: #374151;
  cursor: pointer;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.operations-report__action:hover {
  border-color: #93c5fd;
}

.operations-report__action span,
.operations-report__action small {
  display: block;
}

.operations-report__action span {
  color: #111827;
  font-weight: 700;
}

.operations-report__action small {
  margin-top: 4px;
  color: #64748b;
  line-height: 1.5;
}

.action-center {
  margin-bottom: 16px;
}

.action-center__list {
  display: grid;
  gap: 10px;
}

.action-center__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 0.24fr);
  gap: 14px;
  width: 100%;
  padding: 12px 14px;
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.action-center__item:hover,
.action-center__item:focus-visible {
  border-color: #93c5fd;
  outline: none;
}

.action-center__main {
  min-width: 0;
}

.action-center__title {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}

.action-center__title strong {
  min-width: 0;
  overflow: hidden;
  color: #111827;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-center__item p {
  margin: 0;
  overflow: hidden;
  color: #475569;
  font-size: 13px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-center__meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
  justify-content: center;
}

.action-center__meta small {
  color: #64748b;
  font-size: 12px;
}

.panel-title {
  color: #111827;
  font-size: 17px;
  font-weight: 700;
}

.panel-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
}

.card-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
}

.task-status-filter {
  width: 140px;
}

.table-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.table-toolbar__search {
  max-width: 360px;
}

.table-toolbar__select {
  width: 160px;
}

.filter-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 12px;
  color: #475569;
  font-size: 13px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.filter-summary__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}

.tool-table {
  cursor: pointer;
}

.tool-detail__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.tool-detail__summary > div {
  min-height: 76px;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.tool-detail__summary span {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 12px;
}

.tool-detail__summary strong {
  color: #111827;
  font-size: 15px;
  word-break: break-all;
}

.tool-detail__schemas {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.tool-detail__schemas h3 {
  margin: 0 0 8px;
  color: #111827;
  font-size: 15px;
}

.tool-detail__schemas pre {
  min-height: 180px;
  max-height: 260px;
  padding: 12px;
  overflow: auto;
  color: #334155;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f8fafc;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
}

.rag-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.9fr);
  gap: 16px;
}

.rag-search {
  min-width: 0;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
}

.rag-search__bar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.rag-search__results {
  display: grid;
  gap: 10px;
}

.rag-search-result {
  padding: 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.rag-search-result__header {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.rag-search-result__header strong {
  color: #111827;
  font-size: 14px;
}

.rag-search-result p {
  margin: 0 0 8px;
  color: #374151;
  line-height: 1.6;
}

.rag-search-result small {
  color: #64748b;
}

.rag-document-form__select {
  width: 100%;
}

.supplier-detail__hero {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.supplier-detail__hero h2 {
  margin: 0 0 16px;
  font-size: 20px;
}

.supplier-detail__hero p {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  word-break: break-all;
}

.supplier-detail__tags,
.supplier-detail__actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.supplier-detail__tags {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.supplier-detail__actions {
  flex-wrap: wrap;
  margin: 16px 0;
}

.supplier-detail__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.detail-metric,
.category-list__item {
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.detail-metric span,
.category-list__item span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.detail-metric strong,
.category-list__item strong {
  display: block;
  margin-top: 6px;
  color: #111827;
  font-size: 16px;
}

.supplier-detail__tabs {
  margin-top: 4px;
}

.category-list {
  display: grid;
  gap: 10px;
}

.category-list__item strong {
  word-break: break-all;
}

.risk-assessment-card {
  padding: 14px;
  margin-top: 16px;
  background: #f8fafc;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
}

.risk-assessment-card__header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 10px;
}

.risk-assessment-card__header span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.risk-assessment-card__header strong {
  display: block;
  margin-top: 4px;
  color: #111827;
  font-size: 26px;
}

.risk-assessment-card__tags,
.risk-assessment-card__factors {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.risk-assessment-card p {
  margin: 0 0 10px;
  color: #374151;
  line-height: 1.6;
}

.risk-assessment-card__factors {
  margin-bottom: 8px;
}

.risk-review-card {
  padding: 14px;
  margin-top: 16px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 8px;
}

.risk-review-card__header {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #111827;
  font-weight: 700;
}

.risk-review-card p {
  margin: 0 0 10px;
  color: #374151;
  line-height: 1.6;
}

.risk-review-card small {
  color: #64748b;
}

.risk-review-form__select {
  width: 100%;
}

.risk-review-history {
  margin-top: 18px;
}

.risk-review-history h3 {
  margin: 0 0 14px;
  color: #111827;
  font-size: 16px;
}

.risk-review-history__item {
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.risk-review-history__title {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 8px;
}

.risk-review-history__title span {
  color: #64748b;
  font-size: 13px;
}

.risk-review-history__item p {
  margin: 0;
  color: #374151;
  line-height: 1.6;
}

.agent-task-card {
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
}

.agent-task-card__header {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #111827;
  font-weight: 700;
}

.agent-task-card p {
  margin: 0 0 12px;
  color: #374151;
  line-height: 1.6;
}

.agent-task-card dl {
  display: grid;
  gap: 8px;
  margin: 0;
}

.agent-task-card dl div {
  min-width: 0;
}

.agent-task-card dt {
  color: #64748b;
  font-size: 12px;
}

.agent-task-card dd {
  margin: 2px 0 0;
  color: #111827;
  font-size: 13px;
  word-break: break-all;
}

.agent-task-card__action {
  margin-top: 10px;
}

.agent-task-detail__summary,
.confirmation-detail__summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.agent-task-detail__summary > div,
.confirmation-detail__summary > div {
  min-height: 72px;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.agent-task-detail__summary span,
.confirmation-detail__summary span {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 12px;
}

.agent-task-detail__summary strong,
.confirmation-detail__summary strong {
  color: #111827;
  font-size: 16px;
  word-break: break-all;
}

.agent-task-detail__refs,
.confirmation-detail__refs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.agent-task-detail :deep(.el-descriptions__content),
.confirmation-detail :deep(.el-descriptions__content) {
  word-break: break-all;
}

.agent-task-confirmations,
.agent-task-events {
  margin-top: 18px;
}

.agent-task-confirmations h3,
.agent-task-events h3 {
  margin: 0 0 14px;
  color: #111827;
  font-size: 16px;
}

.agent-task-confirmations__list {
  display: grid;
  gap: 10px;
}

.agent-task-confirmation {
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
}

.agent-task-confirmation__header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.agent-task-confirmation__header strong {
  display: block;
  color: #111827;
  font-size: 14px;
  line-height: 1.5;
}

.agent-task-confirmation__header small {
  display: block;
  margin-top: 4px;
  color: #64748b;
}

.agent-task-confirmation__tags,
.agent-task-confirmation__meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.agent-task-confirmation__tags {
  flex-shrink: 0;
}

.agent-task-confirmation__meta {
  justify-content: space-between;
  margin-top: 10px;
  color: #64748b;
  font-size: 13px;
  word-break: break-all;
}

.agent-task-event {
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
}

.agent-task-event__header {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #111827;
  font-weight: 700;
}

.agent-task-event p {
  margin: 0 0 8px;
  color: #374151;
  line-height: 1.6;
}

.agent-task-event small {
  color: #64748b;
}

@media (max-width: 720px) {
  .b-dashboard {
    margin: 16px 0 32px;
  }

  .b-dashboard__header,
  .table-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .table-toolbar__search,
  .table-toolbar__select {
    width: 100%;
    max-width: none;
  }

  .supplier-detail__hero {
    flex-direction: column;
  }

  .supplier-detail__tags {
    justify-content: flex-start;
  }

  .supplier-detail__metrics {
    grid-template-columns: 1fr;
  }

  .agent-task-detail__summary,
  .confirmation-detail__summary {
    grid-template-columns: 1fr;
  }

  .tool-detail__summary,
  .tool-detail__schemas,
  .operations-report__layout,
  .operations-report__metrics,
  .rag-layout {
    grid-template-columns: 1fr;
  }

  .operations-report__hotspot {
    flex-direction: column;
  }

  .operations-report__hotspot > div:last-child {
    justify-content: flex-start;
  }

  .operations-report__generated {
    white-space: normal;
  }

  .action-center__item {
    grid-template-columns: 1fr;
  }

  .action-center__meta {
    align-items: flex-start;
  }

  .platform-capability {
    grid-template-columns: 1fr;
  }

  .rag-search__bar {
    flex-direction: column;
  }

  .agent-task-confirmation__header,
  .agent-task-confirmation__meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
