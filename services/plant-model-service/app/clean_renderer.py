from __future__ import annotations

import html
import json

from .cleanup import AnnotationKind, CleanupResult
from .drafter import DrafterPlan
from .instrumented_renderer import _bubble, _route_svg
from .models import PlantModel
from .thread_models import ObjectDossier


def _annotation_svg(cleanup: CleanupResult) -> str:
    parts = []
    for ann in cleanup.annotations:
        css = {
            AnnotationKind.LINE_TAG: "linetag",
            AnnotationKind.OFFPAGE: "offpage",
            AnnotationKind.NOTE: "note",
            AnnotationKind.EQUIPMENT_TAG: "tag",
            AnnotationKind.TITLE: "title",
        }[ann.kind]
        parts.append(
            f'<text class="{css}" x="{ann.position.x}" y="{ann.position.y + ann.height - 2}" '
            f'data-annotation-id="{html.escape(ann.annotation_id)}">{html.escape(ann.text)}</text>'
        )
    return "".join(parts)


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
.selectable{{cursor:pointer}} .selectable:hover .sym{{stroke:#1d4ed8;stroke-width:2.2}}
.tabs{{display:flex;flex-wrap:wrap;gap:4px;margin:10px 0}}
.tab{{font-size:10px;padding:5px 7px;border:1px solid #cbd5e1;background:#fff;border-radius:4px;cursor:pointer}}
.tab.active{{background:#1f2937;color:#fff}}
.card{{border:1px solid #e5e7eb;border-radius:5px;padding:7px;margin:6px 0;font-size:10px}}
.card .value{{font-weight:700;margin-top:3px}} .prov{{color:#6b7280;font-size:9px;margin-top:4px}}
.empty{{font-size:10px;color:#6b7280;padding:10px 0}}
.object-head{{border-bottom:1px solid #ddd;padding-bottom:8px}}
.view-switch{{display:flex;gap:6px;margin:10px 0 6px}}
.view-btn{{font-size:10px;padding:6px 9px;border:1px solid #94a3b8;background:#fff;border-radius:4px;cursor:pointer}}
.view-btn.active{{background:#0f172a;color:#fff}}
.property-group{{border:1px solid #cbd5e1;margin:8px 0;background:#fff}}
.property-group-title{{background:#e2e8f0;font:700 10px Arial;padding:6px 8px;text-transform:uppercase;letter-spacing:.2px}}
.property-row{{display:grid;grid-template-columns:45% 55%;border-top:1px solid #e5e7eb;font-size:10px}}
.property-name{{padding:6px 7px;background:#f8fafc;border-right:1px solid #e5e7eb}}
.property-value{{padding:6px 7px;word-break:break-word}}
.property-source{{grid-column:1 / 3;padding:4px 7px 6px;color:#64748b;font-size:9px;border-top:1px dotted #e2e8f0}}
#propertiesContent{{display:none}}
</style>
</head>
<body>
<header>
<div><strong>Digital BDEP — Engineering View</strong><div class="muted">Staged publishing · connected P&ID + object-centric Digital Thread</div></div>
<nav><a href="/configuration-match/CASE-NORMAL">Configuration</a><a href="/compiler/CASE-NORMAL">Compiler</a><a href="/graph">Graph View</a></nav>
</header>
<div class="publishbar" id="publishbar"></div>
<main>
<section class="sheet">
<svg viewBox="0 0 1120 690">
<rect class="border" x="24" y="24" width="1072" height="642"/>
<line class="border" x1="24" y1="590" x2="1096" y2="590"/>
<line class="thin" x1="760" y1="590" x2="760" y2="666"/>
<line class="thin" x1="930" y1="590" x2="930" y2="666"/>

{''.join(_route_svg(route) for route in plan.routes)}

<!-- Separator -->
<g class="selectable" data-object-id="EQ-V101" onclick="selectObject('EQ-V101')">
<path class="sym" d="M184 233 Q220 207 256 233 L256 367 Q220 393 184 367 Z"/>
<line class="sym" x1="220" y1="380" x2="220" y2="405"/>
<text x="220" y="304" text-anchor="middle" class="tag">V-101</text>
</g>

<!-- Protection -->
<path class="sym" d="M223 166 L247 166 L235 146 Z"/>
<line class="sym" x1="235" y1="146" x2="235" y2="128"/>
<line class="sym" x1="227" y1="128" x2="243" y2="128"/>
<text x="262" y="151" class="txt">PSV-101</text>
<path class="sym" d="M222 73 H242 L250 80 L242 87 H222 Z"/>
<path class="sym" d="M128 139 L145 150 L128 161 Z M162 139 L145 150 L162 161 Z"/>
<path class="sym" d="M68 143 H88 L96 150 L88 157 H68 Z"/>
<path class="sym" d="M184 503 L195 520 L206 503 Z M184 537 L195 520 L206 537 Z"/>
<path class="sym" d="M188 562 H202 L209 569 L202 576 H188 Z"/>

<!-- Vessel instruments -->
{_bubble(105,255,"PT","PT-101")}
{_bubble(105,310,"PI","PI-101")}
{_bubble(315,290,"LT","LT-101")}
{_bubble(315,340,"LI","LI-101")}
{_bubble(415,205,"LIC","LIC-101")}

<!-- LCV -->
<path class="sym" d="M376 419 L395 430 L376 441 Z M414 419 L395 430 L414 441 Z"/>
<line class="sym" x1="395" y1="430" x2="395" y2="407"/>
<path class="sym" d="M383 407 Q395 390 407 407"/>
<line class="sym" x1="383" y1="407" x2="407" y2="407"/>
<text x="395" y="458" text-anchor="middle" class="txt">LCV-101</text>

<!-- Pump suction / pump -->
<path class="sym" d="M518 419 L535 430 L518 441 Z M552 419 L535 430 L552 441 Z"/>
<text x="535" y="458" text-anchor="middle" class="txt">XV-101</text>
<g class="selectable" data-object-id="EQ-P101" onclick="selectObject('EQ-P101')">
<circle class="sym" cx="690" cy="430" r="26"/>
<path class="sym" d="M668 430 C688 408 712 412 716 430 C700 433 692 442 684 450"/>
<text x="690" y="474" text-anchor="middle" class="tag">P-101</text>
</g>

<!-- Pump pressure -->
{_bubble(610,360,"PI","PI-101S")}
{_bubble(730,360,"PI","PI-101D")}

<!-- Discharge -->
<circle cx="785" cy="430" r="3" fill="#000"/>
<path class="sym" d="M848 420 L872 430 L848 440 Z"/>
<line class="sym" x1="875" y1="418" x2="875" y2="442"/>
<text x="863" y="458" text-anchor="middle" class="txt">NRV-101</text>
<path class="sym" d="M938 419 L955 430 L938 441 Z M972 419 L955 430 L972 441 Z"/>
<text x="955" y="458" text-anchor="middle" class="txt">XV-102</text>
<path class="sym" d="M1046 423 H1066 L1076 430 L1066 437 H1046 Z"/>

<!-- Minimum-flow control -->
{_bubble(700,215,"FT","FT-101")}
<line class="impulse" x1="700" y1="229" x2="700" y2="255"/>
{_bubble(820,180,"FIC","FIC-101")}
<g class="selectable" data-object-id="VLV-FCV101" onclick="selectObject('VLV-FCV101')">
<path class="sym" d="M501 244 L520 255 L501 266 Z M539 244 L520 255 L539 266 Z"/>
<line class="sym" x1="520" y1="255" x2="520" y2="232"/>
<path class="sym" d="M508 232 Q520 215 532 232"/>
<line class="sym" x1="508" y1="232" x2="532" y2="232"/>
<text x="520" y="284" text-anchor="middle" class="txt">FCV-101</text>
</g>

{_annotation_svg(cleanup)}

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
<div id="objectMeta" class="muted">Click V-101, P-101 or FCV-101</div>
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
<script>
const dossiers={dossier_payload};
let publicationStages={stage_payload};
const publishDefs=[
 ["design_basis","Publish Design Basis"],
 ["simulation","Publish Simulation"],
 ["configuration","Select Configuration"],
 ["process","Publish Process Data"],
 ["instrumentation","Publish Instrumentation"],
 ["mechanical","Publish Mechanical"],
 ["costing","Publish Costing"]
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
 ["design_basis","Design Basis"],
 ["process","Process"],
 ["pid","P&ID"],
 ["calculations","Calculations"],
 ["instrumentation","Instrumentation"],
 ["mechanical","Mechanical"],
 ["electrical","Electrical"],
 ["cost","Cost"],
 ["epc_vendor","EPC / Vendor"],
 ["operations","Operations"],
 ["history","History"]
];
const domainMap={{
 process:"simulation",
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
function provenance(p){{
 if(!p)return "";
 const bits=[p.source_type,p.source_id,p.source_revision?("Rev "+p.source_revision):null,p.method].filter(Boolean);
 return '<div class="prov">Source: '+bits.map(esc).join(" · ")+'</div>';
}}
function card(name,value,unit,status,p){{
 return '<div class="card"><div>'+esc(name)+'</div><div class="value">'+esc(value)+(unit?(" "+esc(unit)):"")+'</div>'+(status?'<div class="prov">Status: '+esc(status)+'</div>':"")+provenance(p)+'</div>';
}}
function recordsFor(d,key){{
 return (d.records||{{}})[key]||[];
}}
function sourceLine(p){{
 if(!p)return "";
 const bits=[p.source_type,p.source_id,p.source_revision?("Rev "+p.source_revision):null,p.method,p.note].filter(Boolean);
 return bits.join(" · ");
}}
function propertyRow(name,value,unit,p){{
 const src=sourceLine(p);
 return '<div class="property-row"><div class="property-name">'+esc(name)+'</div><div class="property-value">'+esc(value)+(unit?(" "+esc(unit)):"")+'</div>'+(src?'<div class="property-source">Source: '+esc(src)+'</div>':"")+'</div>';
}}
function propertyGroup(title,items){{
 if(!items.length)return "";
 return '<div class="property-group"><div class="property-group-title">'+esc(title)+'</div>'+items.join("")+'</div>';
}}
function renderProperties(d){{
 const groups=[];
 groups.push(propertyGroup("Identification",[
   propertyRow("Object ID",d.object_id,null,null),
   propertyRow("Tag",d.tag,null,null),
   propertyRow("Type",d.object_type||d.category,null,null),
   propertyRow("Service",d.service||"—",null,null)
 ]));
 groups.push(propertyGroup("Design Basis",(d.design_basis||[]).map(x=>propertyRow(x.name,x.value,x.unit,x.provenance))));
 const definitions=[
   ["Process / Simulation","simulation"],
   ["Calculations","process_calculation"],
   ["P&ID","pid"],
   ["Instrumentation","instrumentation"],
   ["Mechanical","mechanical"],
   ["Electrical","electrical"],
   ["Cost","cost"],
   ["EPC / Vendor","epc_vendor"],
   ["Operations","operations"]
 ];
 definitions.forEach(([title,key])=>{{
   groups.push(propertyGroup(title,recordsFor(d,key).map(x=>propertyRow(x.name,x.value,x.unit,x.provenance))));
 }});
 document.getElementById("propertiesContent").innerHTML=groups.filter(Boolean).join("")||'<div class="empty">No properties available.</div>';
}}
function renderTabs(){{
 document.getElementById("tabs").innerHTML=tabDefs.map(([id,label])=>'<button class="tab '+(activeTab===id?"active":"")+'" onclick="openTab(\''+id+'\')">'+label+'</button>').join("");
}}
function render(){{
 if(!selectedId||!dossiers[selectedId])return;
 const d=dossiers[selectedId];
 document.getElementById("objectTag").textContent=d.tag;
 document.getElementById("objectMeta").textContent=(d.object_type||d.category)+" · "+(d.service||"");
 renderTabs();
 let html="";
 if(activeTab==="overview"){{
   html=card("Object ID",d.object_id,null,null,null)+card("Type",d.object_type||d.category,null,null,null)+card("Service",d.service||"—",null,null,null);
 }} else if(activeTab==="design_basis"){{
   html=(d.design_basis||[]).map(x=>card(x.name,x.value,x.unit,x.status,x.provenance)).join("")||'<div class="empty">No linked Design Basis criteria.</div>';
 }} else if(activeTab==="history"){{
   const all=[];
   (d.design_basis||[]).forEach(x=>all.push({{name:x.name,value:x.value,unit:x.unit,status:x.status,provenance:x.provenance}}));
   Object.values(d.records||{{}}).flat().forEach(x=>all.push(x));
   html=all.map(x=>card(x.name,x.value,x.unit,x.status,x.provenance)).join("")||'<div class="empty">No provenance records yet.</div>';
 }} else {{
   const key=domainMap[activeTab];
   html=recordsFor(d,key).map(x=>card(x.name,x.value,x.unit,x.status,x.provenance)).join("")||'<div class="empty">No linked records yet for this discipline.</div>';
 }}
 document.getElementById("tabContent").innerHTML=html;
 renderProperties(d);
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
 if(selectedId&&dossiers[selectedId])renderProperties(dossiers[selectedId]);
}}
function selectObject(id){{selectedId=id;activeTab="overview";render();setInspectorMode(inspectorMode);}}
renderPublishBar();
if(dossiers["EQ-V101"])selectObject("EQ-V101");
</script>
</body></html>"""
