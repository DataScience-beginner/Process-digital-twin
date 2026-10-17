"""Synthetic-only tenant privacy regressions; no client fixtures."""
import pytest
from pydantic import ValidationError

from app.tenant_data_governance import (
    LearningCandidate, SourceKind, TenantPolicy,
    may_send_to_external_inference, may_use_for_global_training,
)

HASH = "a" * 64


def policy(**kwargs):
    return TenantPolicy(tenant_id="tenant-a", deployment_mode="managed_shared", **kwargs)


def candidate(**kwargs):
    return LearningCandidate(tenant_id="tenant-a", artifact_sha256=HASH,
                             source_kind=SourceKind.CLIENT_DERIVED, **kwargs)


def test_private_cloud_never_global_trains_even_if_candidate_qa_and_rights_clear():
    p = TenantPolicy(tenant_id="tenant-a", deployment_mode="private_cloud")
    c = candidate(rights_to_train_confirmed=True, independent_engineering_qa_passed=True,
                  purpose_within_consent=True)
    assert may_use_for_global_training(p, c).reason == "private_cloud_never_global_train"


def test_private_cloud_cannot_enable_opt_in_or_external_provider():
    with pytest.raises(ValidationError):
        TenantPolicy(tenant_id="tenant-a", deployment_mode="private_cloud",
                     global_training_opt_in=True, consent_record_id="signed-123")
    with pytest.raises(ValidationError):
        TenantPolicy(tenant_id="tenant-a", deployment_mode="private_cloud",
                     authorized_external_inference_providers=frozenset({"external"}))


def test_default_managed_policy_denies_client_learning():
    assert may_use_for_global_training(policy(), candidate()).reason == "explicit_training_consent_required"


def test_client_derived_crops_embeddings_and_feedback_need_consent():
    assert may_use_for_global_training(policy(), candidate(rights_to_train_confirmed=True)).allowed is False


def test_opt_in_requires_record_and_scope_and_source_rights():
    with pytest.raises(ValidationError):
        policy(global_training_opt_in=True)
    p = policy(global_training_opt_in=True, consent_record_id="signed-123")
    assert may_use_for_global_training(p, candidate()).reason == "rights_or_scope_not_verified"
    assert may_use_for_global_training(p, candidate(rights_to_train_confirmed=True)).reason == "rights_or_scope_not_verified"


def test_independent_qa_mandatory_even_with_consent_and_rights():
    p = policy(global_training_opt_in=True, consent_record_id="signed-123")
    c = candidate(rights_to_train_confirmed=True, purpose_within_consent=True)
    assert may_use_for_global_training(p, c).reason == "independent_qa_required"


def test_approved_client_candidate_is_eligible_not_automatically_trained():
    p = policy(global_training_opt_in=True, consent_record_id="signed-123")
    c = candidate(rights_to_train_confirmed=True, purpose_within_consent=True,
                  independent_engineering_qa_passed=True)
    assert may_use_for_global_training(p, c).reason == "candidate_eligible_for_reviewed_training_queue"


def test_tenant_mismatch_denies_even_public_reference():
    c = LearningCandidate(tenant_id="tenant-b", artifact_sha256=HASH,
                          source_kind="licensed_reference", rights_to_train_confirmed=True,
                          independent_engineering_qa_passed=True)
    assert may_use_for_global_training(policy(), c).reason == "tenant_mismatch"


def test_independent_synthetic_can_be_reviewed_without_customer_opt_in():
    c = LearningCandidate(tenant_id="tenant-a", artifact_sha256=HASH,
                          source_kind="independent_synthetic", rights_to_train_confirmed=True,
                          independent_engineering_qa_passed=True)
    assert may_use_for_global_training(policy(), c).allowed is True


def test_private_cloud_external_inference_denied():
    p = TenantPolicy(tenant_id="tenant-a", deployment_mode="private_cloud")
    assert not may_send_to_external_inference(p, "external").allowed


def test_managed_provider_is_deny_by_default_and_allowlist_is_not_training_consent():
    assert not may_send_to_external_inference(policy(), "external").allowed
    p = policy(authorized_external_inference_providers=frozenset({"approved-provider"}))
    assert may_send_to_external_inference(p, "approved-provider").allowed
    assert not may_send_to_external_inference(p, "other").allowed
    assert not may_use_for_global_training(p, candidate()).allowed


def test_invalid_candidate_metadata_rejected():
    with pytest.raises(ValidationError):
        LearningCandidate(tenant_id="tenant-a", artifact_sha256="fake", source_kind="client_source")
