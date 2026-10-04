from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db_schema import (
    ClientIssueRow,
    EngineeringBaselineRow,
    EngineeringChangePackageRow,
    EngineeringChangeRecordRow,
    EngineeringIntegrationQueueRow,
    EngineeringReviewRequirementRow,
    ReleaseCandidateRow,
)
from .revision_models import (
    ClientIssue,
    ClientIssueStatus,
    EngineeringBaseline,
    EngineeringBaselineStatus,
    EngineeringChangePackage,
    EngineeringChangePackageStatus,
    EngineeringChangeRecord,
    EngineeringImpactState,
    EngineeringReviewRequirement,
    EngineeringReviewStatus,
    EngineeringReviewType,
    IntegrationQueueEntry,
    IntegrationQueueStatus,
    ReleaseCandidate,
    ReleaseCandidateStatus,
)


TERMINOLOGY = {
    "approved_engineering_baseline": "Approved Engineering Baseline",
    "engineering_change_package": "Engineering Change Package",
    "working_revision": "Working Revision",
    "engineering_change_record": "Engineering Change Record",
    "engineering_change_comparison": "Engineering Change Comparison",
    "engineering_conflict": "Engineering Conflict",
    "refresh_against_baseline": "Refresh Against Baseline",
    "engineering_review_package": "Engineering Review Package",
    "discipline_check": "Discipline Check",
    "affected_discipline_review": "Affected-Discipline Review",
    "engineering_approval_gate": "Engineering Approval Gate",
    "integration_queue": "Integration Queue",
    "integrate": "Integrate into Approved Baseline",
    "release_candidate": "Release Candidate",
    "client_issue": "Client Issue",
    "superseded_client_issue": "Superseded Client Issue",
    "affected_update_required": "Affected / Update Required",
    "stale_input": "Stale Input",
}


