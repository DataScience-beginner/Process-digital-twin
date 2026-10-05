from __future__ import annotations

import html
from typing import Any

from .revision_models import ClientIssue, EngineeringChangePackage


def _esc(value: Any) -> str:
    if value is None:
        return "—"
    return html.escape(str(value))


def render_revision_control_html(
    *,
    summary: dict[str, Any],
    packages: list[EngineeringChangePackage],
) -> str:
    baseline = summary.get("approved_engineering_baseline") or {}
    queue = summary.get("integration_queue") or []
    client_issues = summary.get("released_client_issues") or []

    package_cards = []
    for package in packages:
        changes = "".join(
            f"""
            <tr>
              <td>{_esc(change.object_id)}</td>
              <td>{_esc(change.property_path)}</td>
              <td>{_esc(change.base_value)} {_esc(change.unit or "")}</td>
              <td>{_esc(change.proposed_value)} {_esc(change.unit or "")}</td>
              <td>{_esc(change.impact_state.value)}</td>
            </tr>
            """
            for change in package.changes
        )
        reviews = "".join(
            f"""
            <tr>
              <td>{_esc(review.sequence)}</td>
              <td>{_esc(review.review_type.value)}</td>
              <td>{_esc(review.discipline)}</td>
              <td>{_esc(review.reviewer_role)}</td>
              <td>{_esc(review.status.value)}</td>
              <td>{_esc(review.reviewer_id)}</td>
            </tr>
            """
            for review in package.reviews
        )
        package_cards.append(
            f"""
            <section class="package">
              <div class="package-head">
                <div>
                  <h2>{_esc(package.id)} — {_esc(package.title)}</h2>
                  <div class="meta">Working Revision {_esc(package.working_revision)} · Base {_esc(package.base_baseline_id)} · {_esc(package.discipline)}</div>
                </div>
                <span class="status">{_esc(package.status.value)}</span>
              </div>
              <div class="meta">Maker: {_esc(package.maker_id)} · Content hash: {_esc(package.content_hash[:16])}…</div>
              <h3>Engineering Change Comparison</h3>
              <div class="scroll"><table><thead><tr><th>Object</th><th>Property</th><th>Approved / Base</th><th>Proposed</th><th>Engineering State</th></tr></thead><tbody>{changes}</tbody></table></div>
              <h3>Engineering Review Package</h3>
              <div class="scroll"><table><thead><tr><th>Seq.</th><th>Review</th><th>Discipline</th><th>Required Role</th><th>Status</th><th>Reviewer</th></tr></thead><tbody>{reviews}</tbody></table></div>
            </section>
            """
        )

    queue_rows = "".join(
        f"<tr><td>{_esc(row['queue_position'])}</td><td>{_esc(row['change_package_id'])}</td><td>{_esc(row['status'])}</td><td>Revalidate against latest Approved Engineering Baseline before integration</td></tr>"
        for row in queue
    ) or '<tr><td colspan="4">No Engineering Change Package is currently queued.</td></tr>'

    issue_rows = "".join(
        f"<tr><td>{_esc(row['issue_revision'])}</td><td>{_esc(row['purpose'])}</td><td>{_esc(row['status'])}</td><td>{_esc(row.get('issued_at'))}</td></tr>"
        for row in client_issues
    ) or '<tr><td colspan="4">No Client Issue released.</td></tr>'

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP — Engineering Revision & Release Control</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#eef1f4;color:#111}}
header{{background:#fff;border-bottom:1px solid #aaa;padding:12px 16px;display:flex;justify-content:space-between}}
header a{{font-size:11px;color:#174a77;text-decoration:none;margin-left:12px}}
main{{max-width:1600px;margin:auto;padding:12px}}
.hero,.package,.panel{{background:#fff;border:1px solid #999;padding:12px;margin-bottom:10px}}
.hero{{display:grid;grid-template-columns:1fr auto;gap:12px}}
.hero h1{{font-size:19px;margin:0}} .meta{{font-size:9px;color:#64748b;margin-top:4px}}
.kpis{{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}} .kpi{{border:1px solid #cbd5e1;padding:6px 8px;font-size:8px}} .kpi b{{display:block;font-size:15px}}
.package-head{{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid #ddd;padding-bottom:7px}} .package h2{{font-size:13px;margin:0}} h3{{font-size:9px;text-transform:uppercase;color:#475569;margin:10px 0 5px}}
.status{{font-size:8px;border:1px solid #94a3b8;border-radius:999px;padding:4px 7px;height:max-content;background:#f8fafc}}
table{{border-collapse:collapse;width:100%;font-size:8.5px}} th,td{{border:1px solid #ddd;padding:5px;text-align:left;vertical-align:top}} th{{background:#f1f5f9}} .scroll{{overflow:auto}}
.rule{{background:#eff6ff;border:1px solid #bfdbfe;padding:9px;font-size:9px;line-height:1.45;margin-top:8px}}
.flow{{font-size:9px;background:#f8fafc;border:1px solid #dbe1e8;padding:9px;line-height:1.7}}
</style></head>
<body>
<header><div><strong>Digital BDEP — Engineering Revision, Review & Client Issue Control</strong><div class="meta">Engineering / digital-plant terminology throughout the user interface.</div></div><nav><a href="/engineering">Engineering Workspace</a><a href="/client">Client View</a></nav></header>
<main>
<section class="hero">
<div><h1>Approved Engineering Baseline: {_esc(baseline.get("revision"))}</h1><div class="meta">Baseline ID {_esc(baseline.get("id"))} · Model hash {_esc((baseline.get("model_hash") or "")[:20])}…</div>
<div class="rule">{_esc(summary.get("client_visibility_rule"))}</div></div>
<div class="kpis"><div class="kpi"><b>{len(packages)}</b>Change Packages</div><div class="kpi"><b>{len(queue)}</b>Integration Queue</div><div class="kpi"><b>{len(client_issues)}</b>Released Client Issues</div></div>
</section>

<section class="panel"><h2 style="font-size:13px;margin:0 0 7px">Engineering lifecycle</h2>
<div class="flow">Approved Engineering Baseline → Engineering Change Package → Engineering Review Package → Discipline Check / Affected-Discipline Review → Engineering Approval Gate → Integration Queue → Approved Engineering Baseline → Release Candidate → Client Issue</div></section>

{"".join(package_cards)}

<section class="panel"><h2 style="font-size:13px;margin:0 0 7px">Integration Queue</h2><table><thead><tr><th>Position</th><th>Engineering Change Package</th><th>Status</th><th>Rule</th></tr></thead><tbody>{queue_rows}</tbody></table></section>
<section class="panel"><h2 style="font-size:13px;margin:0 0 7px">Released Client Issues</h2><table><thead><tr><th>Client Issue</th><th>Purpose</th><th>Status</th><th>Issued</th></tr></thead><tbody>{issue_rows}</tbody></table></section>
</main></body></html>"""


def render_client_issue_portal_html(issues: list[ClientIssue]) -> str:
    issue_cards = []
    for issue in issues:
        manifest = issue.manifest or {}
        pid = ", ".join(manifest.get("pid", [])) or "—"
        pfd = ", ".join(manifest.get("pfd", [])) or "—"
        issue_cards.append(
            f"""
            <section class="issue">
              <div><h2>{_esc(issue.issue_revision)}</h2><div class="meta">{_esc(issue.purpose)} · Issued {_esc(issue.issued_at)}</div></div>
              <span class="released">Released</span>
              <table>
                <tr><th>Approved Engineering Baseline</th><td>{_esc(issue.baseline_id)}</td></tr>
                <tr><th>PFD</th><td>{_esc(pfd)}</td></tr>
                <tr><th>P&ID</th><td>{_esc(pid)}</td></tr>
                <tr><th>Design Basis</th><td>{_esc(manifest.get("design_basis"))}</td></tr>
                <tr><th>Calculations</th><td>{_esc(manifest.get("calculations"))}</td></tr>
              </table>
            </section>
            """
        )

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP — Client Issue Portal</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#f3f4f6;color:#111}} header{{background:#fff;border-bottom:1px solid #aaa;padding:14px 18px}} main{{max-width:1100px;margin:auto;padding:14px}}
h1{{font-size:19px;margin:0}} .meta{{font-size:9px;color:#64748b;margin-top:4px}} .rule{{font-size:9px;background:#eff6ff;border:1px solid #bfdbfe;padding:9px;margin:10px 0;line-height:1.45}}
.issue{{background:#fff;border:1px solid #999;padding:12px;margin-bottom:10px;display:grid;grid-template-columns:1fr auto;gap:9px}} .issue h2{{font-size:15px;margin:0}} .released{{font-size:8px;background:#dcfce7;color:#166534;border-radius:999px;padding:5px 8px;height:max-content}}
table{{grid-column:1/-1;border-collapse:collapse;width:100%;font-size:9px}} th,td{{border:1px solid #ddd;padding:6px;text-align:left}} th{{width:30%;background:#f8fafc}}
</style></head>
<body><header><h1>Digital BDEP — Client Issue Portal</h1><div class="meta">Read-only formally issued engineering information</div></header>
<main><div class="rule">This portal is bound to immutable Client Issues and shows only formally released engineering information for the selected issue revision.</div>
{"".join(issue_cards) if issue_cards else '<section class="issue"><div>No released Client Issue is available.</div></section>'}
</main></body></html>"""
