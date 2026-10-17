# Tenant data ownership, learning and deployment policy (draft)

## Default boundaries
- **No customer data is used to train or improve shared/global models by default.** This covers P&IDs, legends, extracts, graph data, symbol crops, annotations, review corrections, embeddings, prompts, traces and derived weights.
- **Private-cloud deployments are permanently excluded from our global training pipeline.** Client data and derivatives stay inside the client's approved boundary. Inference is through approved services inside that boundary; no external inference API or raw telemetry by default.
- Managed/shared and dedicated tenants may separately opt in, but only with a documented consent scope, a rights/redistribution review and independent engineering QA. Customer product usage is not model-training consent, and source/legend approval is not permission to train.
- Independent synthetic datasets and properly licensed reference materials may improve shared models after rights and QA checks. Synthetic images based on customer drawing data are **client-derived**, not independent synthetic data.

## Controlled improvement workflow
1. Recognizers place source-anchored uncertain symbol proposals in the client-only review queue.
2. Human reviewers correct/prove labels, ports, valves and topology. Reviews remain tenant-private by default.
3. Before copying any example to shared training storage, a server-side governance decision checks deployment type, tenant identity, data origin, documented consent, explicit rights, agreed purpose and independent QA.
4. Allowed candidates join a versioned training queue. Evaluate using whole-drawing independent holdouts, class-level accuracy, abstention, and graph-topology regressions before release.
5. Promotion to production models requires a separate model release approval. Never auto-retrain cross-client models from a single correction.
6. Maintain source-to-dataset-to-model lineage, consent updates, revocation and deletion records. Revocation blocks **future** training immediately; models already trained may require retraining/retirement under contractual and legal requirements. Do not promise instant unlearning.

## Deployment matrix

| Deployment | Inference | Use client data to train global models | Client knowledge |
| --- | --- | --- | --- |
| Shared managed SaaS | Approved provider / private processing contract | Denied by default; opt-in+rights+QA only | Tenant-isolated |
| Dedicated managed | Dedicated services and contract | Denied by default; opt-in+rights+QA only | Tenant-isolated |
| Private cloud / client-controlled VPC | Within approved boundary | **Always forbidden** | Private; never pooled |

## Production security gates (not yet fulfilled)
- Company-verified tenant identity, SSO/RBAC, server-side authoritative settings; never trust tenant IDs or opt-in flags from client requests.
- Strong isolation of object storage, relational records, vector stores, queues, telemetry, backups, secrets and model artifacts.
- Approved inference-provider no-training/no-retention contracts and transfer/data-residency review; allowlist is insufficient proof.
- Audit access, consent, exports and model lineage; exclude source text/images and sensitive derivatives from generic analytics.
- Restrict client-derived artifacts from public GitHub, pull request attachments and external issue trackers.
- Enforce retention, revocation, deletion, incident response and enterprise agreement constraints.
- Keep external customer upload blocked until authentication, tenant isolation, 2-free-P&ID quota, storage boundaries and audit are tested.

## Implemented code status
`app/tenant_data_governance.py` provides pure, fail-closed **policy decisions only** and synthetic regression tests. **It is not yet plugged into all existing upload, inference or training endpoints.** Production compliance/security enforcement remains blocked until middleware, storage, workers and model registry checks are integrated and validated.
