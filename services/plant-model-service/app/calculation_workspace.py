from __future__ import annotations

import html
from typing import Any

from .hazop import hazop_rows_for_entity
from .thread_models import ObjectDossier, RecordDomain


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(_fmt(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_fmt(val)}" for key, val in value.items())
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _table(rows: list[dict[str, Any]], *, preferred: list[str] | None = None) -> str:
    if not rows:
        return '<div class="empty">No data.</div>'
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    if preferred:
        keys = [key for key in preferred if key in keys] + [key for key in keys if key not in preferred]
    head = "".join(f"<th>{html.escape(key.replace('_', ' ').title())}</th>" for key in keys)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(_fmt(row.get(key)))}</td>" for key in keys) + "</tr>"
        for row in rows
    )
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _name_value(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">No data.</div>'
    body = []
    for row in rows:
        label = row.get("name") or row.get("criterion_id") or row.get("field") or "Item"
        value = _fmt(row.get("value"))
        unit = row.get("unit")
        if unit:
            value = f"{value} {unit}"
        extra = []
        if row.get("source"):
            extra.append(f"Source: {row['source']}")
        if row.get("criterion_id") and row.get("name"):
            extra.append(f"ID: {row['criterion_id']}")
        note = f'<div class="source">{" · ".join(html.escape(item) for item in extra)}</div>' if extra else ""
        body.append(
            f'<div class="nv"><div class="nv-name">{html.escape(str(label))}</div>'
            f'<div class="nv-value">{html.escape(value)}{note}</div></div>'
        )
    return '<div class="nvgrid">' + "".join(body) + "</div>"


def _trace(detail: dict[str, Any]) -> str:
    trace = detail.get("trace")
    if not isinstance(trace, dict):
        return '<div class="empty">No step-by-step trace has been published for this record yet.</div>'

    steps = trace.get("steps") or []
    step_rows = []
    for step in steps:
        step_rows.append(
            {
                "step": step.get("step"),
                "title": step.get("title"),
                "equation": step.get("equation"),
                "substitution": step.get("substitution"),
                "result": _fmt(step.get("result")),
                "unit": step.get("unit"),
                "note": step.get("note"),
            }
        )

    checks = trace.get("validation_checks") or []
    selection = trace.get("selection_checks") or []
    assumptions = trace.get("assumptions") or []
    limitations = trace.get("limitations") or []
    consumers = trace.get("downstream_consumers") or []

    return f"""
    <div class="trace-banner">
      <b>Trace ID:</b> {html.escape(_fmt(trace.get("trace_id")))}
      <span>Service: {html.escape(_fmt(trace.get("service_version")))}</span>
      <span>Qualification: {html.escape(_fmt(trace.get("qualification")))}</span>
    </div>
    <section class="calc-section">
      <h4>Input Sources / Provenance</h4>
      {_table(trace.get("input_sources") or [], preferred=["source","item","field","criterion_id","value","unit"])}
    </section>
    <section class="calc-section">
      <h4>Calculation Steps</h4>
      {_table(step_rows, preferred=["step","title","equation","substitution","result","unit","note"])}
    </section>
    <section class="calc-section">
      <h4>Candidate / Selection Checks</h4>
      {_table(selection)}
    </section>
    <section class="calc-section">
      <h4>Validation Checks</h4>
      {_table(checks, preferred=["check","actual","criterion","result"])}
    </section>
    <div class="triple">
      <section class="calc-section"><h4>Assumptions</h4><ul>{"".join(f"<li>{html.escape(str(x))}</li>" for x in assumptions) or "<li>—</li>"}</ul></section>
      <section class="calc-section gate"><h4>Limitations / Gates</h4><ul>{"".join(f"<li>{html.escape(str(x))}</li>" for x in limitations) or "<li>—</li>"}</ul></section>
      <section class="calc-section"><h4>Downstream Consumers</h4><ul>{"".join(f"<li>{html.escape(str(x))}</li>" for x in consumers) or "<li>—</li>"}</ul></section>
    </div>
    """


def _record(record) -> str:
    detail = (record.metadata or {}).get("calculation_detail")
    value = record.value
    value_html = _table([value]) if isinstance(value, dict) else f'<div class="record-value">{html.escape(_fmt(value))} {html.escape(record.unit or "")}</div>'

    if not isinstance(detail, dict):
        return f"""
        <article class="calc-card">
          <div class="calc-head"><div><h3>{html.escape(record.name)}</h3><div class="sub">{html.escape(record.id)}</div></div><span class="status">{html.escape(record.status)}</span></div>
          {value_html}
          <div class="source">Source: {html.escape(record.provenance.source_id)} · {html.escape(record.provenance.method or "")}</div>
        </article>
        """

    scenarios = detail.get("relief_scenarios") or []
    return f"""
    <article class="calc-card">
      <div class="calc-head">
        <div><h3>{html.escape(record.name)}</h3><div class="sub">{html.escape(record.id)} · Source {html.escape(record.provenance.source_id)}</div></div>
        <span class="status">{html.escape(record.status)}</span>
      </div>
      <div class="resultbar">{value_html}</div>
      <div class="two">
        <section class="calc-section"><h4>Inputs</h4>{_name_value(detail.get("inputs") or [])}</section>
        <section class="calc-section"><h4>Criteria / Limits</h4>{_name_value(detail.get("criteria") or [])}</section>
      </div>
      <section class="calc-section"><h4>Cases / Operating Envelope</h4>{_table(detail.get("case_results") or [])}</section>
      {f'<section class="calc-section relief"><h4>Relief Scenario Register</h4>{_table(scenarios, preferred=["scenario","why_considered","screening_status","screening_load_tph","basis","result","data_gap"])}</section>' if scenarios else ""}
      <div class="governing"><b>Governing / selected case:</b> {html.escape(_fmt(detail.get("governing_case") or detail.get("preliminary_selected_scenario")))}<br>
      <b>Why:</b> {html.escape(_fmt(detail.get("governing_reason") or detail.get("selection_reason")))}</div>
      <section class="calc-section"><h4>Final Outputs / Selection</h4>{_name_value(detail.get("outputs") or [])}</section>
      <section class="calc-section"><h4>Method</h4><div class="method">{html.escape(_fmt(detail.get("method")))}</div></section>
      <section class="calc-section trace"><h4>Full Calculation Trace</h4>{_trace(detail)}</section>
    </article>
    """


def _records(dossier: ObjectDossier | None, domain: RecordDomain) -> list:
    if dossier is None:
        return []
    return dossier.records.get(domain, [])


def _discipline_body(dossier: ObjectDossier | None, domain: RecordDomain) -> str:
    rows = _records(dossier, domain)
    if not rows:
        return '<div class="empty">No published records in this discipline.</div>'
    return "".join(_record(record) for record in rows)


def _hazop(entity_id: str) -> str:
    rows = hazop_rows_for_entity(entity_id)
    if not rows:
        return '<div class="empty">No HAZOP rows are currently linked to this entity.</div>'
    parts = []
    for row in rows:
        cause_text = "; ".join(item["text"] for item in row["causes"])
        safeguard_text = "; ".join(item["text"] for item in row["safeguards"])
        parts.append(
            f"""
            <tr>
              <td>{html.escape(row["node_id"])}<br><span class="sub">{html.escape(row["node_name"])}</span></td>
              <td>{html.escape(row["guideword"])}</td>
              <td>{html.escape(row["parameter"])}</td>
              <td>{html.escape(row["deviation"])}</td>
              <td>{html.escape(cause_text)}</td>
              <td>{html.escape("; ".join(row["consequences"]))}</td>
              <td>{html.escape(safeguard_text)}</td>
              <td>{html.escape(row["recommendation"])}</td>
              <td>{html.escape(row["risk"])}</td>
              <td>{html.escape(row["status"])}</td>
            </tr>
            """
        )
    return f"""
    <div class="hazop-note"><b>HAZOP support rule:</b> the Digital Thread pre-populates node intent, possible causes, safeguards and linked calculations. The multidisciplinary HAZOP team owns the final deviation review, risk ranking and action closure.</div>
    <div class="scroll"><table><thead><tr>
    <th>Node</th><th>Guideword</th><th>Parameter</th><th>Deviation</th><th>Candidate Causes</th><th>Consequences</th><th>Existing Safeguards</th><th>Recommendation / Action</th><th>Risk</th><th>Status</th>
    </tr></thead><tbody>{"".join(parts)}</tbody></table></div>
    """


def render_calculation_workspace_html(
    *,
    entity: dict[str, Any],
    dossier: ObjectDossier | None,
) -> str:
    entity_id = entity["id"]
    tag = entity.get("tag") or entity_id
    type_text = entity.get("object_type") or entity.get("category") or "entity"
    service = entity.get("service") or ""

    line_record = None
    if entity.get("record_metadata"):
        class _P:
            source_id = entity.get("id")
            method = "linked line engineering record"
        class _R:
            id = entity.get("id")
            name = "Line sizing / engineering calculation"
            value = entity.get("record_value")
            unit = None
            status = entity.get("status") or "published"
            provenance = _P()
            metadata = entity.get("record_metadata") or {}
        line_record = _R()

    tabs = [
        ("process", "Process / Safety"),
        ("instrumentation", "Instrumentation / DCS"),
        ("mechanical", "Technical / Mechanical"),
        ("electrical", "Electrical"),
        ("cost", "Cost Estimate"),
        ("vendor", "Vendor / EPC"),
        ("operations", "Operations"),
        ("hazop", "HAZOP"),
        ("audit", "Provenance / Audit"),
    ]

    pane_content: dict[str, str] = {}
    process_records = _discipline_body(dossier, RecordDomain.PROCESS_CALC)
    if line_record is not None:
        process_records = _record(line_record) + process_records
    pane_content["process"] = process_records
    pane_content["instrumentation"] = _discipline_body(dossier, RecordDomain.INSTRUMENTATION)
    pane_content["mechanical"] = _discipline_body(dossier, RecordDomain.MECHANICAL)
    pane_content["electrical"] = _discipline_body(dossier, RecordDomain.ELECTRICAL)
    pane_content["cost"] = _discipline_body(dossier, RecordDomain.COST)
    pane_content["vendor"] = _discipline_body(dossier, RecordDomain.EPC_VENDOR)
    pane_content["operations"] = _discipline_body(dossier, RecordDomain.OPERATIONS)
    pane_content["hazop"] = _hazop(entity_id)

    audit_rows = []
    if dossier:
        for criterion in dossier.design_basis:
            audit_rows.append({
                "type": "Design Basis",
                "id": criterion.id,
                "name": criterion.name,
                "status": criterion.status.value,
                "source": criterion.provenance.source_id,
                "revision": criterion.provenance.source_revision,
            })
        for records in dossier.records.values():
            for record in records:
                audit_rows.append({
                    "type": record.domain.value,
                    "id": record.id,
                    "name": record.name,
                    "status": record.status,
                    "source": record.provenance.source_id,
                    "revision": record.provenance.source_revision,
                })
    if line_record is not None:
        audit_rows.append({
            "type": "line_calculation",
            "id": line_record.id,
            "name": line_record.name,
            "status": line_record.status,
            "source": entity_id,
            "revision": "A",
        })
    pane_content["audit"] = _table(audit_rows)

    basis_rows = []
    if dossier:
        basis_rows = [
            {
                "criterion_id": criterion.id,
                "criterion": criterion.name,
                "value": criterion.value,
                "unit": criterion.unit,
                "revision": criterion.revision,
                "status": criterion.status.value,
                "source": criterion.provenance.source_id,
            }
            for criterion in dossier.design_basis
        ]

    connections = []
    for key, title in [("from","FROM"),("through","THROUGH"),("to","TO")]:
        value = entity.get(key)
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        for ref in values:
            connections.append({
                "relationship": title,
                "entity": ref.get("label") or ref.get("id"),
                "entity_id": ref.get("id"),
                "type": ref.get("object_type") or ref.get("category"),
                "service": ref.get("service"),
            })
    for ref in entity.get("connected_lines") or []:
        connections.append({
            "relationship": "CONNECTED LINE",
            "entity": ref.get("label"),
            "entity_id": ref.get("id"),
            "type": ref.get("object_type"),
            "service": ref.get("service"),
        })

    tabs_html = "".join(
        f'<button class="tab {"active" if i == 0 else ""}" data-tab="{tab_id}" onclick="showTab(\'{tab_id}\',this)">{html.escape(label)}</button>'
        for i, (tab_id, label) in enumerate(tabs)
    )
    panes_html = "".join(
        f'<section id="pane-{tab_id}" class="pane {"active" if i == 0 else ""}">{pane_content[tab_id]}</section>'
        for i, (tab_id, _) in enumerate(tabs)
    )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(tag)} — Engineering Calculation Workspace</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#e9edf1;color:#111}}
