"""Fail-closed tenant privacy decisions for P&ID agent workflows.

Pure policy component. Callers MUST load TenantPolicy from a trusted server-side
tenant registry, not client-submitted JSON. No content enters decisions/logs.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeploymentMode(StrEnum):
    MANAGED_SHARED = "managed_shared"
    MANAGED_DEDICATED = "managed_dedicated"
    PRIVATE_CLOUD = "private_cloud"


class SourceKind(StrEnum):
    CLIENT_SOURCE = "client_source"
    CLIENT_DERIVED = "client_derived"  # crops, graphs, labels, embeddings, feedback
    INDEPENDENT_SYNTHETIC = "independent_synthetic"
    LICENSED_REFERENCE = "licensed_reference"


class TenantPolicy(BaseModel):
    """Configuration provisioned by an authorized platform administrator."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    tenant_id: str = Field(min_length=1)
    deployment_mode: DeploymentMode
    global_training_opt_in: bool = False
    consent_record_id: str | None = None
    authorized_external_inference_providers: frozenset[str] = frozenset()

    @model_validator(mode="after")
    def reject_inconsistent_policy(self) -> "TenantPolicy":
        if self.deployment_mode == DeploymentMode.PRIVATE_CLOUD:
            if self.global_training_opt_in or self.authorized_external_inference_providers:
                raise ValueError("Private-cloud tenants cannot opt into global training or external inference")
        if self.global_training_opt_in and not self.consent_record_id:
            raise ValueError("Global training opt-in must have an auditable consent record")
        return self


class LearningCandidate(BaseModel):
    """Metadata only; no images, drawing text, or extracted graphs here."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    tenant_id: str = Field(min_length=1)
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_kind: SourceKind
    rights_to_train_confirmed: bool = False
    independent_engineering_qa_passed: bool = False
    purpose_within_consent: bool = False


class GateDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    allowed: bool
    reason: str
    next_action: Literal["none", "request_consent", "rights_review", "qa_review", "deny"]


def may_use_for_global_training(policy: TenantPolicy, candidate: LearningCandidate) -> GateDecision:
    """Gate candidates BEFORE copying to shared ML training datasets.

    The private-cloud ban wins even for apparently public source entries in a
    private customer workspace. Model-release, lineage and revocation are
    separate workflows and must be implemented before production use.
    """
    if candidate.tenant_id != policy.tenant_id:
        return GateDecision(allowed=False, reason="tenant_mismatch", next_action="deny")
    if policy.deployment_mode == DeploymentMode.PRIVATE_CLOUD:
        return GateDecision(allowed=False, reason="private_cloud_never_global_train", next_action="deny")

    from_client = candidate.source_kind in {SourceKind.CLIENT_SOURCE, SourceKind.CLIENT_DERIVED}
    if from_client and (not policy.global_training_opt_in or not policy.consent_record_id):
        return GateDecision(allowed=False, reason="explicit_training_consent_required", next_action="request_consent")
    if not candidate.rights_to_train_confirmed or (from_client and not candidate.purpose_within_consent):
        return GateDecision(allowed=False, reason="rights_or_scope_not_verified", next_action="rights_review")
    if not candidate.independent_engineering_qa_passed:
        return GateDecision(allowed=False, reason="independent_qa_required", next_action="qa_review")
    return GateDecision(allowed=True, reason="candidate_eligible_for_reviewed_training_queue", next_action="none")


def may_send_to_external_inference(policy: TenantPolicy, provider_id: str) -> GateDecision:
    """Inference permission is separate from training consent.

    Providers also need independently verified zero-training/retention terms.
    A tenant allowlist does not itself establish the contract or data security.
    """
    if policy.deployment_mode == DeploymentMode.PRIVATE_CLOUD:
        return GateDecision(allowed=False, reason="private_cloud_no_external_inference", next_action="deny")
    if not provider_id or provider_id not in policy.authorized_external_inference_providers:
        return GateDecision(allowed=False, reason="provider_not_allowlisted", next_action="deny")
    return GateDecision(allowed=True, reason="tenant_provider_allowlisted_requires_platform_contract_check", next_action="none")
