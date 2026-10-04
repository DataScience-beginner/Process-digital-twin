from __future__ import annotations

import html
from typing import Any

from .thread_models import ObjectDossier


PRIMARY_EQUIPMENT = {
    "EQ-V101": [
        "VLV-PSV101",
        "VLV-LCV101",
        "INS-PT101",
        "INS-LT101",
        "INS-LIC101",
    ],
    "EQ-P101": [
        "VLV-FCV101",
        "INS-FT101",
        "INS-FIC101",
    ],
}


def _contains_tbd(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return any(_contains_tbd(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_tbd(v) for v in value)
    return "TBD" in str(value).upper()


def _records(dossier: ObjectDossier, domain: str):
    for key, records in dossier.records.items():
        if key.value == domain:
            return records
    return []


def _bundle(
    dossiers: dict[str, ObjectDossier],
    parent_id: str,
) -> list[ObjectDossier]:
    ids = [parent_id, *PRIMARY_EQUIPMENT.get(parent_id, [])]
    return [dossiers[item_id] for item_id in ids if item_id in dossiers]


def _bundle_records(bundle: list[ObjectDossier], domain: str):
    return [
        record
        for dossier in bundle
        for record in _records(dossier, domain)
    ]


def _direct_cost(dossier: ObjectDossier) -> tuple[float | None, str | None]:
    candidates = [
        record
        for record in _records(dossier, "cost")
        if isinstance(record.value, (int, float))
    ]
    if not candidates:
        return None, None
    record = candidates[0]
    return float(record.value), record.unit


def _status_cell(ok: bool, label: str = "Ready") -> str:
    css = "ok" if ok else "pending"
    text = label if ok else "Pending"
    return f'<span class="pill {css}">{html.escape(text)}</span>'


def render_dashboard_html(
    dossiers: dict[str, ObjectDossier],
    stages: list,
) -> str:
    stage_cards = []
    for stage in stages:
        item = stage.model_dump(mode="json") if hasattr(stage, "model_dump") else stage
        published = item.get("status") == "published"
        stage_cards.append(
            f"""
            <div class="stage-card">
              <div class="stage-name">{html.escape(item.get("label") or item.get("stage", ""))}</div>
              {_status_cell(published, "Published")}
              <div class="stage-meta">Rev {html.escape(str(item.get("revision") or "—"))}</div>
            </div>
            """
        )

    equipment_rows = []
    outstanding_count = 0
    total_currency = "USD"

    for parent_id, child_ids in PRIMARY_EQUIPMENT.items():
        dossier = dossiers.get(parent_id)
        if dossier is None:
            continue

        bundle = _bundle(dossiers, parent_id)
        process_records = _bundle_records(bundle, "process_calculation")
        inst_records = _bundle_records(bundle, "instrumentation")
        mech_records = _bundle_records(bundle, "mechanical")
        cost_records = _bundle_records(bundle, "cost")
        epc_records = _bundle_records(bundle, "epc_vendor")

        direct_cost, currency = _direct_cost(dossier)
        if currency:
            total_currency = currency

        tbd = sum(
            1
            for member in bundle
            for records in member.records.values()
            for record in records
            if _contains_tbd(record.value)
            or "placeholder" in record.status.lower()
        )
        outstanding_count += tbd

        child_tags = [
            dossiers[child_id].tag
            for child_id in child_ids
            if child_id in dossiers
        ]
        direct_cost_text = (
            f"{html.escape(currency or '')} {direct_cost:,.2f}"
            if direct_cost is not None
            else "—"
        )

        equipment_rows.append(
            f"""
            <tr>
              <td>
                <a href="/object/{html.escape(dossier.object_id)}/detail"><b>{html.escape(dossier.tag)}</b></a>
                <div class="small">{html.escape(dossier.service or "")}</div>
              </td>
              <td>{html.escape(dossier.object_type or dossier.category)}</td>
              <td><div class="child-list">{html.escape(" · ".join(child_tags) or "—")}</div></td>
              <td>{_status_cell(bool(dossier.design_basis))}</td>
              <td>{_status_cell(bool(process_records))}</td>
              <td>{_status_cell(bool(inst_records))}</td>
              <td>{_status_cell(bool(mech_records))}</td>
              <td>{_status_cell(bool(cost_records))}</td>
              <td>{_status_cell(bool(epc_records), "Started")}</td>
              <td>{direct_cost_text}</td>
              <td>{tbd}</td>
            </tr>
            """
        )

    package_total = None
    for dossier in dossiers.values():
        for record in _records(dossier, "cost"):
            if record.id == "COST-PACKAGE-TOTAL" and isinstance(record.value, dict):
                package_total = record.value
                break
        if package_total:
            break

    project_total = package_total.get("total") if package_total else 0.0
    if package_total:
        total_currency = package_total.get("currency") or total_currency

    published_count = sum(
        1
        for stage in stages
        if (stage.status if hasattr(stage, "status") else stage.get("status"))
        == "published"
    )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP Dashboard</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#eef1f4;color:#111}}
header{{background:#fff;border-bottom:1px solid #bbb;padding:13px 17px;display:flex;justify-content:space-between;align-items:center}}
header a{{font-size:12px;color:#174a77;text-decoration:none;margin-left:12px}}
main{{padding:14px;max-width:1500px;margin:auto}}
.cards{{display:grid;grid-template-columns:repeat(4,minmax(170px,1fr));gap:10px}}
.card{{background:#fff;border:1px solid #aaa;padding:14px;border-radius:6px}}
.big{{font-size:24px;font-weight:700}} .label{{font-size:10px;color:#64748b;text-transform:uppercase;margin-bottom:5px}}
.stage-grid{{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:8px;margin-top:10px}}
.stage-card{{background:#fff;border:1px solid #cbd5e1;border-radius:5px;padding:9px}}
.stage-name{{font-size:11px;font-weight:700;margin-bottom:5px}} .stage-meta{{font-size:9px;color:#64748b;margin-top:4px}}
.pill{{display:inline-block;font-size:9px;border-radius:999px;padding:3px 6px}} .pill.ok{{background:#dcfce7;color:#166534}} .pill.pending{{background:#fef3c7;color:#92400e}}
.panel{{background:#fff;border:1px solid #aaa;margin-top:12px;padding:12px}}
h2{{font-size:14px;margin:0 0 9px}} table{{border-collapse:collapse;width:100%;font-size:10px}}
th,td{{border:1px solid #ddd;padding:6px;text-align:left;vertical-align:top}} th{{background:#f1f5f9}}
a{{color:#174a77;text-decoration:none}} .small{{font-size:9px;color:#64748b;margin-top:2px}}
.note{{font-size:9px;color:#64748b;margin-top:7px}} .child-list{{font-size:9px;color:#475569;line-height:1.4}}
@media(max-width:900px){{.cards,.stage-grid{{grid-template-columns:1fr 1fr}}}}
</style>
</head>
<body>
<header>
<div><strong>Digital BDEP — Project / Section Dashboard</strong><div class="small">Primary equipment completion with child discipline objects rolled up underneath</div></div>
<nav><a href="/engineering">Engineering View</a><a href="/configuration-match/CASE-NORMAL">Configuration</a></nav>
</header>
<main>
<div class="cards">
<div class="card"><div class="label">Published stages</div><div class="big">{published_count} / {len(stages)}</div></div>
<div class="card"><div class="label">Primary equipment</div><div class="big">{len(equipment_rows)}</div><div class="note">Small valves/instruments are child objects, not separate major equipment rows.</div></div>
<div class="card"><div class="label">Demo project/section estimate</div><div class="big">{html.escape(str(total_currency))} {float(project_total or 0):,.0f}</div><div class="note">Non-commercial demo cost model</div></div>
<div class="card"><div class="label">Outstanding / TBD records</div><div class="big">{outstanding_count}</div></div>
</div>

<section class="panel">
<h2>Publication Stages</h2>
<div class="stage-grid">{"".join(stage_cards)}</div>
</section>

<section class="panel">
<h2>Primary Equipment Completion Matrix</h2>
<div style="overflow:auto"><table>
<thead><tr>
<th>Equipment</th><th>Type</th><th>Associated P&ID / Discipline Objects</th><th>Design Basis</th><th>Process / Safety</th><th>Instrumentation / DCS</th><th>Technical / Mechanical</th><th>Cost Estimate</th><th>EPC / Vendor</th><th>Direct Equipment Cost</th><th>TBD / Gated</th>
</tr></thead>
<tbody>{"".join(equipment_rows)}</tbody>
</table></div>
<div class="note">PSV, control valves and instrument bubbles remain individually traceable in the Digital Thread, but dashboard completion rolls them into their parent equipment/system instead of treating them as separate major equipment.</div>
</section>
</main>
</body></html>"""