header{{background:#fff;border-bottom:1px solid #aaa;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:20}}
header a{{font-size:11px;color:#174a77;text-decoration:none;margin-left:12px}}
main{{max-width:1500px;margin:auto;padding:12px}}
.hero{{background:#fff;border:1px solid #888;padding:14px;display:grid;grid-template-columns:1fr auto;gap:12px}}
.hero h1{{margin:0;font-size:22px}} .sub{{font-size:9px;color:#64748b;margin-top:4px}}
.badge{{font-size:9px;border-radius:999px;background:#dcfce7;color:#166534;padding:5px 8px;height:max-content}}
.toolbar{{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}} .toolbar a,.toolbar button{{font-size:9px;padding:6px 8px;border:1px solid #94a3b8;background:#fff;border-radius:4px;color:#174a77;text-decoration:none;cursor:pointer}}
.topgrid{{display:grid;grid-template-columns:1.2fr 1fr;gap:10px;margin-top:10px}}
.panel{{background:#fff;border:1px solid #aaa;padding:10px}} .panel h2{{font-size:12px;margin:0 0 8px}}
.tabs{{display:flex;gap:4px;flex-wrap:wrap;background:#fff;border:1px solid #aaa;padding:8px;margin-top:10px;position:sticky;top:58px;z-index:10}}
.tab{{font-size:9px;padding:6px 8px;border:1px solid #94a3b8;background:#fff;border-radius:4px;cursor:pointer}} .tab.active{{background:#0f172a;color:#fff}}
.pane{{display:none;margin-top:10px}} .pane.active{{display:block}}
.calc-card{{background:#fff;border:1px solid #7d8791;margin-bottom:12px;padding:12px}}
.calc-head{{display:flex;justify-content:space-between;gap:10px;border-bottom:2px solid #cbd5e1;padding-bottom:8px}} .calc-head h3{{font-size:13px;margin:0}}
.status{{font-size:8px;padding:4px 6px;border-radius:999px;background:#e2e8f0;height:max-content}}
.resultbar{{margin-top:8px;background:#f8fafc;border:1px solid #dbe1e8;padding:8px}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:8px}} .triple{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}}
.calc-section{{margin-top:9px;border:1px solid #dbe1e8;padding:8px}} .calc-section h4{{font-size:9px;text-transform:uppercase;color:#334155;margin:0 0 7px}}
.calc-section.gate{{background:#fffbeb}} .relief{{border-color:#f59e0b}} .trace{{border-width:2px;border-color:#93c5fd}}
.trace-banner{{font-size:9px;background:#eff6ff;border:1px solid #bfdbfe;padding:7px;display:flex;gap:14px;flex-wrap:wrap}}
.nvgrid{{border:1px solid #e5e7eb}} .nv{{display:grid;grid-template-columns:44% 56%;border-top:1px solid #e5e7eb;font-size:9px}} .nv:first-child{{border-top:0}}
.nv-name{{background:#f8fafc;padding:5px;font-weight:600}} .nv-value{{padding:5px}} .source{{font-size:8px;color:#64748b;margin-top:2px}}
table{{border-collapse:collapse;width:100%;font-size:8.5px}} th,td{{border:1px solid #ddd;padding:5px;text-align:left;vertical-align:top}} th{{background:#f1f5f9}}
.scroll{{overflow:auto}} .governing{{background:#fffbeb;border:1px solid #fde68a;padding:8px;margin-top:8px;font-size:9px;line-height:1.5}}
.method{{font-size:9px;line-height:1.5}} .empty{{font-size:9px;color:#64748b;padding:8px}}
.hazop-note{{background:#eff6ff;border:1px solid #bfdbfe;padding:9px;font-size:9px;margin-bottom:8px}}
ul{{font-size:9px;line-height:1.5;margin:0;padding-left:18px}}
@media(max-width:900px){{.topgrid,.two,.triple{{grid-template-columns:1fr}}}}
@media print{{header,.toolbar,.tabs{{display:none}} body{{background:#fff}} main{{max-width:none;padding:0}} .pane{{display:block!important}} .calc-card,.panel,.hero{{break-inside:avoid;border-color:#999}}}}
</style>
</head>
<body>
<header>
<div><strong>Digital BDEP — Engineering Calculation & Datasheet Workspace</strong><div class="sub">In-house-tool style trace: inputs → criteria → equations → checks → selected result → downstream handoff</div></div>
<nav><a href="/engineering">P&ID</a><a href="/hazop">HAZOP</a><a href="/summaries">Summaries</a></nav>
</header>
<main>
<section class="hero">
<div>
<h1>{html.escape(tag)}</h1>
<div class="sub">{html.escape(type_text)} · {html.escape(service)}</div>
<div class="sub">Entity ID: {html.escape(entity_id)} · Governing Design Basis: DB-001 Rev A</div>
<div class="toolbar">
<a href="/export/dexpi.xml">DEXPI XML</a>
<a href="/export/summary.csv">Summary CSV</a>
<button onclick="window.print()">Print / Save PDF</button>
<a href="/engineering">Back to P&ID</a>
</div>
</div>
<span class="badge">Published data + explicit engineering gates</span>
</section>

<div class="topgrid">
<section class="panel"><h2>Design Basis / Criteria</h2>{_table(basis_rows, preferred=["criterion_id","criterion","value","unit","revision","status","source"])}</section>
<section class="panel"><h2>Digital Thread Connections</h2>{_table(connections, preferred=["relationship","entity","entity_id","type","service"])}</section>
</div>

<div class="tabs">{tabs_html}</div>
{panes_html}
</main>
<script>
function showTab(id,button){{
 document.querySelectorAll('.pane').forEach(x=>x.classList.remove('active'));
 document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
 document.getElementById('pane-'+id).classList.add('active');
 button.classList.add('active');
}}
</script>
</body></html>"""
