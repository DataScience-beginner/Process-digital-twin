from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EngineeringBaselineStatus(StrEnum):
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class EngineeringChangePackageStatus(StrEnum):
    WORKING = "working"
    IN_REVIEW = "in_review"
    CHECKED = "checked"
    APPROVED = "approved"
    INTEGRATION_QUEUED = "integration_queued"
    INTEGRATED = "integrated"
    CONFLICT = "conflict"
    STALE_INPUT = "stale_input"
    BLOCKED = "blocked"
    REJECTED = "rejected"


class EngineeringImpactState(StrEnum):
    CHANGED = "changed"
    AFFECTED = "affected"
    UPDATE_REQUIRED = "update_required"
    VERIFIED_UNCHANGED = "verified_unchanged"


class EngineeringReviewType(StrEnum):
    DISCIPLINE_CHECK = "discipline_check"
    AFFECTED_DISCIPLINE_REVIEW = "affected_discipline_review"
    ENGINEERING_APPROVAL_GATE = "engineering_approval_gate"
    QA_DOCUMENT_CONTROL = "qa_document_control"
    RELEASE_AUTHORIZATION = "release_authorization"


class EngineeringReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUIRED = "changes_required"
    REJECTED = "rejected"


class IntegrationQueueStatus(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    REFRESH_REQUIRED = "refresh_required"
    BLOCKED = "blocked"
    INTEGRATED = "integrated"


class ReleaseCandidateStatus(StrEnum):
    PREPARING = "preparing"
    DISCIPLINE_REVIEW = "discipline_review"
    QA_CHECK = "qa_check"
    RELEASE_APPROVAL = "release_approval"
    APPROVED = "approved"
    WITHDRAWN = "withdrawn"


class ClientIssueStatus(StrEnum):
    RELEASED = "released"
    SUPERSEDED = "superseded"


class EngineeringBaseline(BaseModel):
    id: str
    project_id: str
    revision: str
    status: EngineeringBaselineStatus
    model_hash: str
    parent_baseline_id: str | None = None
    created_at: datetime | None = None
    approved_at: datetime | None = None


class EngineeringChangeRecord(BaseModel):
    id: int | None = None
    change_package_id: str
    object_id: str
    property_path: str
    change_type: str
    base_object_revision: int
    base_value: Any = None
    proposed_value: Any = None
    unit: str | None = None
    impact_state: EngineeringImpactState = EngineeringImpactState.CHANGED
    provenance: dict[str, Any] = Field(default_factory=dict)


class EngineeringReviewRequirement(BaseModel):
    id: int | None = None
    change_package_id: str
    review_type: EngineeringReviewType
    discipline: str
    reviewer_role: str
    sequence: int = 10
    required: bool = True
    status: EngineeringReviewStatus = EngineeringReviewStatus.PENDING
    reviewer_id: str | None = None
    reviewed_content_hash: str | None = None
    comments: str | None = None
    reviewed_at: datetime | None = None


class EngineeringChangePackage(BaseModel):
    id: str
    project_id: str
    title: str
    discipline: str
    status: EngineeringChangePackageStatus
    base_baseline_id: str
    working_revision: str
    maker_id: str
    description: str | None = None
    content_hash: str
    created_at: datetime | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    changes: list[EngineeringChangeRecord] = Field(default_factory=list)
    reviews: list[EngineeringReviewRequirement] = Field(default_factory=list)


class IntegrationQueueEntry(BaseModel):
    id: int | None = None
    change_package_id: str
    queue_position: int
    status: IntegrationQueueStatus
    validation: dict[str, Any] = Field(default_factory=dict)
    queued_at: datetime | None = None
    integrated_at: datetime | None = None


class ReleaseCandidate(BaseModel):
    id: str
    project_id: str
    baseline_id: str
    revision: str
    status: ReleaseCandidateStatus
    manifest: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    approved_at: datetime | None = None


class ClientIssue(BaseModel):
    id: str
    project_id: str
    release_candidate_id: str
    baseline_id: str
    issue_revision: str
    purpose: str
    status: ClientIssueStatus
    supersedes_issue_id: str | None = None
    manifest: dict[str, Any] = Field(default_factory=dict)
    issued_at: datetime | None = None
    client_visible: bool = True



class EngineeringReviewAction(BaseModel):
    reviewer_id: str
    decision: EngineeringReviewStatus
    comments: str | None = None