class RevisionControlBlocked(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def semantic_hash(payload) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _baseline_model(row: EngineeringBaselineRow) -> EngineeringBaseline:
    return EngineeringBaseline(
        id=row.id,
        project_id=row.project_id,
        revision=row.revision,
        status=EngineeringBaselineStatus(row.status),
        parent_baseline_id=row.parent_baseline_id,
        model_hash=row.model_hash,
        created_at=row.created_at,
        approved_at=row.approved_at,
    )


def _change_record_model(row: EngineeringChangeRecordRow) -> EngineeringChangeRecord:
    return EngineeringChangeRecord(
        id=row.id,
        change_package_id=row.change_package_id,
        object_id=row.object_id,
        property_path=row.property_path,
        change_type=row.change_type,
        base_object_revision=row.base_object_revision,
        base_value=row.base_value_json,
        proposed_value=row.proposed_value_json,
        unit=row.unit,
        impact_state=EngineeringImpactState(row.impact_state),
        provenance=row.provenance_json or {},
    )


def _review_model(row: EngineeringReviewRequirementRow) -> EngineeringReviewRequirement:
    return EngineeringReviewRequirement(
        id=row.id,
        change_package_id=row.change_package_id,
        review_type=EngineeringReviewType(row.review_type),
        discipline=row.discipline,
        reviewer_role=row.reviewer_role,
        sequence=row.sequence,
        required=row.required,
        status=EngineeringReviewStatus(row.status),
        reviewer_id=row.reviewer_id,
        reviewed_content_hash=row.reviewed_content_hash,
        comments=row.comments,
        reviewed_at=row.reviewed_at,
    )


def load_change_package(session: Session, package_id: str) -> EngineeringChangePackage:
    row = session.get(EngineeringChangePackageRow, package_id)
    if row is None:
        raise KeyError(package_id)

    changes = session.scalars(
        select(EngineeringChangeRecordRow)
        .where(EngineeringChangeRecordRow.change_package_id == package_id)
        .order_by(EngineeringChangeRecordRow.id)
    ).all()
    reviews = session.scalars(
        select(EngineeringReviewRequirementRow)
        .where(EngineeringReviewRequirementRow.change_package_id == package_id)
        .order_by(
            EngineeringReviewRequirementRow.sequence,
            EngineeringReviewRequirementRow.id,
        )
    ).all()

    return EngineeringChangePackage(
        id=row.id,
        project_id=row.project_id,
        title=row.title,
        discipline=row.discipline,
        status=EngineeringChangePackageStatus(row.status),
        base_baseline_id=row.base_baseline_id,
        working_revision=row.working_revision,
        maker_id=row.maker_id,
        description=row.description,
        content_hash=row.content_hash,
        created_at=row.created_at,
        submitted_at=row.submitted_at,
        approved_at=row.approved_at,
        changes=[_change_record_model(item) for item in changes],
        reviews=[_review_model(item) for item in reviews],
    )


def current_approved_baseline(
    session: Session,
    project_id: str,
) -> EngineeringBaseline | None:
    row = session.scalars(
        select(EngineeringBaselineRow)
        .where(
            EngineeringBaselineRow.project_id == project_id,
            EngineeringBaselineRow.status == EngineeringBaselineStatus.APPROVED.value,
        )
        .order_by(EngineeringBaselineRow.approved_at.desc(), EngineeringBaselineRow.revision.desc())
    ).first()
    return _baseline_model(row) if row is not None else None


def client_issue_catalog(session: Session, project_id: str) -> list[ClientIssue]:
    """Return only formally released client-visible issues.

    This is the server-side boundary used by the client viewer. Internal
    Engineering Change Packages, review comments, conflicts and Release
    Candidates are intentionally not included.
    """
    rows = session.scalars(
        select(ClientIssueRow)
        .where(
            ClientIssueRow.project_id == project_id,
            ClientIssueRow.client_visible.is_(True),
            ClientIssueRow.status == ClientIssueStatus.RELEASED.value,
        )
        .order_by(ClientIssueRow.issued_at.desc(), ClientIssueRow.issue_revision.desc())
    ).all()
    return [
        ClientIssue(
            id=row.id,
            project_id=row.project_id,
            release_candidate_id=row.release_candidate_id,
            baseline_id=row.baseline_id,
            issue_revision=row.issue_revision,
            purpose=row.purpose,
            status=ClientIssueStatus(row.status),
            supersedes_issue_id=row.supersedes_issue_id,
            manifest=row.manifest_json or {},
            issued_at=row.issued_at,
            client_visible=row.client_visible,
        )
        for row in rows
    ]


def integration_readiness(session: Session, package_id: str) -> dict:
    package = load_change_package(session, package_id)
    baseline = current_approved_baseline(session, package.project_id)
    reviews = package.reviews

    stale_baseline = baseline is None or package.base_baseline_id != baseline.id
    required_reviews = [review for review in reviews if review.required]
    review_failures = [
        review.reviewer_role
        for review in required_reviews
        if review.status != EngineeringReviewStatus.APPROVED
        or review.reviewed_content_hash != package.content_hash
    ]
    blocking_impacts = [
        change.object_id
        for change in package.changes
        if change.impact_state == EngineeringImpactState.UPDATE_REQUIRED
    ]

    return {
        "change_package_id": package.id,
        "base_baseline_id": package.base_baseline_id,
        "current_approved_baseline_id": baseline.id if baseline else None,
        "refresh_against_baseline_required": stale_baseline,
        "required_review_count": len(required_reviews),
        "review_failures": review_failures,
        "update_required_objects": blocking_impacts,
        "ready_for_integration": (
            package.status == EngineeringChangePackageStatus.APPROVED
            and not stale_baseline
            and not review_failures
            and not blocking_impacts
        ),
    }


def record_engineering_review(
    session: Session,
    *,
    review_requirement_id: int,
    reviewer_id: str,
    decision: EngineeringReviewStatus,
    comments: str | None = None,
) -> EngineeringChangePackage:
    review = session.get(EngineeringReviewRequirementRow, review_requirement_id)
    if review is None:
        raise RevisionControlBlocked(f"Unknown engineering review requirement {review_requirement_id}.")

    package = session.get(EngineeringChangePackageRow, review.change_package_id)
    if package is None:
        raise RevisionControlBlocked("Engineering Change Package no longer exists.")

    if reviewer_id == package.maker_id:
        raise RevisionControlBlocked(
            "Maker cannot perform the Discipline Check / approval for the same Engineering Change Package."
        )

    if decision == EngineeringReviewStatus.PENDING:
        raise RevisionControlBlocked("A completed engineering review cannot be recorded as pending.")

    review.reviewer_id = reviewer_id
    review.status = decision.value
    review.comments = comments
    review.reviewed_at = _now()
    review.reviewed_content_hash = package.content_hash

    session.flush()

    all_required = session.scalars(
        select(EngineeringReviewRequirementRow).where(
            EngineeringReviewRequirementRow.change_package_id == package.id,
            EngineeringReviewRequirementRow.required.is_(True),
        )
    ).all()

    if any(
        item.status in {
            EngineeringReviewStatus.CHANGES_REQUIRED.value,
            EngineeringReviewStatus.REJECTED.value,
        }
        for item in all_required
    ):
        package.status = EngineeringChangePackageStatus.WORKING.value
        package.approved_at = None
    elif all(
        item.status == EngineeringReviewStatus.APPROVED.value
        and item.reviewed_content_hash == package.content_hash
        for item in all_required
    ):
        package.status = EngineeringChangePackageStatus.APPROVED.value
        package.approved_at = _now()
    else:
        package.status = EngineeringChangePackageStatus.IN_REVIEW.value

    session.commit()
    return load_change_package(session, package.id)


def queue_for_integration(session: Session, package_id: str) -> IntegrationQueueEntry:
    readiness = integration_readiness(session, package_id)
    if not readiness["ready_for_integration"]:
        raise RevisionControlBlocked(
            "Engineering Change Package is not ready for the Integration Queue: "
            + json.dumps(readiness, sort_keys=True)
        )

    package = session.get(EngineeringChangePackageRow, package_id)
    existing = session.scalar(
        select(EngineeringIntegrationQueueRow).where(
            EngineeringIntegrationQueueRow.change_package_id == package_id
        )
    )
    if existing is not None:
        return IntegrationQueueEntry(
            id=existing.id,
            change_package_id=existing.change_package_id,
            queue_position=existing.queue_position,
            status=IntegrationQueueStatus(existing.status),
            validation=existing.validation_json or {},
            queued_at=existing.queued_at,
            integrated_at=existing.integrated_at,
        )

    highest = session.scalar(select(func.max(EngineeringIntegrationQueueRow.queue_position))) or 0
    row = EngineeringIntegrationQueueRow(
        change_package_id=package_id,
        queue_position=highest + 1,
        status=IntegrationQueueStatus.QUEUED.value,
        validation_json=readiness,
        queued_at=_now(),
    )
    session.add(row)
    package.status = EngineeringChangePackageStatus.INTEGRATION_QUEUED.value
    session.commit()
    session.refresh(row)

    return IntegrationQueueEntry(
        id=row.id,
        change_package_id=row.change_package_id,
        queue_position=row.queue_position,
        status=IntegrationQueueStatus(row.status),
        validation=row.validation_json or {},
        queued_at=row.queued_at,
        integrated_at=row.integrated_at,
    )


def revision_control_summary(session: Session, project_id: str) -> dict:
    baseline = current_approved_baseline(session, project_id)
    packages = session.scalars(
        select(EngineeringChangePackageRow)
        .where(EngineeringChangePackageRow.project_id == project_id)
        .order_by(EngineeringChangePackageRow.created_at.desc())
    ).all()
    queue = session.scalars(
        select(EngineeringIntegrationQueueRow)
        .join(
            EngineeringChangePackageRow,
            EngineeringChangePackageRow.id == EngineeringIntegrationQueueRow.change_package_id,
        )
        .where(EngineeringChangePackageRow.project_id == project_id)
        .order_by(EngineeringIntegrationQueueRow.queue_position)
    ).all()
    issues = client_issue_catalog(session, project_id)

    return {
        "terminology": TERMINOLOGY,
        "approved_engineering_baseline": (
            baseline.model_dump(mode="json") if baseline else None
        ),
        "engineering_change_packages": [
            {
                "id": row.id,
                "title": row.title,
                "discipline": row.discipline,
                "status": row.status,
                "base_baseline_id": row.base_baseline_id,
                "working_revision": row.working_revision,
                "maker_id": row.maker_id,
            }
            for row in packages
        ],
        "integration_queue": [
            {
                "change_package_id": row.change_package_id,
                "queue_position": row.queue_position,
                "status": row.status,
                "validation": row.validation_json or {},
            }
            for row in queue
        ],
        "released_client_issues": [
            issue.model_dump(mode="json") for issue in issues
        ],
        "client_visibility_rule": (
            "Client viewer is bound to an immutable Client Issue and exposes "
            "released Client Issues only. Working Revisions, Engineering Change "
            "Packages, internal reviews, conflicts and Release Candidates are internal."
        ),
    }


def seed_revision_control_demo(session: Session, project_id: str) -> None:
    """Backfill a deterministic governance slice without resetting project data."""
    baseline_id = "BASE-BDEP-R03"
    if session.get(EngineeringBaselineRow, baseline_id) is None:
        session.add(
            EngineeringBaselineRow(
                id=baseline_id,
                project_id=project_id,
                revision="BDEP-R03",
                status=EngineeringBaselineStatus.APPROVED.value,
                model_hash=semantic_hash(
                    {
                        "project_id": project_id,
                        "revision": "BDEP-R03",
                        "scope": "Digital BDEP demo approved engineering baseline",
                    }
                ),
                created_at=datetime(2026, 10, 1, 9, 0, 0),
                approved_at=datetime(2026, 10, 1, 16, 0, 0),
            )
        )
        session.flush()

    review_package_id = "ECP-2026-0142"
    if session.get(EngineeringChangePackageRow, review_package_id) is None:
        changes = [
            {
                "object_id": "STR-S102",
                "property_path": "cases.maximum.mass_flow",
                "change_type": "modify",
                "base_object_revision": 19,
                "base_value": 92.0,
                "proposed_value": 110.0,
                "unit": "t/h",
                "impact_state": EngineeringImpactState.CHANGED.value,
            },
            {
                "object_id": "EQ-P101",
                "property_path": "rated_flow",
                "change_type": "derive",
                "base_object_revision": 27,
                "base_value": 101.2,
                "proposed_value": 121.0,
                "unit": "t/h",
                "impact_state": EngineeringImpactState.CHANGED.value,
            },
            {
                "object_id": "VLV-FCV101",
                "property_path": "design_cv",
                "change_type": "impact",
                "base_object_revision": 12,
                "base_value": 42.976,
                "proposed_value": None,
                "unit": None,
                "impact_state": EngineeringImpactState.UPDATE_REQUIRED.value,
            },
            {
                "object_id": "VLV-PSV101",
                "property_path": "relief_basis",
                "change_type": "impact",
                "base_object_revision": 8,
                "base_value": "current approved relief basis",
                "proposed_value": None,
                "unit": None,
                "impact_state": EngineeringImpactState.AFFECTED.value,
            },
        ]
        package_hash = semantic_hash(changes)
        session.add(
            EngineeringChangePackageRow(
                id=review_package_id,
                project_id=project_id,
                title="Capacity Increase — Separator Bottoms System",
                discipline="process",
                status=EngineeringChangePackageStatus.IN_REVIEW.value,
                base_baseline_id=baseline_id,
                working_revision="WR-03",
                maker_id="process-sizing-agent-07",
                description=(
                    "Demonstrates an isolated engineering change with deterministic "
                    "derived impacts and multidisciplinary review."
                ),
                content_hash=package_hash,
                created_at=datetime(2026, 10, 5, 9, 0, 0),
                submitted_at=datetime(2026, 10, 5, 11, 0, 0),
            )
        )
        session.flush()
        for change in changes:
            session.add(
                EngineeringChangeRecordRow(
                    change_package_id=review_package_id,
                    object_id=change["object_id"],
                    property_path=change["property_path"],
                    change_type=change["change_type"],
                    base_object_revision=change["base_object_revision"],
                    base_value_json=change["base_value"],
                    proposed_value_json=change["proposed_value"],
                    unit=change["unit"],
                    impact_state=change["impact_state"],
                    provenance_json={
                        "source": "demo capacity-change study",
                        "base_baseline": baseline_id,
                    },
                )
            )
        session.flush()

        reviews = [
            (
                EngineeringReviewType.DISCIPLINE_CHECK,
                "process",
                "Process Checker",
                10,
                EngineeringReviewStatus.APPROVED,
                "process-checker-01",
            ),
            (
                EngineeringReviewType.AFFECTED_DISCIPLINE_REVIEW,
                "mechanical",
                "Mechanical Lead",
                20,
                EngineeringReviewStatus.PENDING,
                None,
            ),
            (
                EngineeringReviewType.AFFECTED_DISCIPLINE_REVIEW,
                "safety_relief",
                "Relief Specialist",
                20,
                EngineeringReviewStatus.PENDING,
                None,
            ),
            (
                EngineeringReviewType.ENGINEERING_APPROVAL_GATE,
                "project_engineering",
                "Project Engineering Manager",
                30,
                EngineeringReviewStatus.PENDING,
                None,
            ),
        ]
        for review_type, discipline, role, sequence, status, reviewer in reviews:
            session.add(
                EngineeringReviewRequirementRow(
                    change_package_id=review_package_id,
                    review_type=review_type.value,
                    discipline=discipline,
                    reviewer_role=role,
                    sequence=sequence,
                    required=True,
                    status=status.value,
                    reviewer_id=reviewer,
                    reviewed_content_hash=package_hash if reviewer else None,
                    reviewed_at=datetime(2026, 10, 5, 12, 0, 0) if reviewer else None,
                )
            )

    queued_package_id = "ECP-2026-0138"
    if session.get(EngineeringChangePackageRow, queued_package_id) is None:
        queued_changes = [
            {
                "object_id": "INS-FT101",
                "property_path": "range.maximum",
                "base_value": 40.0,
                "proposed_value": 50.0,
                "unit": "t/h",
            }
        ]
        queued_hash = semantic_hash(queued_changes)
        session.add(
            EngineeringChangePackageRow(
                id=queued_package_id,
                project_id=project_id,
                title="FT-101 Measurement Range Update",
                discipline="instrumentation",
                status=EngineeringChangePackageStatus.INTEGRATION_QUEUED.value,
                base_baseline_id=baseline_id,
                working_revision="WR-02",
                maker_id="instrument-engineer-03",
                content_hash=queued_hash,
                created_at=datetime(2026, 10, 4, 9, 0, 0),
                submitted_at=datetime(2026, 10, 4, 12, 0, 0),
                approved_at=datetime(2026, 10, 4, 16, 0, 0),
            )
        )
        session.flush()
        session.add(
            EngineeringChangeRecordRow(
                change_package_id=queued_package_id,
                object_id="INS-FT101",
                property_path="range.maximum",
                change_type="modify",
                base_object_revision=4,
                base_value_json=40.0,
                proposed_value_json=50.0,
                unit="t/h",
                impact_state=EngineeringImpactState.CHANGED.value,
                provenance_json={"source": "instrument range review"},
            )
        )
        for sequence, review_type, discipline, role, reviewer in [
            (10, EngineeringReviewType.DISCIPLINE_CHECK, "instrumentation", "Instrument Checker", "instrument-checker-01"),
            (30, EngineeringReviewType.ENGINEERING_APPROVAL_GATE, "instrumentation", "Instrumentation Lead", "instrument-lead-01"),
        ]:
            session.add(
                EngineeringReviewRequirementRow(
                    change_package_id=queued_package_id,
                    review_type=review_type.value,
                    discipline=discipline,
                    reviewer_role=role,
                    sequence=sequence,
                    required=True,
                    status=EngineeringReviewStatus.APPROVED.value,
                    reviewer_id=reviewer,
                    reviewed_content_hash=queued_hash,
                    reviewed_at=datetime(2026, 10, 4, 16, 0, 0),
                )
            )
        session.flush()
        if session.scalar(
            select(EngineeringIntegrationQueueRow).where(
                EngineeringIntegrationQueueRow.change_package_id == queued_package_id
            )
        ) is None:
            session.add(
                EngineeringIntegrationQueueRow(
                    change_package_id=queued_package_id,
                    queue_position=1,
                    status=IntegrationQueueStatus.QUEUED.value,
                    validation_json={
                        "base_baseline": baseline_id,
                        "discipline_checks": "approved",
                        "deterministic_checks": "green",
                        "note": "Revalidate immediately before integration.",
                    },
                    queued_at=datetime(2026, 10, 4, 16, 5, 0),
                )
            )

    candidate_id = "RC-BDEP-R03"
    if session.get(ReleaseCandidateRow, candidate_id) is None:
        session.add(
            ReleaseCandidateRow(
                id=candidate_id,
                project_id=project_id,
                baseline_id=baseline_id,
                revision="BDEP-R03-RC1",
                status=ReleaseCandidateStatus.APPROVED.value,
                manifest_json={
                    "plant_model": "BDEP-R03",
                    "design_basis": "DB-001 Rev A",
                    "pfd": ["PFD-DEMO-001"],
                    "pid": ["PID-DEMO-001"],
                    "calculations": "frozen at issue",
                    "summaries": "frozen at issue",
                    "service_versions": "captured in release manifest",
                },
                created_at=datetime(2026, 10, 1, 16, 10, 0),
                approved_at=datetime(2026, 10, 2, 10, 0, 0),
            )
        )
        session.flush()

    client_issue_id = "CLIENT-BDEP-R03"
    if session.get(ClientIssueRow, client_issue_id) is None:
        candidate = session.get(ReleaseCandidateRow, candidate_id)
        session.add(
            ClientIssueRow(
                id=client_issue_id,
                project_id=project_id,
                release_candidate_id=candidate_id,
                baseline_id=baseline_id,
                issue_revision="BDEP-R03",
                purpose="Client Review",
                status=ClientIssueStatus.RELEASED.value,
                manifest_json=candidate.manifest_json,
                issued_at=datetime(2026, 10, 2, 14, 0, 0),
                client_visible=True,
            )
        )

    session.commit()
