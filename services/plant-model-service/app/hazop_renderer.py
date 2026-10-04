from __future__ import annotations

import html

from .hazop import build_demo_hazop, hazop_rows_for_entity


_CALC_ENTITY = {
    "RELIEF-PSV101-BASIS": "VLV-PSV101",
    "CALC-V101-HOLDUP": "EQ-V101",
    "CALC-P101-RATED-FLOW": "EQ-P101",
    "CALC-FCV101-CV": "VLV-FCV101",
    "LINE-1102-SIZING": "LINE-1102",
    "LINE-1103-SIZING": "LINE-1103",
    "LINE-1190-SIZING": "LINE-1190",
}


def _calc_link(calc_id: str) -> str:
    entity_id = _CALC_ENTITY.get(calc_id)
    if entity_id is None:
        return f'<span class="calc">{html.escape(calc_id)}</span>'
    return (
        f'<a class="calc" href="/workspace/{html.escape(entity_id)}#calc-{html.escape(calc_id)}">'
        f'{html.escape(calc_id)}</a>'
    )


def _entity_links(items):
    links = []
    for item in items:
        for entity_id in item.get("entity_ids", []):
            links.append(
                f'<a class="entity" href="/workspace/{html.escape(entity_id)}">{html.escape(entity_id)}</a>'
            )
    return " ".join(dict.fromkeys(links))


def render_hazop_html() -> str:
    data = build_demo_hazop()
    node_html = []
    total_rows = 0
    for node in data["nodes"]:
        rows = []
        for row in node["rows"]:
            total_rows += 1
            causes = "<br>".join(
                f'{html.escape(item["text"])}<div class="links">{_entity_links([item])}</div>'
                for item in row["causes"]
            )
            safeguards = "<br>".join(
                f'{html.escape(item["text"])}<div class="links">{_entity_links([item])}</div>'
                for item in row["safeguards"]
            )
            calculations = " ".join(
                _calc_link(calc_id)
                for calc_id in row["linked_calculations"]
            ) or "—"
            rows.append(
                f"""
                <tr>
                  <td><b>{html.escape(row["row_id"])}</b></td>
                  <td>{html.escape(row["guideword"])}</td>
                  <td>{html.escape(row["parameter"])}</td>
                  <td>{html.escape(row["deviation"])}</td>
                  <td>{causes}</td>
                  <td>{html.escape("; ".join(row["consequences"]))}</td>
                  <td>{safeguards}</td>
                  <td>{calculations}</td>
                  <td>{html.escape(row["recommendation"])}</td>
                  <td>{html.escape(row["risk"])}</td>
                  <td>{html.escape(row["status"])}</td>
                </tr>
                """
            )
        entity_links = " ".join(
            f'<a class="entity" href="/workspace/{html.escape(entity_id)}">{html.escape(entity_id)}</a>'
            for entity_id in node["entity_ids"]
        )
        node_html.append(
            f"""
            <section class="node">
              <div class="node-head">
                <div><h2>{html.escape(node["node_id"])} — {html.escape(node["name"])}</h2>
                <div class="intent"><b>Design intent:</b> {html.escape(node["design_intent"])}</div></div>
                <div class="entity-list">{entity_links}</div>
              </div>
              <div class="scroll"><table>
                <thead><tr>
                <th>Row</th><th>Guideword</th><th>Parameter</th><th>Deviation</th>
                <th>Candidate Causes + Digital Thread</th><th>Consequences</th>
                <th>Existing Safeguards + Digital Thread</th><th>Linked Calculations</th>
                <th>Recommendation / Action</th><th>Risk</th><th>Status</th>
                </tr></thead>
                <tbody>{"".join(rows)}</tbody>
              </table></div>
            </section>
            """
        )

    impact_rows = hazop_rows_for_entity("LINE-1102")
    impact_ids = ", ".join(row["row_id"] for row in impact_rows)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP HAZOP Demonstrator</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#eef1f4;color:#111}}
header{{background:#fff;border-bottom:1px solid #aaa;padding:12px 16px;display:flex;justify-content:space-between}}
header a{{font-size:11px;color:#174a77;text-decoration:none;margin-left:12px}}
main{{padding:12px;max-width:1800px;margin:auto}}
.hero,.node{{background:#fff;border:1px solid #999;padding:12px;margin-bottom:10px}}
.hero h1{{font-size:20px;margin:0}} .sub{{font-size:9px;color:#64748b;margin-top:4px}}
.kpis{{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}} .kpi{{border:1px solid #cbd5e1;padding:7px 10px;font-size:9px}} .kpi b{{font-size:17px;display:block}}
.note{{background:#eff6ff;border:1px solid #bfdbfe;padding:9px;font-size:10px;margin-top:10px;line-height:1.45}}
.node-head{{display:grid;grid-template-columns:1fr auto;gap:10px;border-bottom:1px solid #ddd;padding-bottom:8px}}
.node h2{{font-size:13px;margin:0}} .intent{{font-size:9px;color:#475569;margin-top:4px;max-width:950px}}
.entity-list{{max-width:480px;text-align:right}} .entity{{display:inline-block;font-size:8px;padding:3px 5px;border:1px solid #93c5fd;border-radius:999px;color:#174a77;text-decoration:none;margin:2px}}
.links{{margin-top:3px}} .calc{{font-size:8px;background:#f1f5f9;border:1px solid #cbd5e1;padding:2px 4px;display:inline-block;margin:1px;color:#174a77;text-decoration:none}}
table{{border-collapse:collapse;width:100%;font-size:8px}} th,td{{border:1px solid #ddd;padding:5px;text-align:left;vertical-align:top;min-width:70px}} th{{background:#f1f5f9;position:sticky;top:0}}
.scroll{{overflow:auto;max-height:520px;margin-top:8px}}
</style>
</head>
<body>
<header><div><strong>Digital BDEP — HAZOP Digital-Thread Demonstrator</strong><div class="sub">HAZOP preparation generated from the same connected engineering model</div></div><nav><a href="/engineering">P&ID</a><a href="/summaries">Summaries</a></nav></header>
<main>
<section class="hero">
<h1>{html.escape(data["title"])}</h1>
<div class="kpis"><div class="kpi"><b>{len(data["nodes"])}</b>HAZOP nodes</div><div class="kpi"><b>{total_rows}</b>pre-populated deviations</div><div class="kpi"><b>Live</b>entity/calculation links</div></div>
<div class="note">{html.escape(data["governance_note"])}</div>
<div class="note"><b>Change-impact demonstration:</b> if suction line <a class="entity" href="/workspace/LINE-1102">LINE-1102 / 8&quot;-HC-1102-CS150</a> changes, the Digital Thread immediately identifies HAZOP rows <b>{html.escape(impact_ids)}</b> as requiring review. The system does not rewrite the HAZOP decision; it tells the team exactly which rows are affected.</div>
</section>
{"".join(node_html)}
</main>
</body></html>"""
