from __future__ import annotations

import html
from typing import Any

from .thread_models import ObjectDossier


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, tuple)):
        return ", ".join(_fmt(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_fmt(val)}" for key, val in value.items())
    return str(value)


def _simple_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return '<div class="empty">No data.</div>'
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = "".join(
            f"<td>{html.escape(_fmt(row.get(key)))}</td>"
            for key, _ in columns
        )
        body.append(f"<tr>{cells}</tr>")
    return f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _kv_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">No data.</div>'
    out = []
    for row in rows:
        name = row.get("name") or row.get("criterion_id") or "Item"
        value = row.get("value")
        unit = row.get("unit")
        shown = f"{_fmt(value)} {unit or ''}".strip()
        out.append(
            f"<tr><td>{html.escape(str(name))}</td><td>{html.escape(shown)}</td></tr>"
        )
    return f'<table class="kv"><tbody>{"".join(out)}</tbody></table>'


def _structured_value(value: Any) -> str:
    if isinstance(value, dict):
        rows = "".join(
            f"<tr><td>{html.escape(str(k).replace('_', ' ').title())}</td>"
            f"<td>{html.escape(_fmt(v))}</td></tr>"
            for k, v in value.items()
        )
        return f'<table class="kv"><tbody>{rows}</tbody></table>'
    if isinstance(value, list):
        return "<ul>" + "".join(f"<li>{html.escape(_fmt(v))}</li>" for v in value) + "</ul>"
    return html.escape(_fmt(value))


def _calc_detail(record) -> str:
    meta = record.metadata or {}
    detail = meta.get("calculation_detail")
    if not isinstance(detail, dict):
        return ""

    parts = ['<div class="calc-detail">']
    parts.append('<div class="calcgrid">')
    parts.append('<section><h4>Inputs</h4>' + _kv_table(detail.get("inputs", [])) + '</section>')
    parts.append('<section><h4>Criteria / Limits</h4>' + _kv_table(detail.get("criteria", [])) + '</section>')
    parts.append('</div>')

    case_rows = detail.get("case_results", [])
    if case_rows:
        keys = []
        for row in case_rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        preferred = [
            "case", "simulation_case_id", "stream_number", "mass_flow_tph",
            "pressure_barg", "suction_pressure_barg", "discharge_pressure_barg",
            "required_holdup_volume_m3", "raw_differential_head_m",
            "velocity_ms", "required_recycle_tph", "comment",
        ]
        ordered = [k for k in preferred if k in keys] + [k for k in keys if k not in preferred]
        columns = [(k, k.replace("_", " ").title()) for k in ordered]
        parts.append('<section><h4>Case Results</h4>' + _simple_table(case_rows, columns) + '</section>')

    scenarios = detail.get("relief_scenarios", [])
    if scenarios:
        columns = [
            ("scenario", "Scenario"),
            ("why_considered", "Why Considered"),
            ("screening_status", "Screening Status"),
            ("screening_load_tph", "Screening Load t/h"),
            ("data_gap", "Data Gap / Required Work"),
        ]
        parts.append('<section><h4>Relief Scenario Register</h4>' + _simple_table(scenarios, columns) + '</section>')
        parts.append(
            '<div class="governing"><b>Preliminary selected scenario:</b> '
            + html.escape(_fmt(detail.get("preliminary_selected_scenario")))
            + '<br><b>Why selected now:</b> '
            + html.escape(_fmt(detail.get("selection_reason")))
            + '</div>'
        )

    if detail.get("governing_case") or detail.get("governing_reason"):
        parts.append(
            '<div class="governing"><b>Governing case:</b> '
            + html.escape(_fmt(detail.get("governing_case")))
            + '<br><b>Reason:</b> '
            + html.escape(_fmt(detail.get("governing_reason")))
            + '</div>'
        )

    parts.append('<section><h4>Outputs</h4>' + _kv_table(detail.get("outputs", [])) + '</section>')
    parts.append('<div class="method"><b>Method:</b> ' + html.escape(_fmt(detail.get("method"))) + '</div>')
    parts.append('</div>')
    return "".join(parts)


def _record_block(record) -> str:
    provenance = record.provenance
    src = " · ".join(
        part for part in [
            provenance.source_type,
            provenance.source_id,
            f"Rev {provenance.source_revision}" if provenance.source_revision else None,
            provenance.method,
            provenance.note,
        ]
        if part
    )
    return f"""
    <article class="record">
      <div class="record-head">
        <div><strong>{html.escape(record.name)}</strong><div class="record-id">{html.escape(record.id)}</div></div>
        <span class="status">{html.escape(record.status)}</span>
      </div>
      <div class="record-value">{_structured_value(record.value)}</div>
      {_calc_detail(record)}
      <div class="source">Source: {html.escape(src)}</div>
    </article>
    """


def render_object_detail_html(dossier: ObjectDossier) -> str:
    basis = "".join(
        f"""
        <tr>
          <td>{html.escape(item.name)}</td>
          <td>{html.escape(_fmt(item.value))}</td>
          <td>{html.escape(item.unit or "")}</td>
          <td>{html.escape(item.provenance.source_id)} Rev {html.escape(item.provenance.source_revision or "—")}</td>
        </tr>
        """
        for item in dossier.design_basis
    ) or '<tr><td colspan="4">No linked Design Basis criteria.</td></tr>'

    domain_sections = []
    domain_labels = {
        "simulation": "Process / Simulation",
        "process_calculation": "Process / Safety Calculations",
        "pid": "P&ID / Configuration",
        "instrumentation": "Instrumentation / DCS",
        "mechanical": "Technical / Mechanical",
        "electrical": "Electrical",
        "cost": "Cost Estimate",
        "epc_vendor": "EPC / Vendor",
        "operations": "Operations",
        "history": "History",
    }
    for domain, records in dossier.records.items():
        label = domain_labels.get(domain.value, domain.value.replace("_", " ").title())
        domain_sections.append(
            f'<section class="domain"><h2>{html.escape(label)}</h2>'
            + "".join(_record_block(record) for record in records)
            + "</section>"
        )

    statuses = [
        record.status
        for records in dossier.records.values()
        for record in records
    ]
    maturity = "Published / Mixed Discipline Maturity" if statuses else "Basis only"
    if dossier.design_basis:
        basis_source = dossier.design_basis[0].provenance.source_id
        basis_revision = dossier.design_basis[0].provenance.source_revision or "—"
    else:
        basis_source = "No linked Design Basis"
        basis_revision = "—"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(dossier.tag)} — Digital BDEP Detail</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#eef1f4;color:#111}}
