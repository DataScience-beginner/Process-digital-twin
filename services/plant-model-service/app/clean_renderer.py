from __future__ import annotations

import html
import json

from .cleanup import AnnotationKind, CleanupResult
from .drafter import DrafterPlan
from .instrumented_renderer import _bubble, _route_class
from .inspection_graph import build_inspection_graph, route_entity_id
from .models import PlantModel
from .thread_models import ObjectDossier


def _annotation_svg(
    cleanup: CleanupResult,
    line_labels: dict[str, str] | None = None,
) -> str:
    parts = []
    overrides = line_labels or {}
    for ann in cleanup.annotations:
        css = {
            AnnotationKind.LINE_TAG: "linetag",
            AnnotationKind.OFFPAGE: "offpage",
            AnnotationKind.NOTE: "note",
            AnnotationKind.EQUIPMENT_TAG: "tag",
            AnnotationKind.TITLE: "title",
        }[ann.kind]
        display_text = overrides.get(ann.annotation_id, ann.text)
        parts.append(
            f'<text class="{css}" x="{ann.position.x}" y="{ann.position.y + ann.height - 2}" '
            f'data-annotation-id="{html.escape(ann.annotation_id)}">{html.escape(display_text)}</text>'
        )
    return "".join(parts)


def _selectable_route_svg(route) -> str:
    points = " ".join(f"{p.x},{p.y}" for p in route.points)
    edge_ids = ",".join(route.semantic_edge_ids)
    entity_id = route_entity_id(route.role)
    css = _route_class(route.role)
    return (
        f'<polyline class="{css}" points="{points}" '
        f'data-semantic-edge-ids="{html.escape(edge_ids)}" '
        f'data-route-role="{html.escape(route.role)}"/>'
        f'<polyline class="route-hit" points="{points}" '
        f'data-route-entity-id="{html.escape(entity_id)}" '
        f'onclick="selectEntity(\'{html.escape(entity_id)}\')" '
        f'aria-label="Select {html.escape(entity_id)}"/>'
    )


def render_clean_pid_html(
    model: PlantModel,
    plan: DrafterPlan,
    cleanup: CleanupResult,
    dossiers: dict[str, ObjectDossier] | None = None,
    publication_stages: list | None = None,
) -> str:
    quality_issues = [*plan.issues, *cleanup.issues]
    status = "RED" if any(i.severity == "RED" for i in quality_issues) else (
        "AMBER" if quality_issues else "GREEN"
    )
    quality_rows = "".join(
        f'<div class="issue {issue.severity.lower()}"><b>{issue.severity}</b> · {html.escape(issue.message)}</div>'
        for issue in quality_issues
    ) or '<div class="issue green"><b>GREEN</b> · No blocking drafting-quality issues detected.</div>'
    dossier_payload = json.dumps(
        {
            object_id: dossier.model_dump(mode="json")
            for object_id, dossier in (dossiers or {}).items()
        }
    ).replace("</", "<\\/")
    stage_payload = json.dumps(
        [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in (publication_stages or [])
        ]
    ).replace("</", "<\\/")
    inspection_payload = json.dumps(
        build_inspection_graph(model, dossiers or {}, plan.routes)
    ).replace("</", "<\\/")

    line_labels = {
        "ANN-L-V101-LIQ": "1102",
        "ANN-L-P101-DIS": "1103",
        "ANN-L-P101-REC": "1190",
    }
    for dossier in (dossiers or {}).values():
        for records in dossier.records.values():
            for record in records:
                if not record.id.startswith("LINE-") or not isinstance(record.value, dict):
                    continue
                line_number = record.value.get("line_number")
                if record.id == "LINE-1102-SIZING" and line_number:
                    line_labels["ANN-L-V101-LIQ"] = str(line_number)
                elif record.id == "LINE-1103-SIZING" and line_number:
                    line_labels["ANN-L-P101-DIS"] = str(line_number)
                elif record.id == "LINE-1190-SIZING" and line_number:
                    line_labels["ANN-L-P101-REC"] = str(line_number)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP MVP 0.5C</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#e7e9ec;color:#111}}
