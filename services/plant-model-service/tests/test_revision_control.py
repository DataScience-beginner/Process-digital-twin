import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_schema import (
    EngineeringReviewRequirementRow,
    create_schema,
)
from app.persistence import PROJECT_ID, seed_demo_database
from app.revision_control import (
    RevisionControlBlocked,
    client_issue_catalog,
    integration_readiness,
    load_change_package,
    record_engineering_review,
    revision_control_summary,
    seed_revision_control_demo,
)
from app.revision_control_renderer import (
    render_client_issue_portal_html,
    render_revision_control_html,
)
from app.revision_models import EngineeringReviewStatus


def _engine():
    engine = create_schema("sqlite+pysqlite:///:memory:")
    seed_demo_database(engine)
    with Session(engine) as session:
        seed_revision_control_demo(session, PROJECT_ID)
    return engine


def test_engineering_revision_control_uses_plant_engineering_nomenclature():
    engine = _engine()
    with Session(engine) as session:
        summary = revision_control_summary(session, PROJECT_ID)

    terminology = summary["terminology"]
    assert terminology["approved_engineering_baseline"] == "Approved Engineering Baseline"
    assert terminology["engineering_change_package"] == "Engineering Change Package"
    assert terminology["engineering_review_package"] == "Engineering Review Package"
    assert terminology["discipline_check"] == "Discipline Check"
    assert terminology["engineering_approval_gate"] == "Engineering Approval Gate"
    assert terminology["integration_queue"] == "Integration Queue"
    assert terminology["client_issue"] == "Client Issue"
    assert terminology["affected_update_required"] == "Affected / Update Required"

    user_terms = " ".join(terminology.values()).lower()
    for software_term in ["pull request", "commit", "merge request", "checkout"]:
        assert software_term not in user_terms


def test_demo_has_approved_baseline_concurrent_change_packages_and_integration_queue():
    engine = _engine()
    with Session(engine) as session:
        summary = revision_control_summary(session, PROJECT_ID)

    assert summary["approved_engineering_baseline"]["revision"] == "BDEP-R03"
    assert {row["id"] for row in summary["engineering_change_packages"]} == {
        "ECP-2026-0138",
        "ECP-2026-0142",
    }
    assert summary["integration_queue"][0]["change_package_id"] == "ECP-2026-0138"
    assert summary["integration_queue"][0]["status"] == "queued"


def test_engineering_change_package_is_semantic_not_document_diff():
    engine = _engine()
    with Session(engine) as session:
        package = load_change_package(session, "ECP-2026-0142")

    by_object = {change.object_id: change for change in package.changes}
    assert by_object["STR-S102"].property_path == "cases.maximum.mass_flow"
    assert by_object["STR-S102"].base_value == 92.0
    assert by_object["STR-S102"].proposed_value == 110.0
    assert by_object["EQ-P101"].property_path == "rated_flow"
    assert by_object["VLV-FCV101"].impact_state.value == "update_required"
    assert by_object["VLV-PSV101"].impact_state.value == "affected"


def test_maker_cannot_approve_own_change_package():
    engine = _engine()
    with Session(engine) as session:
        pending = session.scalars(
            select(EngineeringReviewRequirementRow).where(
                EngineeringReviewRequirementRow.change_package_id == "ECP-2026-0142",
                EngineeringReviewRequirementRow.status == "pending",
            )
        ).first()
        with pytest.raises(RevisionControlBlocked, match="Maker cannot"):
            record_engineering_review(
                session,
                review_requirement_id=pending.id,
                reviewer_id="process-sizing-agent-07",
                decision=EngineeringReviewStatus.APPROVED,
            )


def test_reviews_are_bound_to_exact_change_content_hash():
    engine = _engine()
    with Session(engine) as session:
        package = load_change_package(session, "ECP-2026-0142")
        checked = next(
            review
            for review in package.reviews
            if review.status == EngineeringReviewStatus.APPROVED
        )

    assert checked.reviewed_content_hash == package.content_hash


def test_integration_is_blocked_until_reviews_and_update_required_items_are_closed():
    engine = _engine()
    with Session(engine) as session:
        readiness = integration_readiness(session, "ECP-2026-0142")

    assert readiness["ready_for_integration"] is False
    assert "VLV-FCV101" in readiness["update_required_objects"]
    assert readiness["review_failures"]


def test_client_catalog_exposes_released_issue_only_not_internal_change_packages():
    engine = _engine()
    with Session(engine) as session:
        issues = client_issue_catalog(session, PROJECT_ID)
        summary = revision_control_summary(session, PROJECT_ID)

    assert len(issues) == 1
    assert issues[0].issue_revision == "BDEP-R03"
    assert issues[0].status.value == "released"

    client_payload = json.dumps(
        [issue.model_dump(mode="json") for issue in issues],
        default=str,
    )
    assert "ECP-2026-0142" not in client_payload
    assert "ECP-2026-0138" not in client_payload
    assert "working_revision" not in client_payload
    assert "integration_queue" not in client_payload

    assert "released Client Issues only" in summary["client_visibility_rule"]


def test_internal_and_client_views_are_separate():
    engine = _engine()
    with Session(engine) as session:
        summary = revision_control_summary(session, PROJECT_ID)
        packages = [
            load_change_package(session, row["id"])
            for row in summary["engineering_change_packages"]
        ]
        issues = client_issue_catalog(session, PROJECT_ID)

    internal_html = render_revision_control_html(
        summary=summary,
        packages=packages,
    )
    client_html = render_client_issue_portal_html(issues)

    assert "Engineering Change Package" in internal_html
    assert "Integration Queue" in internal_html
    assert "ECP-2026-0142" in internal_html

    assert "Client Issue Portal" in client_html
    assert "BDEP-R03" in client_html
    assert "ECP-2026-0142" not in client_html
    assert "Integration Queue" not in client_html
    assert "internal reviews" in client_html
