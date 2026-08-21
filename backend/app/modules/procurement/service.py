from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.contracts.master_data import MasterDataStatus
from app.contracts.organizations import OrganizationStatus
from app.contracts.procurement import (
    ProcurementRequestCreate,
    ProcurementRequestLineInput,
    ProcurementRequestLineSnapshot,
    ProcurementRequestSnapshot,
    ProcurementRequestStatus,
    ProcurementRequestUpdate,
)
from app.core.database import utc_now
from app.modules.identity.facade import IdentityFacade
from app.modules.master_data.facade import MasterDataFacade
from app.modules.procurement.models import (
    ProcurementRequest,
    ProcurementRequestLine,
    ProcurementRequestRecordStatus,
)
from app.modules.procurement.repository import ProcurementRepository

MONEY_QUANTUM = Decimal("0.01")
MAX_MONEY = Decimal("9999999999999999.99")


class ProcurementRequestNotFoundError(LookupError):
    pass


class ProcurementRequestConflictError(ValueError):
    pass


class ProcurementRequestStateError(ValueError):
    pass


class InvalidProcurementReferenceError(ValueError):
    pass


class ProcurementRequestService:
    def __init__(
        self,
        repository: ProcurementRepository,
        identity: IdentityFacade,
        master_data: MasterDataFacade,
        today: Callable[[], date] = date.today,
    ) -> None:
        self.repository = repository
        self.identity = identity
        self.master_data = master_data
        self.today = today

    def create(
        self,
        payload: ProcurementRequestCreate,
        requester_membership_id: UUID,
        requester_id: UUID,
    ) -> ProcurementRequestSnapshot:
        self._validate_request_context(
            requester_membership_id,
            requester_id,
            payload.org_id,
            payload.department_id,
        )
        self._validate_required_date(payload.required_date)
        lines = self._build_lines(payload.org_id, payload.lines)
        request = ProcurementRequest(
            request_no=self._new_request_no(),
            organization_id=payload.org_id,
            department_id=payload.department_id,
            requester_id=requester_id,
            requester_membership_id=requester_membership_id,
            currency=payload.currency,
            purpose=payload.purpose.strip(),
            required_date=payload.required_date,
            estimated_total=self._total(lines),
            lines=lines,
        )
        self.repository.add(request)
        self._commit("request number collision")
        return self.snapshot(request)

    def get(self, request_id: UUID) -> ProcurementRequestSnapshot:
        return self.snapshot(self._request(request_id))

    def get_for_update(self, request_id: UUID) -> ProcurementRequestSnapshot:
        request = self.repository.request_for_update(request_id)
        if request is None:
            raise ProcurementRequestNotFoundError(str(request_id))
        return self.snapshot(request)

    def list_requests(self, organization_id: UUID) -> tuple[ProcurementRequestSnapshot, ...]:
        return tuple(
            self.snapshot(request) for request in self.repository.requests(organization_id)
        )

    def update(
        self, request_id: UUID, payload: ProcurementRequestUpdate
    ) -> ProcurementRequestSnapshot:
        request = self._request(request_id)
        self._require_draft(request)
        self._require_version(request, payload.expected_version)
        self._validate_required_date(payload.required_date)
        lines = self._build_lines(request.organization_id, payload.lines)
        request.currency = payload.currency
        request.purpose = payload.purpose.strip()
        request.required_date = payload.required_date
        request.estimated_total = self._total(lines)
        request.updated_at = utc_now()
        try:
            self.repository.replace_lines(request, lines)
        except (IntegrityError, StaleDataError) as exc:
            self.repository.rollback()
            raise ProcurementRequestConflictError("request was updated concurrently") from exc
        self._commit("request was updated concurrently")
        return self.snapshot(request)

    def delete(self, request_id: UUID, expected_version: int) -> None:
        request = self._request(request_id)
        self._require_draft(request)
        self._require_version(request, expected_version)
        self.repository.delete(request)
        self._commit("request was updated concurrently")

    def submit(self, request_id: UUID, expected_version: int) -> ProcurementRequestSnapshot:
        request = self._request(request_id)
        self._require_draft(request)
        self._require_version(request, expected_version)
        if not request.lines:
            raise ProcurementRequestStateError("a request must contain at least one line")
        self._validate_required_date(request.required_date)
        request.status = ProcurementRequestRecordStatus.SUBMITTED
        request.submitted_at = utc_now()
        self._commit("request was updated concurrently")
        return self.snapshot(request)

    def withdraw(self, request_id: UUID, expected_version: int) -> ProcurementRequestSnapshot:
        request = self._request(request_id)
        self._require_version(request, expected_version)
        if request.status != ProcurementRequestRecordStatus.SUBMITTED:
            raise ProcurementRequestStateError("only submitted requests can be withdrawn")
        request.status = ProcurementRequestRecordStatus.DRAFT
        request.submitted_at = None
        self._commit("request was updated concurrently")
        return self.snapshot(request)

    def begin_approval(self, request_id: UUID, expected_version: int) -> ProcurementRequestSnapshot:
        request = self._request(request_id)
        self._require_version(request, expected_version)
        if request.status != ProcurementRequestRecordStatus.SUBMITTED:
            raise ProcurementRequestStateError("only submitted requests can enter approval")
        request.status = ProcurementRequestRecordStatus.IN_APPROVAL
        self._commit("request was updated concurrently")
        return self.snapshot(request)

    def complete_approval(
        self, request_id: UUID, expected_version: int, approved: bool
    ) -> ProcurementRequestSnapshot:
        request = self._request(request_id)
        self._require_version(request, expected_version)
        if request.status != ProcurementRequestRecordStatus.IN_APPROVAL:
            raise ProcurementRequestStateError("request is not in approval")
        request.status = (
            ProcurementRequestRecordStatus.APPROVED
            if approved
            else ProcurementRequestRecordStatus.REJECTED
        )
        self._commit("request was updated concurrently")
        return self.snapshot(request)

    def cancel_approval(
        self, request_id: UUID, expected_version: int
    ) -> ProcurementRequestSnapshot:
        request = self._request(request_id)
        self._require_version(request, expected_version)
        if request.status != ProcurementRequestRecordStatus.IN_APPROVAL:
            raise ProcurementRequestStateError("request is not in approval")
        request.status = ProcurementRequestRecordStatus.SUBMITTED
        self._commit("request was updated concurrently")
        return self.snapshot(request)

    def _validate_request_context(
        self,
        membership_id: UUID,
        requester_id: UUID,
        organization_id: UUID,
        department_id: UUID,
    ) -> None:
        try:
            membership = self.identity.membership(membership_id)
            organization = self.identity.organization(organization_id)
            department = self.identity.organization(department_id)
        except LookupError as exc:
            raise InvalidProcurementReferenceError(
                "active requester, organization, or department not found"
            ) from exc
        if membership.user_id != requester_id:
            raise InvalidProcurementReferenceError("active requester membership not found")
        if (
            organization.status is not OrganizationStatus.ACTIVE
            or membership.organization_id != organization.organization_id
        ):
            raise InvalidProcurementReferenceError(
                "request organization must match the requester membership"
            )
        if (
            department.status is not OrganizationStatus.ACTIVE
            or not self.identity.is_descendant_or_self(
                department.organization_id, organization.organization_id
            )
        ):
            raise InvalidProcurementReferenceError(
                "request department must belong to the organization tree"
            )

    def _build_lines(
        self, organization_id: UUID, payloads: list[ProcurementRequestLineInput]
    ) -> list[ProcurementRequestLine]:
        lines: list[ProcurementRequestLine] = []
        for line_no, payload in enumerate(payloads, start=1):
            try:
                category = self.master_data.category(payload.category_id)
                unit = self.master_data.unit(payload.unit)
            except LookupError as exc:
                raise InvalidProcurementReferenceError(
                    f"line {line_no} category or unit is not active"
                ) from exc
            if (
                category.status is not MasterDataStatus.ACTIVE
                or category.organization_id != organization_id
            ):
                raise InvalidProcurementReferenceError(
                    f"line {line_no} category is not active in the request organization"
                )
            if unit.status is not MasterDataStatus.ACTIVE:
                raise InvalidProcurementReferenceError(f"line {line_no} unit is not active")
            if payload.material_id is not None:
                try:
                    material = self.master_data.material(payload.material_id)
                except LookupError as exc:
                    raise InvalidProcurementReferenceError(
                        f"line {line_no} material is not active"
                    ) from exc
                if (
                    material.status is not MasterDataStatus.ACTIVE
                    or material.organization_id != organization_id
                    or material.category_id != category.category_id
                    or material.unit_code != unit.code
                ):
                    raise InvalidProcurementReferenceError(
                        f"line {line_no} material, category, and unit do not match"
                    )
            price = payload.estimated_unit_price
            amount = (
                Decimal("0.00")
                if price is None
                else (payload.quantity * price).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
            )
            if amount > MAX_MONEY:
                raise InvalidProcurementReferenceError(
                    f"line {line_no} estimated amount exceeds the supported money range"
                )
            lines.append(
                ProcurementRequestLine(
                    line_no=line_no,
                    material_id=payload.material_id,
                    category_id=payload.category_id,
                    description=payload.description.strip(),
                    specification=(
                        payload.specification.strip() if payload.specification is not None else None
                    ),
                    quantity=payload.quantity,
                    unit_code=unit.code,
                    estimated_unit_price=price,
                    estimated_amount=amount,
                )
            )
        return lines

    def _request(self, request_id: UUID) -> ProcurementRequest:
        request = self.repository.request(request_id)
        if request is None:
            raise ProcurementRequestNotFoundError(str(request_id))
        return request

    def _validate_required_date(self, required_date: date) -> None:
        if required_date < self.today():
            raise InvalidProcurementReferenceError("required date cannot be in the past")

    @staticmethod
    def _require_draft(request: ProcurementRequest) -> None:
        if request.status != ProcurementRequestRecordStatus.DRAFT:
            raise ProcurementRequestStateError("only draft requests can be changed")

    @staticmethod
    def _require_version(request: ProcurementRequest, expected_version: int) -> None:
        if request.version != expected_version:
            raise ProcurementRequestConflictError(
                f"version mismatch: expected {expected_version}, current {request.version}"
            )

    @staticmethod
    def _total(lines: list[ProcurementRequestLine]) -> Decimal:
        total = sum((line.estimated_amount for line in lines), Decimal("0.00")).quantize(
            MONEY_QUANTUM
        )
        if total > MAX_MONEY:
            raise InvalidProcurementReferenceError(
                "request estimated total exceeds the supported money range"
            )
        return total

    def _new_request_no(self) -> str:
        return f"PR-{self.today():%Y%m%d}-{uuid4().hex[:12].upper()}"

    def _commit(self, conflict_message: str) -> None:
        try:
            self.repository.commit()
        except (IntegrityError, StaleDataError) as exc:
            self.repository.rollback()
            raise ProcurementRequestConflictError(conflict_message) from exc

    @staticmethod
    def snapshot(request: ProcurementRequest) -> ProcurementRequestSnapshot:
        return ProcurementRequestSnapshot(
            request_id=request.id,
            request_no=request.request_no,
            org_id=request.organization_id,
            department_id=request.department_id,
            requester_id=request.requester_id,
            status=ProcurementRequestStatus(request.status),
            currency=request.currency,
            purpose=request.purpose,
            estimated_total=request.estimated_total,
            required_date=request.required_date,
            lines=[
                ProcurementRequestLineSnapshot(
                    line_id=line.id,
                    line_no=line.line_no,
                    material_id=line.material_id,
                    category_id=line.category_id,
                    description=line.description,
                    specification=line.specification,
                    quantity=line.quantity,
                    unit=line.unit_code,
                    estimated_unit_price=line.estimated_unit_price,
                    estimated_amount=line.estimated_amount,
                )
                for line in request.lines
            ],
            version=request.version,
            submitted_at=request.submitted_at,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