header{{background:#fff;border-bottom:1px solid #aaa;padding:11px 16px;display:flex;justify-content:space-between}}
header a{{margin-left:14px;color:#174a77;text-decoration:none;font-size:12px}}
.publishbar{{background:#f8fafc;border-bottom:1px solid #cbd5e1;padding:8px 12px;display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
.pubbtn{{font-size:10px;padding:7px 9px;border:1px solid #94a3b8;background:#fff;border-radius:4px;cursor:pointer}}
.pubbtn:hover{{background:#eef2ff}} .pubbtn.all{{font-weight:700;border-color:#334155}}
.pubstatus{{font-size:9px;padding:3px 6px;border-radius:999px;background:#e5e7eb;color:#374151}}
.pubstatus.published{{background:#dcfce7;color:#166534}}
.pubmsg{{font-size:10px;margin-left:auto;color:#475569}}
main{{display:grid;grid-template-columns:minmax(900px,1fr) 430px;gap:12px;padding:12px}}
.sheet{{background:#fff;border:1px solid #777;overflow:auto}}
.side{{background:#fff;border:1px solid #aaa;padding:14px}}
svg{{width:100%;min-width:1120px;height:auto;background:#fff}}
.border{{fill:none;stroke:#000;stroke-width:1.1}}
.thin{{fill:none;stroke:#000;stroke-width:.7}}
.pipe{{fill:none;stroke:#000;stroke-width:1.6;stroke-linecap:square;stroke-linejoin:miter}}
.impulse{{fill:none;stroke:#000;stroke-width:1;stroke-linecap:square;stroke-linejoin:miter}}
.signal{{fill:none;stroke:#000;stroke-width:1;stroke-dasharray:7 4;stroke-linecap:square;stroke-linejoin:miter}}
.sym{{fill:#fff;stroke:#000;stroke-width:1.5;stroke-linejoin:miter}}
.inst{{fill:#fff;stroke:#000;stroke-width:1.2}}
.tag{{font:700 11px Arial}} .title{{font:700 9px Arial}} .txt{{font:8px Arial}} .itxt{{font:700 8px Arial}}
.linetag{{font:7px Arial}} .offpage{{font:7px Arial}} .note{{font:7px Arial}}
.issue{{padding:7px 0;border-bottom:1px solid #ddd;font-size:11px}}
.green{{color:#166534}} .amber{{color:#92400e}} .red{{color:#991b1b}}
.muted{{font-size:11px;color:#666}} .section{{font-size:10px;font-weight:700;text-transform:uppercase;margin-top:14px}}
.metric{{font-size:11px;padding:5px 0;border-bottom:1px solid #e5e7eb}}
.selectable{{cursor:pointer}} .selectable:hover .sym,.selectable:hover .inst{{stroke:#1d4ed8;stroke-width:2.2}}
.route-hit{{fill:none;stroke:rgba(37,99,235,0);stroke-width:12;pointer-events:stroke;cursor:pointer}}
.route-hit:hover{{stroke:rgba(37,99,235,.16)}}
.tabs{{display:flex;flex-wrap:wrap;gap:4px;margin:10px 0}}
.tab{{font-size:10px;padding:5px 7px;border:1px solid #cbd5e1;background:#fff;border-radius:4px;cursor:pointer}}
.tab.active{{background:#1f2937;color:#fff}}
.card{{border:1px solid #e5e7eb;border-radius:5px;padding:7px;margin:6px 0;font-size:10px}}
.card .value{{font-weight:700;margin-top:3px}} .prov{{color:#6b7280;font-size:9px;margin-top:4px}}
.structured-value{{margin-top:5px;border:1px solid #e5e7eb;border-radius:4px;overflow:hidden}}
.sv-row{{display:grid;grid-template-columns:52% 48%;border-top:1px solid #e5e7eb;font-size:9px}}
.sv-row:first-child{{border-top:0}} .sv-key{{background:#f8fafc;padding:5px 6px;font-weight:600}}
.sv-val{{padding:5px 6px;word-break:break-word}} .sv-list{{margin:0;padding-left:16px;font-weight:400}}
.empty{{font-size:10px;color:#6b7280;padding:10px 0}}
.object-head{{border-bottom:1px solid #ddd;padding-bottom:8px}}
.object-actions{{display:flex;gap:6px;margin-top:8px}}
.detail-btn{{font-size:10px;padding:6px 8px;border:1px solid #64748b;background:#fff;border-radius:4px;cursor:pointer}}
.detail-btn:hover{{background:#eff6ff}}
dialog{{width:min(1040px,92vw);max-height:86vh;border:1px solid #64748b;border-radius:8px;padding:0}}
dialog::backdrop{{background:rgba(15,23,42,.45)}}
.dialog-head{{display:flex;justify-content:space-between;gap:10px;padding:12px 14px;border-bottom:1px solid #ddd;background:#f8fafc;position:sticky;top:0}}
.dialog-body{{padding:14px;overflow:auto;max-height:72vh}}
.dialog-close{{border:1px solid #94a3b8;background:#fff;border-radius:4px;padding:5px 8px;cursor:pointer}}
.detail-section{{border:1px solid #dbe1e8;border-radius:5px;margin:8px 0;padding:8px}}
.detail-section h4{{font-size:10px;text-transform:uppercase;margin:0 0 7px;color:#334155}}
.detail-record{{border-top:1px solid #e5e7eb;padding:7px 0;font-size:10px}}
.detail-record:first-child{{border-top:0}}
.detail-sub{{font-size:9px;color:#64748b;margin-top:4px}}
.case-table{{border-collapse:collapse;width:100%;font-size:9px;margin-top:6px}}
.case-table th,.case-table td{{border:1px solid #ddd;padding:4px;text-align:left;vertical-align:top}}
.case-table th{{background:#f1f5f9}}
.view-switch{{display:flex;gap:6px;margin:10px 0 6px}}
.view-btn{{font-size:10px;padding:6px 9px;border:1px solid #94a3b8;background:#fff;border-radius:4px;cursor:pointer}}
.view-btn.active{{background:#0f172a;color:#fff}}
.property-group{{border:1px solid #cbd5e1;margin:8px 0;background:#fff}}
.property-group-title{{background:#e2e8f0;font:700 10px Arial;padding:6px 8px;text-transform:uppercase;letter-spacing:.2px}}
.property-row{{display:grid;grid-template-columns:45% 55%;border-top:1px solid #e5e7eb;font-size:10px}}
.property-name{{padding:6px 7px;background:#f8fafc;border-right:1px solid #e5e7eb}}
.property-value{{padding:6px 7px;word-break:break-word}}
.property-source{{grid-column:1 / 3;padding:4px 7px 6px;color:#64748b;font-size:9px;border-top:1px dotted #e2e8f0}}
.node-group{{border:1px solid #cbd5e1;margin:7px 0;background:#fff}}
.node-group-title{{background:#e2e8f0;font:700 10px Arial;padding:6px 8px;text-transform:uppercase}}
.node-list{{display:flex;flex-wrap:wrap;gap:5px;padding:7px}}
.node-link{{font-size:9px;padding:5px 7px;border:1px solid #94a3b8;background:#fff;border-radius:999px;cursor:pointer;text-align:left}}
.node-link:hover{{background:#eff6ff;border-color:#3b82f6}}
.node-rel{{font-size:8px;color:#64748b;margin-left:4px}}
.path-flow{{display:flex;flex-wrap:wrap;align-items:center;gap:5px;padding:7px}}
.path-arrow{{color:#64748b}}
#propertiesContent{{display:none}}
</style>
</head>
<body>
<header>
<div><strong>Digital BDEP — Engineering View</strong><div class="muted">Staged publishing · connected P&ID + object-centric Digital Thread</div></div>
<nav><a href="/dashboard">Dashboard</a><a href="/configuration-match/CASE-NORMAL">Configuration</a><a href="/compiler/CASE-NORMAL">Compiler</a><a href="/graph">Graph View</a></nav>
</header>
<div class="publishbar" id="publishbar"></div>
<main>
<section class="sheet">
<svg viewBox="0 0 1120 690">
<rect class="border" x="24" y="24" width="1072" height="642"/>
<line class="border" x1="24" y1="590" x2="1096" y2="590"/>
<line class="thin" x1="760" y1="590" x2="760" y2="666"/>
<line class="thin" x1="930" y1="590" x2="930" y2="666"/>

{''.join(_selectable_route_svg(route) for route in plan.routes)}

<!-- Separator -->
<g class="selectable" data-object-id="EQ-V101" onclick="selectEntity('EQ-V101')">
<path class="sym" d="M184 233 Q220 207 256 233 L256 367 Q220 393 184 367 Z"/>
<line class="sym" x1="220" y1="380" x2="220" y2="405"/>
<text x="220" y="304" text-anchor="middle" class="tag">V-101</text>
</g>

<!-- Protection -->
<g class="selectable" data-object-id="VLV-PSV101" onclick="selectEntity('VLV-PSV101')">
<path class="sym" d="M223 166 L247 166 L235 146 Z"/>
<line class="sym" x1="235" y1="146" x2="235" y2="128"/>
<line class="sym" x1="227" y1="128" x2="243" y2="128"/>
<text x="262" y="151" class="txt">PSV-101</text>
</g>
<g class="selectable" data-object-id="BOUND-RELIEF" onclick="selectEntity('BOUND-RELIEF')">
<path class="sym" d="M222 73 H242 L250 80 L242 87 H222 Z"/>
</g>
<g class="selectable" data-object-id="VLV-VENT101" onclick="selectEntity('VLV-VENT101')">
<path class="sym" d="M128 139 L145 150 L128 161 Z M162 139 L145 150 L162 161 Z"/>
</g>
<g class="selectable" data-object-id="BOUND-VENT" onclick="selectEntity('BOUND-VENT')">
<path class="sym" d="M68 143 H88 L96 150 L88 157 H68 Z"/>
</g>
<g class="selectable" data-object-id="VLV-DRAIN101" onclick="selectEntity('VLV-DRAIN101')">
<path class="sym" d="M184 503 L195 520 L206 503 Z M184 537 L195 520 L206 537 Z"/>
</g>
<g class="selectable" data-object-id="BOUND-DRAIN" onclick="selectEntity('BOUND-DRAIN')">
<path class="sym" d="M188 562 H202 L209 569 L202 576 H188 Z"/>
</g>

<!-- Vessel instruments -->
<g class="selectable" data-object-id="INS-PT101" onclick="selectEntity('INS-PT101')">{_bubble(105,255,"PT","PT-101")}</g>
<g class="selectable" data-object-id="INS-PI101" onclick="selectEntity('INS-PI101')">{_bubble(105,310,"PI","PI-101")}</g>
<g class="selectable" data-object-id="INS-LT101" onclick="selectEntity('INS-LT101')">{_bubble(315,290,"LT","LT-101")}</g>
<g class="selectable" data-object-id="INS-LI101" onclick="selectEntity('INS-LI101')">{_bubble(315,340,"LI","LI-101")}</g>
<g class="selectable" data-object-id="INS-LIC101" onclick="selectEntity('INS-LIC101')">{_bubble(415,205,"LIC","LIC-101")}</g>

<!-- LCV -->
<g class="selectable" data-object-id="VLV-LCV101" onclick="selectEntity('VLV-LCV101')">
<path class="sym" d="M376 419 L395 430 L376 441 Z M414 419 L395 430 L414 441 Z"/>
<line class="sym" x1="395" y1="430" x2="395" y2="407"/>
<path class="sym" d="M383 407 Q395 390 407 407"/>
<line class="sym" x1="383" y1="407" x2="407" y2="407"/>
<text x="395" y="458" text-anchor="middle" class="txt">LCV-101</text>
</g>

<!-- Pump suction / pump -->
<g class="selectable" data-object-id="VLV-XV101" onclick="selectEntity('VLV-XV101')">
<path class="sym" d="M518 419 L535 430 L518 441 Z M552 419 L535 430 L552 441 Z"/>
<text x="535" y="458" text-anchor="middle" class="txt">XV-101</text>
</g>
<g class="selectable" data-object-id="EQ-P101" onclick="selectEntity('EQ-P101')">
<circle class="sym" cx="690" cy="430" r="26"/>
<path class="sym" d="M668 430 C688 408 712 412 716 430 C700 433 692 442 684 450"/>
<text x="690" y="474" text-anchor="middle" class="tag">P-101</text>
</g>

<!-- Pump pressure -->
<g class="selectable" data-object-id="INS-PI101S" onclick="selectEntity('INS-PI101S')">{_bubble(610,360,"PI","PI-101S")}</g>
<g class="selectable" data-object-id="INS-PI101D" onclick="selectEntity('INS-PI101D')">{_bubble(730,360,"PI","PI-101D")}</g>

<!-- Discharge -->
<g class="selectable" data-object-id="JUNC-P101-DIS" onclick="selectEntity('JUNC-P101-DIS')">
<circle cx="785" cy="430" r="5" fill="#000"/>
</g>
<g class="selectable" data-object-id="VLV-NRV101" onclick="selectEntity('VLV-NRV101')">
<path class="sym" d="M848 420 L872 430 L848 440 Z"/>
<line class="sym" x1="875" y1="418" x2="875" y2="442"/>
<text x="863" y="458" text-anchor="middle" class="txt">NRV-101</text>
</g>
<g class="selectable" data-object-id="VLV-XV102" onclick="selectEntity('VLV-XV102')">
<path class="sym" d="M938 419 L955 430 L938 441 Z M972 419 L955 430 L972 441 Z"/>
<text x="955" y="458" text-anchor="middle" class="txt">XV-102</text>
</g>
<g class="selectable" data-object-id="BOUND-PRODUCT" onclick="selectEntity('BOUND-PRODUCT')">
<path class="sym" d="M1046 423 H1066 L1076 430 L1066 437 H1046 Z"/>
</g>

<!-- Minimum-flow control -->
<g class="selectable" data-object-id="INS-FT101" onclick="selectEntity('INS-FT101')">{_bubble(700,215,"FT","FT-101")}</g>
<line class="impulse" x1="700" y1="229" x2="700" y2="255"/>
<g class="selectable" data-object-id="INS-FIC101" onclick="selectEntity('INS-FIC101')">{_bubble(820,180,"FIC","FIC-101")}</g>
<g class="selectable" data-object-id="VLV-FCV101" onclick="selectEntity('VLV-FCV101')">
<path class="sym" d="M501 244 L520 255 L501 266 Z M539 244 L520 255 L539 266 Z"/>
<line class="sym" x1="520" y1="255" x2="520" y2="232"/>
<path class="sym" d="M508 232 Q520 215 532 232"/>
<line class="sym" x1="508" y1="232" x2="532" y2="232"/>
<text x="520" y="284" text-anchor="middle" class="txt">FCV-101</text>
</g>

{_annotation_svg(cleanup, line_labels)}

<!-- Title block -->
<text class="title" x="775" y="612">DIGITAL BDEP - P&ID</text>
<text class="txt" x="775" y="629">SEPARATOR + PUMP CONFIGURATION</text>
<text class="txt" x="775" y="646">DRAWING: PID-DEMO-001</text>
<text class="txt" x="945" y="612">REV: A</text>
<text class="txt" x="945" y="629">STATUS: {status}</text>
<text class="txt" x="945" y="646">VIEW: ENGINEERING</text>
</svg>
</section>
<aside class="side">
<div class="object-head">
<h3 id="objectTag">Digital BDEP Object</h3>
<div id="objectMeta" class="muted">Click any visible equipment, valve, instrument, boundary or line</div>
<div class="object-actions">
<button class="detail-btn" onclick="openDetailModal()">↗ Detailed View</button>
<button class="detail-btn" onclick="popOutDetail()">⧉ Pop out</button>
</div>
</div>
<div class="view-switch">
<button id="tabsModeBtn" class="view-btn active" onclick="setInspectorMode('tabs')">Tabs</button>
<button id="propertiesModeBtn" class="view-btn" onclick="setInspectorMode('properties')">Properties</button>
</div>
<div id="tabsMode">
<div class="tabs" id="tabs"></div>
<div id="tabContent">
<div class="empty">Select an engineering object to open its object-centric digital thread.</div>
</div>
</div>
<div id="propertiesContent"></div>
<div class="section">Drawing quality</div>
<div class="metric"><b>Status:</b> {status}</div>
<div class="metric"><b>Detected issues:</b> {len(quality_issues)}</div>
</aside>
</main>
<dialog id="detailDialog">
<div class="dialog-head">
<div><strong id="dialogTitle">Detailed View</strong><div class="muted" id="dialogSub"></div></div>
<div><button class="detail-btn" onclick="popOutDetail()">⧉ Pop out</button> <button class="dialog-close" onclick="document.getElementById('detailDialog').close()">Close</button></div>
</div>
<div class="dialog-body" id="dialogBody"></div>
</dialog>
<script>
const dossiers={dossier_payload};
const inspection={inspection_payload};
const entities=inspection.entities||{{}};
let publicationStages={stage_payload};
const publishDefs=[
 ["design_basis","Publish Design Basis"],
 ["simulation","Publish Simulation"],
 ["configuration","Select Configuration"],
 ["process","Publish Process / Safety"],
 ["instrumentation","Publish Instrumentation / DCS"],
 ["mechanical","Publish Technical / Mechanical"],
 ["costing","Publish Cost Estimate"]
];
function stageState(id){{
 return publicationStages.find(x=>x.stage===id)||{{status:"not_published"}};
}}
function renderPublishBar(){{
 const buttons=publishDefs.map(([id,label])=>{{
   const state=stageState(id);
   return '<button class="pubbtn" onclick="publishStage(\''+id+'\')">'+label+'</button><span class="pubstatus '+(state.status==="published"?"published":"")+'">'+esc(state.status||"not_published")+'</span>';
 }}).join("");
 document.getElementById("publishbar").innerHTML=buttons+'<button class="pubbtn all" onclick="publishAllStages()">Publish All</button><span id="pubmsg" class="pubmsg"></span>';
}}
async function publishStage(stage){{
 const msg=document.getElementById("pubmsg");
 msg.textContent="Publishing "+stage+"...";
 try {{
   const r=await fetch('/api/publish/'+stage,{{method:'POST'}});
   const body=await r.json();
   if(!r.ok) throw new Error(body.detail||'Publish failed');
   msg.textContent=stage+" published.";
   setTimeout(()=>location.reload(),350);
 }} catch(e) {{
   msg.textContent="Blocked: "+e.message;
 }}
}}
async function publishAllStages(){{
 const msg=document.getElementById("pubmsg");
 msg.textContent="Publishing all stages...";
 try {{
   const r=await fetch('/api/publish-all',{{method:'POST'}});
   const body=await r.json();
   if(!r.ok) throw new Error(body.detail||'Publish all failed');
   msg.textContent="All current stages published.";
   setTimeout(()=>location.reload(),350);
 }} catch(e) {{
   msg.textContent="Blocked: "+e.message;
 }}
}}
const tabDefs=[
 ["overview","Overview"],
 ["connections","Connections"],
 ["design_basis","Design Basis"],
 ["process","Process / Safety"],
 ["pid","P&ID / Lines"],
 ["calculations","Calculations"],
 ["instrumentation","Instrumentation / DCS"],
 ["mechanical","Technical / Mechanical"],
 ["electrical","Electrical"],
 ["cost","Cost Estimate"],
 ["epc_vendor","EPC / Vendor"],
 ["operations","Operations"],
 ["history","History"]
];
const domainMap={{
 pid:"pid",
 calculations:"process_calculation",
 instrumentation:"instrumentation",
 mechanical:"mechanical",
 electrical:"electrical",
 cost:"cost",
 epc_vendor:"epc_vendor",
 operations:"operations"
}};
let selectedId=null;
let activeTab="overview";
let inspectorMode="tabs";

function esc(v){{
 return String(v ?? "—").replace(/[&<>"']/g,m=>({{"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}}[m]));
}}
function humanKey(key){{
 return String(key).replace(/_/g," ").replace(/\b\w/g,m=>m.toUpperCase());
}}
function formatValue(value,unit){{
 if(value===null||value===undefined)return "—";
 if(Array.isArray(value)){{
   if(!value.length)return "—";
   return '<ul class="sv-list">'+value.map(v=>'<li>'+formatValue(v,null)+'</li>').join("")+'</ul>';
 }}
 if(typeof value==="object"){{
   const rows=Object.entries(value).map(([k,v])=>'<div class="sv-row"><div class="sv-key">'+esc(humanKey(k))+'</div><div class="sv-val">'+formatValue(v,null)+'</div></div>').join("");
   return '<div class="structured-value">'+rows+'</div>';
 }}
 return esc(value)+(unit?(" "+esc(unit)):"");
}}
function provenance(p){{
 if(!p)return "";
 const bits=[p.source_type,p.source_id,p.source_revision?("Rev "+p.source_revision):null,p.method,p.note].filter(Boolean);
 return '<div class="prov">Source: '+bits.map(esc).join(" · ")+'</div>';
}}
function card(name,value,unit,status,p){{
 return '<div class="card"><div>'+esc(name)+'</div><div class="value">'+formatValue(value,unit)+'</div>'+(status?'<div class="prov">Status: '+esc(status)+'</div>':"")+provenance(p)+'</div>';
}}
function entityFor(id){{return entities[id]||null;}}
function dossierFor(id){{return dossiers[id]||null;}}
function recordsFor(d,key,includeLines=false){{
 const rows=(d&&d.records?d.records[key]:[])||[];
 return includeLines?rows:rows.filter(x=>!String(x.id||"").startsWith("LINE-"));
}}
function sourceLine(p){{
 if(!p)return "";
 const bits=[p.source_type,p.source_id,p.source_revision?("Rev "+p.source_revision):null,p.method,p.note].filter(Boolean);
 return bits.join(" · ");
}}
function propertyRow(name,value,unit,p){{
 const src=sourceLine(p);
 return '<div class="property-row"><div class="property-name">'+esc(name)+'</div><div class="property-value">'+formatValue(value,unit)+'</div>'+(src?'<div class="property-source">Source: '+esc(src)+'</div>':"")+'</div>';
}}
function propertyGroup(title,items){{
 if(!items.length)return "";
 return '<div class="property-group"><div class="property-group-title">'+esc(title)+'</div>'+items.join("")+'</div>';
}}
function nodeButton(ref){{
 if(!ref)return "";
 return '<button class="node-link" data-entity-id="'+esc(ref.id)+'" onclick="selectEntity(this.dataset.entityId)">'+esc(ref.label||ref.id)+(ref.relation?'<span class="node-rel">'+esc(humanKey(ref.relation))+'</span>':"")+'</button>';
}}
function nodeGroup(title,refs){{
 if(!Array.isArray(refs)||!refs.length)return "";
 return '<div class="node-group"><div class="node-group-title">'+esc(title)+'</div><div class="node-list">'+refs.map(nodeButton).join("")+'</div></div>';
}}
function connectedLineRefs(e){{
 return (e&&e.connected_lines||[]).map(x=>({{id:x.id,label:x.label,relation:(x.direction||"connected")+"_line"}}));
}}
function renderConnections(e){{
 if(!e)return '<div class="empty">No entity selected.</div>';
 let h="";
 if(e.parent_equipment)h+=nodeGroup("Parent Equipment",[e.parent_equipment]);
 if(e.from)h+=nodeGroup("From",[e.from]);
 if(e.through&&e.through.length)h+=nodeGroup("Through",e.through);
 if(e.to)h+=nodeGroup("To",[e.to]);
 if(e.children&&e.children.length){{
   const byCat={{}};
   e.children.forEach(x=>{{const k=humanKey(x.category||"child");(byCat[k]||(byCat[k]=[])).push(x);}});
   Object.entries(byCat).forEach(([cat,refs])=>{{h+=nodeGroup("Contained "+cat,refs);}});
 }}
 if(e.relationships&&e.relationships.length){{
   const byRel={{}};
   e.relationships.forEach(x=>{{const k=humanKey(x.relation||"related");(byRel[k]||(byRel[k]=[])).push(x);}});
   Object.entries(byRel).forEach(([rel,refs])=>{{h+=nodeGroup(rel,refs);}});
 }}
 if(e.connected_lines&&e.connected_lines.length)h+=nodeGroup("Connected Lines / Connections",connectedLineRefs(e));
 if(e.path&&e.path.length){{
   h+='<div class="node-group"><div class="node-group-title">Complete Path</div><div class="path-flow">'+e.path.map((x,i)=>nodeButton(x)+(i<e.path.length-1?'<span class="path-arrow">→</span>':"")).join("")+'</div></div>';
 }}
 return h||'<div class="empty">No direct semantic relationships.</div>';
}}
function lineRecord(e){{
 if(!e||!e.record_value)return null;
 return {{
   id:e.id,
   name:"Line / connection engineering record",
   value:e.record_value,
   unit:null,
   status:e.status||"published",
   provenance:e.record_provenance||null,
   metadata:e.record_metadata||{{}}
 }};
}}
function renderProperties(){{
 const e=entityFor(selectedId);
 const d=dossierFor(selectedId);
 if(!e)return;
 const groups=[];
 groups.push(propertyGroup("Identification",[
   propertyRow("Entity ID",e.id,null,null),
   propertyRow("Tag / Number",e.tag,null,null),
   propertyRow("Category",e.category,null,null),
   propertyRow("Type",e.object_type||e.category,null,null),
   propertyRow("Service",e.service||"—",null,null)
 ]));
 if(e.line_number||e.stream_number){{
   groups.push(propertyGroup("Line Definition",[
     propertyRow("Line Number",e.line_number||e.tag,null,null),
     propertyRow("Stream Number",e.stream_number||"Derived / N.A.",null,null),
     propertyRow("Semantic Edges",e.semantic_edge_ids||[],null,null)
   ]));
 }}
 if(d){{
   groups.push(propertyGroup("Design Basis",(d.design_basis||[]).map(x=>propertyRow(x.name,x.value,x.unit,x.provenance))));
   const definitions=[
     ["Process / Simulation","simulation"],
     ["Calculations","process_calculation"],
     ["P&ID","pid"],
     ["Instrumentation / DCS","instrumentation"],
     ["Technical / Mechanical","mechanical"],
     ["Electrical","electrical"],
     ["Cost Estimate","cost"],
     ["EPC / Vendor","epc_vendor"],
     ["Operations","operations"]
   ];
   definitions.forEach(([title,key])=>{{
     groups.push(propertyGroup(title,recordsFor(d,key).map(x=>propertyRow(x.name,x.value,x.unit,x.provenance))));
   }});
 }}
 const lr=lineRecord(e);
 if(lr)groups.push(propertyGroup("Sizing / Engineering Output",[propertyRow(lr.name,lr.value,null,lr.provenance)]));
 document.getElementById("propertiesContent").innerHTML=groups.filter(Boolean).join("")+renderConnections(e);
}}
function renderTabs(){{
 document.getElementById("tabs").innerHTML=tabDefs.map(([id,label])=>'<button class="tab '+(activeTab===id?"active":"")+'" onclick="openTab(\''+id+'\')">'+label+'</button>').join("");
}}
function renderLineOverview(e){{
 return card("Entity ID",e.id,null,null,null)+card("Type",e.object_type||e.category,null,null,null)+card("Service",e.service||"—",null,null,null)+(e.line_number?card("Line Number",e.line_number,null,e.status,null):"")+(e.stream_number?card("Stream Number",e.stream_number,null,null,null):"");
}}
function render(){{
 const e=entityFor(selectedId);
 const d=dossierFor(selectedId);
 if(!e)return;
 document.getElementById("objectTag").textContent=e.tag||e.id;
 document.getElementById("objectMeta").textContent=(e.object_type||e.category)+" · "+(e.service||"");
 renderTabs();
 let html="";
 if(activeTab==="overview"){{
   html=renderLineOverview(e);
   if(e.parent_equipment)html+=nodeGroup("Parent Equipment",[e.parent_equipment]);
   if(e.connected_lines&&e.connected_lines.length)html+=nodeGroup("Connected Lines / Connections",connectedLineRefs(e));
 }} else if(activeTab==="connections"){{
   html=renderConnections(e);
 }} else if(activeTab==="design_basis"){{
   html=d?((d.design_basis||[]).map(x=>card(x.name,x.value,x.unit,x.status,x.provenance)).join("")||'<div class="empty">No linked Design Basis criteria.</div>'):'<div class="empty">Design Basis is inherited through connected equipment/line criteria; no direct object criterion is linked.</div>';
 }} else if(activeTab==="process"){{
   if(e.category==="line"||e.category==="connection"){{
     const lr=lineRecord(e);
     html=lr?(card(lr.name,lr.value,null,lr.status,lr.provenance)+calculationDetail(lr)):'<div class="empty">No published sizing record for this connection yet.</div>';
   }} else {{
     const rows=[...recordsFor(d,"simulation"),...recordsFor(d,"process_calculation")];
     html=rows.map(x=>card(x.name,x.value,x.unit,x.status,x.provenance)+calculationDetail(x)).join("")||'<div class="empty">No linked Process / Safety records.</div>';
   }}
 }} else if(activeTab==="pid"){{
   html=renderConnections(e);
   if(e.line_number||e.stream_number)html=renderLineOverview(e)+html;
   if(d)html+=recordsFor(d,"pid").map(x=>card(x.name,x.value,x.unit,x.status,x.provenance)).join("");
 }} else if(activeTab==="calculations"){{
   if(e.category==="line"||e.category==="connection"){{
     const lr=lineRecord(e);
     html=lr?(card(lr.name,lr.value,null,lr.status,lr.provenance)+calculationDetail(lr)):'<div class="empty">No detailed calculation is published for this connection.</div>';
   }} else {{
     html=recordsFor(d,"process_calculation").map(x=>card(x.name,x.value,x.unit,x.status,x.provenance)+calculationDetail(x)).join("")||'<div class="empty">No direct calculation records for this entity. Connected line calculations are opened by selecting the line itself.</div>';
   }}
 }} else if(activeTab==="history"){{
   if(!d){{
     html=card("Status",e.status||"semantic",null,null,e.record_provenance||null);
   }} else {{
     const all=[];
     (d.design_basis||[]).forEach(x=>all.push({{name:x.name,value:x.value,unit:x.unit,status:x.status,provenance:x.provenance}}));
     Object.values(d.records||{{}}).flat().filter(x=>!String(x.id||"").startsWith("LINE-")).forEach(x=>all.push(x));
     html=all.map(x=>card(x.name,x.value,x.unit,x.status,x.provenance)).join("")||'<div class="empty">No provenance records yet.</div>';
   }}
 }} else {{
   if(!d){{
     html='<div class="empty">This connection/entity has no direct record in this discipline.</div>';
   }} else {{
     const key=domainMap[activeTab];
     html=recordsFor(d,key).map(x=>card(x.name,x.value,x.unit,x.status,x.provenance)+calculationDetail(x)).join("")||'<div class="empty">No linked records yet for this discipline.</div>';
   }}
 }}
 document.getElementById("tabContent").innerHTML=html;
 renderProperties();
}}
function detailTable(rows){{
 if(!Array.isArray(rows)||!rows.length)return '<div class="empty">No data.</div>';
 const keys=[];
 rows.forEach(row=>Object.keys(row||{{}}).forEach(k=>{{if(!keys.includes(k))keys.push(k);}}));
 return '<div style="overflow:auto"><table class="case-table"><thead><tr>'+keys.map(k=>'<th>'+esc(humanKey(k))+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+keys.map(k=>'<td>'+formatValue(row[k],null)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
}}
function detailList(rows){{
 if(!Array.isArray(rows)||!rows.length)return '<div class="empty">No data.</div>';
 return '<div class="structured-value">'+rows.map(x=>'<div class="sv-row"><div class="sv-key">'+esc(x.name||x.criterion_id||'Item')+'</div><div class="sv-val">'+formatValue(x.value,x.unit)+'</div></div>').join('')+'</div>';
}}
function calculationDetail(record){{
 const d=((record&&record.metadata)||{{}}).calculation_detail;
 if(!d)return '';
 let h='<div class="detail-section"><h4>Calculation detail</h4>';
 h+='<b>Inputs</b>'+detailList(d.inputs||[]);
 h+='<b>Criteria / Limits</b>'+detailList(d.criteria||[]);
 if(d.case_results&&d.case_results.length)h+='<b>Case Results</b>'+detailTable(d.case_results);
 if(d.relief_scenarios&&d.relief_scenarios.length)h+='<b>Relief Scenario Register</b>'+detailTable(d.relief_scenarios);
 if(d.preliminary_selected_scenario)h+='<div class="detail-record"><b>Preliminary selected scenario:</b> '+esc(d.preliminary_selected_scenario)+'<div class="detail-sub">'+esc(d.selection_reason||'')+'</div></div>';
 if(d.governing_case)h+='<div class="detail-record"><b>Governing case:</b> '+esc(d.governing_case)+'<div class="detail-sub">'+esc(d.governing_reason||'')+'</div></div>';
 h+='<b>Outputs</b>'+detailList(d.outputs||[]);
 if(d.method)h+='<div class="detail-record"><b>Method:</b> '+esc(d.method)+'</div>';
 return h+'</div>';
}}
function buildDetailedDossier(d,e){{
 let h='<div class="detail-section"><h4>Identification</h4>'+propertyRow("Entity ID",e.id,null,null)+propertyRow("Type",e.object_type||e.category,null,null)+propertyRow("Service",e.service||"—",null,null)+'</div>';
 h+='<div class="detail-section"><h4>Connected Nodes</h4>'+renderConnections(e)+'</div>';
 if(d){{
   h+='<div class="detail-section"><h4>Design Basis</h4>'+((d.design_basis||[]).map(x=>propertyRow(x.name,x.value,x.unit,x.provenance)).join('')||'<div class="empty">No direct criteria.</div>')+'</div>';
   Object.entries(d.records||{{}}).forEach(([domain,records])=>{{
     const filtered=records.filter(r=>!String(r.id||"").startsWith("LINE-"));
     if(!filtered.length)return;
     h+='<div class="detail-section"><h4>'+esc(humanKey(domain))+'</h4>';
     filtered.forEach(r=>{{
       h+='<div class="detail-record"><b>'+esc(r.name)+'</b><div>'+formatValue(r.value,r.unit)+'</div><div class="detail-sub">Status: '+esc(r.status)+' · Source: '+esc(sourceLine(r.provenance))+'</div>'+calculationDetail(r)+'</div>';
     }});
     h+='</div>';
   }});
 }}
 const lr=lineRecord(e);
 if(lr){{
   h+='<div class="detail-section"><h4>Line / Connection Engineering</h4><div class="detail-record"><b>'+esc(lr.name)+'</b><div>'+formatValue(lr.value,null)+'</div>'+calculationDetail(lr)+'</div></div>';
 }}
 return h;
}}
function openDetailModal(){{
 const e=entityFor(selectedId);
 if(!e)return;
 const d=dossierFor(selectedId);
 document.getElementById('dialogTitle').textContent=(e.tag||e.id)+' — Detailed View';
 document.getElementById('dialogSub').textContent=(e.object_type||e.category)+' · '+(e.service||'');
 document.getElementById('dialogBody').innerHTML=buildDetailedDossier(d,e);
 document.getElementById('detailDialog').showModal();
}}
function popOutDetail(){{
 if(!selectedId)return;
 window.open('/entity/'+encodeURIComponent(selectedId)+'/detail','_blank','noopener');
}}
function openTab(tab){{activeTab=tab;render();}}
function setInspectorMode(mode){{
 inspectorMode=mode;
 const tabsMode=document.getElementById("tabsMode");
 const props=document.getElementById("propertiesContent");
 const tabsBtn=document.getElementById("tabsModeBtn");
 const propsBtn=document.getElementById("propertiesModeBtn");
 tabsMode.style.display=mode==="tabs"?"block":"none";
 props.style.display=mode==="properties"?"block":"none";
 tabsBtn.classList.toggle("active",mode==="tabs");
 propsBtn.classList.toggle("active",mode==="properties");
 if(selectedId)renderProperties();
}}
function selectEntity(id){{if(!entityFor(id))return;selectedId=id;activeTab="overview";render();setInspectorMode(inspectorMode);}}
function selectObject(id){{selectEntity(id);}}
renderPublishBar();
if(entities["EQ-V101"])selectEntity("EQ-V101");
</script>
</body></html>"""