header{{background:#fff;border-bottom:1px solid #bbb;padding:14px 18px;position:sticky;top:0;z-index:5;display:flex;justify-content:space-between}}
header a{{font-size:12px;color:#174a77;text-decoration:none;margin-left:12px}}
main{{max-width:1400px;margin:auto;padding:14px}}
.hero{{background:#fff;border:1px solid #aaa;padding:16px;display:grid;grid-template-columns:1fr auto;gap:12px}}
.hero h1{{margin:0;font-size:22px}} .muted{{color:#666;font-size:11px;margin-top:4px}}
.chip{{font-size:10px;padding:5px 8px;border-radius:999px;background:#dcfce7;color:#166534;align-self:start}}
section.domain,.basis{{background:#fff;border:1px solid #aaa;margin-top:12px;padding:14px}}
h2{{font-size:14px;margin:0 0 10px}} h4{{font-size:10px;text-transform:uppercase;margin:9px 0 6px;color:#334155}}
table{{border-collapse:collapse;width:100%;font-size:10px}} th,td{{border:1px solid #ddd;padding:6px;vertical-align:top;text-align:left}}
th{{background:#f1f5f9;position:sticky;top:0}} .tablewrap{{overflow:auto;max-height:360px}}
.record{{border:1px solid #d7dde3;border-radius:6px;margin:8px 0;padding:10px}}
.record-head{{display:flex;justify-content:space-between;gap:10px}} .record-id{{font-size:9px;color:#64748b;margin-top:2px}}
.status{{font-size:9px;background:#e2e8f0;padding:4px 6px;border-radius:999px;height:max-content}}
.record-value{{margin-top:8px}} .source{{font-size:9px;color:#64748b;border-top:1px dotted #ddd;margin-top:8px;padding-top:6px}}
.calc-detail{{border-top:2px solid #dbeafe;margin-top:10px;padding-top:8px}}
.calcgrid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} .kv td:first-child{{width:55%;background:#f8fafc;font-weight:600}}
.governing{{background:#fffbeb;border:1px solid #fde68a;padding:8px;margin:8px 0;font-size:10px;line-height:1.45}}
.method{{font-size:10px;background:#f8fafc;border:1px solid #e5e7eb;padding:7px;margin-top:8px}}
.empty{{font-size:10px;color:#666}}
@media(max-width:800px){{.calcgrid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header>
<div><strong>Digital BDEP Detail / Datasheet View</strong></div>
<nav><a href="/engineering">Engineering View</a><a href="/dashboard">Dashboard</a></nav>
</header>
<main>
<section class="hero">
<div>
<h1>{html.escape(dossier.tag)}</h1>
<div class="muted">{html.escape(dossier.object_type or dossier.category)} · {html.escape(dossier.service or "")}</div>
<div class="muted">Object ID: {html.escape(dossier.object_id)}</div>
<div class="muted">Governing basis: {html.escape(basis_source)} Rev {html.escape(basis_revision)}</div>
</div>
<span class="chip">{html.escape(maturity)}</span>
</section>

<section class="basis">
<h2>Design Basis Criteria</h2>
<div class="tablewrap"><table>
<thead><tr><th>Criterion</th><th>Value</th><th>Unit</th><th>Source</th></tr></thead>
<tbody>{basis}</tbody>
</table></div>
</section>

{"".join(domain_sections)}
</main>
</body></html>"""
