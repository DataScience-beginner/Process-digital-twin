from __future__ import annotations

import html
from typing import Any


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_fmt(val)}" for key, val in value.items())
    if isinstance(value, list):
        return ", ".join(_fmt(item) for item in value)
    return str(value)


def _table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">No rows.</div>'
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    head = "".join(f"<th>{html.escape(key.replace('_',' ').title())}</th>" for key in keys)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(_fmt(row.get(key)))}</td>" for key in keys) + "</tr>"
        for row in rows
    )
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render_summaries_html(summaries: dict[str, list[dict[str, Any]]]) -> str:
    defs = [
        ("equipment_list", "Equipment List"),
        ("stream_list", "Stream List"),
        ("line_list", "Line List"),
        ("valve_list", "Valve List"),
        ("control_valve_list", "Control Valve List"),
        ("instrument_index", "Instrument Index"),
        ("control_loop_list", "Control Loop List"),
        ("psv_relief_summary", "PSV / Relief Summary"),
        ("calculation_register", "Calculation Register"),
        ("technical_summary", "Technical / Mechanical Summary"),
        ("cost_summary", "Cost Summary"),
        ("publication_summary", "Publication / Completion Summary"),
        ("drawing_index", "P&ID / Drawing Index"),
        ("continuation_register", "Cross-Sheet Continuation Register"),
    ]
    buttons = "".join(
        f'<button class="tab {"active" if i == 0 else ""}" onclick="showTab(\'{key}\',this)">{html.escape(label)}</button>'
        for i, (key, label) in enumerate(defs)
    )
    panes = "".join(
        f'<section id="pane-{key}" class="pane {"active" if i == 0 else ""}"><div class="panel"><div class="panel-head"><h2>{html.escape(label)}</h2><a href="/export/summary/{key}.csv">CSV</a></div>{_table(summaries.get(key, []))}</div></section>'
        for i, (key, label) in enumerate(defs)
    )
    total = summaries.get("project_total") or []
    total_text = _fmt(total[0].get("value")) if total else "—"
    total_unit = total[0].get("unit") if total else ""

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP Summaries</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#eef1f4;color:#111}}
header{{background:#fff;border-bottom:1px solid #aaa;padding:12px 16px;display:flex;justify-content:space-between}}
header a{{font-size:11px;color:#174a77;text-decoration:none;margin-left:12px}}
main{{max-width:1700px;margin:auto;padding:12px}}
.hero{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}}
.card,.panel{{background:#fff;border:1px solid #aaa;padding:11px}} .label{{font-size:9px;text-transform:uppercase;color:#64748b}} .big{{font-size:22px;font-weight:700;margin-top:4px}}
.tabs{{background:#fff;border:1px solid #aaa;padding:8px;display:flex;flex-wrap:wrap;gap:4px;margin-top:10px;position:sticky;top:0;z-index:10}}
.tab{{font-size:9px;padding:6px 8px;border:1px solid #94a3b8;background:#fff;border-radius:4px;cursor:pointer}} .tab.active{{background:#0f172a;color:#fff}}
.pane{{display:none;margin-top:10px}} .pane.active{{display:block}}
.panel-head{{display:flex;justify-content:space-between;align-items:center}} .panel h2{{font-size:13px;margin:0 0 8px}} .panel a{{font-size:9px;color:#174a77}}
table{{border-collapse:collapse;width:100%;font-size:8.5px}} th,td{{border:1px solid #ddd;padding:5px;text-align:left;vertical-align:top}} th{{background:#f1f5f9;position:sticky;top:0}}
.scroll{{overflow:auto;max-height:650px}} .empty{{font-size:9px;color:#64748b}}
@media(max-width:900px){{.hero{{grid-template-columns:1fr 1fr}}}}
</style>
</head>
<body>
<header><div><strong>Digital BDEP — Generated BDEP Summaries</strong><div style="font-size:9px;color:#64748b">One model → all discipline lists and registers</div></div><nav><a href="/engineering">P&ID</a><a href="/hazop">HAZOP</a><a href="/export/summaries.pdf">Summary PDF</a><a href="/export/dexpi.xml">DEXPI XML</a></nav></header>
<main>
<div class="hero">
<div class="card"><div class="label">Equipment</div><div class="big">{len(summaries.get("equipment_list", []))}</div></div>
<div class="card"><div class="label">Process / utility lines</div><div class="big">{len(summaries.get("line_list", []))}</div></div>
<div class="card"><div class="label">Instruments</div><div class="big">{len(summaries.get("instrument_index", []))}</div></div>
<div class="card"><div class="label">Demo section estimate</div><div class="big">{html.escape(str(total_unit or ""))} {html.escape(total_text)}</div></div>
</div>
<div class="tabs">{buttons}</div>
{panes}
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
