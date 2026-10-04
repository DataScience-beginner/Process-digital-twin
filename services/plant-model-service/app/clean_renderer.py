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
main.workspace-grid{{display:grid;grid-template-columns:270px minmax(650px,1fr) 430px;gap:10px;padding:10px;align-items:start}}
.workspace-grid.left-hidden{{grid-template-columns:minmax(650px,1fr) 430px}}
.workspace-grid.left-hidden .left-sidebar{{display:none}}
.workspace-grid.right-hidden{{grid-template-columns:270px minmax(650px,1fr)}}
.workspace-grid.right-hidden .right-sidebar{{display:none}}
.workspace-grid.left-hidden.right-hidden{{grid-template-columns:minmax(650px,1fr)}}
.left-sidebar,.side{{background:#fff;border:1px solid #aaa;padding:12px}}
.left-sidebar,.right-sidebar{{position:sticky;top:8px;max-height:calc(100vh - 20px);overflow:auto}}
.center-workspace{{min-width:0}}
.canvas-toolbar{{background:#fff;border:1px solid #aaa;border-bottom:0;padding:7px 8px;display:flex;gap:5px;align-items:center;flex-wrap:wrap}}
.canvas-btn,.workspace-btn,.tool-btn{{font-size:9px;padding:6px 8px;border:1px solid #94a3b8;background:#fff;border-radius:4px;cursor:pointer}}
.canvas-btn.active,.workspace-btn.active{{background:#0f172a;color:#fff}}
.canvas-title{{font-size:10px;font-weight:700;margin-right:auto}}
.sheet{{background:#fff;border:1px solid #777;overflow:auto}}
.embed-pane{{display:none;background:#fff;border:1px solid #777;height:760px}}
.embed-pane iframe{{width:100%;height:100%;border:0}}
.workspace-section{{border-top:1px solid #dbe1e8;margin-top:10px;padding-top:9px}}
.workspace-section:first-child{{border-top:0;margin-top:0;padding-top:0}}
.workspace-heading{{font-size:9px;font-weight:700;text-transform:uppercase;color:#475569;margin-bottom:6px;letter-spacing:.3px}}
.workspace-nav{{display:grid;gap:4px}}
.workspace-btn{{text-align:left;width:100%;box-sizing:border-box;text-decoration:none;color:#111}}
.left-publish{{display:grid;grid-template-columns:1fr auto;gap:4px;padding:0;background:transparent;border:0}}
.left-publish .pubbtn{{width:100%;text-align:left}}
.left-publish .pubstatus{{align-self:center}}
.left-publish .pubbtn.all{{grid-column:1 / 3}}
.left-publish .pubmsg{{grid-column:1 / 3;margin-left:0;padding-top:4px}}
.stencil-grid{{display:grid;grid-template-columns:1fr 1fr;gap:5px}}
.stencil{{border:1px solid #94a3b8;background:#fff;border-radius:4px;padding:7px 5px;text-align:center;font-size:8px;cursor:grab;user-select:none}}
.stencil:active{{cursor:grabbing}}
.tool-grid{{display:grid;grid-template-columns:1fr 1fr;gap:5px}}
.tool-btn{{font-size:8px}}
.tool-btn.active{{background:#dbeafe;border-color:#3b82f6;color:#1e3a8a}}
.tool-status{{font-size:8px;line-height:1.4;background:#f8fafc;border:1px solid #e2e8f0;padding:6px;margin-top:6px;color:#475569}}
.draft-object{{cursor:move}}
.draft-object .draft-shape{{fill:#fff7ed;stroke:#ea580c;stroke-width:1.5;stroke-dasharray:4 2}}
.draft-object .draft-label{{font:700 8px Arial;fill:#9a3412}}
.draft-connector{{fill:none;stroke:#ea580c;stroke-width:1.4;stroke-dasharray:5 3;cursor:pointer}}
.draft-connector.signal-kind{{stroke:#2563eb;stroke-dasharray:7 4}}
.draft-connector:hover{{stroke-width:2.4}}
.change-json{{white-space:pre-wrap;background:#0f172a;color:#e2e8f0;padding:10px;border-radius:5px;font:9px monospace;max-height:420px;overflow:auto}}
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
.calc-trace{{border:2px solid #bfdbfe;background:#f8fbff;margin:9px 0;padding:9px}}
.calc-trace-head{{display:grid;grid-template-columns:1fr 1fr;gap:5px;background:#eff6ff;border:1px solid #bfdbfe;padding:7px;font-size:9px}}
.calc-trace h5{{font-size:9px;text-transform:uppercase;color:#1e3a5f;margin:10px 0 5px}}
.calc-step{{background:#fff;border-left:3px solid #60a5fa;padding:7px;margin:6px 0;font-size:9px;line-height:1.45}}
.calc-step-title{{font-weight:700;margin-bottom:3px}} .calc-step-no{{font-size:8px;color:#64748b;text-transform:uppercase}}
.calc-step code{{white-space:normal;font-size:9px}} .calc-trace ul{{font-size:9px;line-height:1.45}}
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
@media(max-width:1180px){{
 main.workspace-grid{{grid-template-columns:230px minmax(620px,1fr)}}
 .right-sidebar{{position:static;grid-column:1 / -1;max-height:none}}
}}
@media(max-width:820px){{
 main.workspace-grid{{display:block}}
 .left-sidebar,.right-sidebar{{position:static;max-height:none;margin-bottom:8px}}
 .canvas-toolbar{{position:sticky;top:0;z-index:15}}
}}
</style>
</head>
<body>
<header>
<div><strong>Digital BDEP — Engineering View</strong><div class="muted">Staged publishing · connected P&ID + object-centric Digital Thread</div></div>
<nav><a href="/dashboard">Dashboard</a><a href="/hazop">HAZOP</a><a href="/summaries">Summaries</a><a href="/engineering-2">PID-002</a><a href="/configuration-match/CASE-NORMAL">Configuration</a><a href="/compiler/CASE-NORMAL">Compiler</a><a href="/graph">Graph View</a></nav>
</header>
<main id="workspaceGrid" class="workspace-grid">
<aside id="leftSidebar" class="left-sidebar">
  <div class="workspace-section">
    <div class="workspace-heading">Workspace</div>
    <div class="workspace-nav">
      <button class="workspace-btn active" data-canvas="pid1" onclick="switchCanvas('pid1',this)">P&ID 001 — Engineering</button>
      <button class="workspace-btn" data-canvas="plant" onclick="switchCanvas('plant',this)">Plant Model / Digital Thread</button>
      <button class="workspace-btn" data-canvas="pid2" onclick="switchCanvas('pid2',this)">P&ID 002 — Continuation</button>
      <button class="workspace-btn" data-canvas="dashboard" onclick="switchCanvas('dashboard',this)">Project Dashboard</button>
      <button class="workspace-btn" data-canvas="hazop" onclick="switchCanvas('hazop',this)">HAZOP</button>
      <button class="workspace-btn" data-canvas="summaries" onclick="switchCanvas('summaries',this)">BDEP Summaries</button>
      <button class="workspace-btn" data-canvas="configuration" onclick="switchCanvas('configuration',this)">Configuration Match</button>
      <button class="workspace-btn" data-canvas="compiler" onclick="switchCanvas('compiler',this)">Compiler / Plant Data</button>
    </div>
  </div>
  <div class="workspace-section">
    <div class="workspace-heading">Publish Project Stages</div>
    <div class="publishbar left-publish" id="publishbar"></div>
  </div>
  <div class="workspace-section">
    <div class="workspace-heading">Discipline Inspector</div>
    <div class="workspace-nav">
      <button class="workspace-btn" onclick="focusInspector('design_basis')">Design Basis</button>
      <button class="workspace-btn" onclick="focusInspector('process')">Process / Safety</button>
      <button class="workspace-btn" onclick="focusInspector('calculations')">Full Calculations</button>
      <button class="workspace-btn" onclick="focusInspector('instrumentation')">Instrumentation / DCS</button>
      <button class="workspace-btn" onclick="focusInspector('mechanical')">Technical / Mechanical</button>
      <button class="workspace-btn" onclick="focusInspector('electrical')">Electrical</button>
      <button class="workspace-btn" onclick="focusInspector('cost')">Cost Estimate</button>
      <button class="workspace-btn" onclick="focusInspector('epc_vendor')">Vendor / EPC</button>
      <button class="workspace-btn" onclick="focusInspector('operations')">Operations</button>
    </div>
  </div>
  <div class="workspace-section">
    <div class="workspace-heading">Sketch / Stencil Palette</div>
    <div class="stencil-grid">
      <div class="stencil" draggable="true" data-stencil="vessel" ondragstart="stencilDragStart(event)">Vessel</div>
      <div class="stencil" draggable="true" data-stencil="pump" ondragstart="stencilDragStart(event)">Pump</div>
      <div class="stencil" draggable="true" data-stencil="exchanger" ondragstart="stencilDragStart(event)">Exchanger</div>
      <div class="stencil" draggable="true" data-stencil="manual_valve" ondragstart="stencilDragStart(event)">Manual Valve</div>
      <div class="stencil" draggable="true" data-stencil="control_valve" ondragstart="stencilDragStart(event)">Control Valve</div>
      <div class="stencil" draggable="true" data-stencil="psv" ondragstart="stencilDragStart(event)">PSV</div>
      <div class="stencil" draggable="true" data-stencil="instrument" ondragstart="stencilDragStart(event)">Instrument</div>
      <div class="stencil" draggable="true" data-stencil="boundary" ondragstart="stencilDragStart(event)">Off-page / B.L.</div>
    </div>
    <div class="muted" style="font-size:8px;margin-top:5px">Drag onto P&ID 001. New items stay provisional until a controlled change set is prepared.</div>
  </div>
  <div class="workspace-section">
    <div class="workspace-heading">Drafting Assistance</div>
    <div class="tool-grid">
      <button id="connectorBtn" class="tool-btn" onclick="toggleConnectorMode()">Guided Connector</button>
      <button class="tool-btn" onclick="autoCorrectDrafts()">Auto-correct</button>
      <button class="tool-btn" onclick="validateDrafts()">Validate Draft</button>
      <button class="tool-btn" onclick="undoDraft()">Undo</button>
      <button class="tool-btn" onclick="clearDrafts()">Clear Draft</button>
      <button class="tool-btn" onclick="prepareChangeSet()">Prepare Change Set</button>
    </div>
    <div id="toolStatus" class="tool-status">Draft mode ready. Drop a stencil on the P&ID or start Guided Connector.</div>
  </div>
  <div class="workspace-section">
    <div class="workspace-heading">Exports</div>
    <div class="workspace-nav">
      <a class="workspace-btn" href="/export/dexpi.xml">DEXPI XML</a>
      <a class="workspace-btn" href="/export/visio.vdx">Visio VDX</a>
      <a class="workspace-btn" href="/export/drawing.dxf">CAD DXF</a>
      <a class="workspace-btn" href="/export/drawing.dwg">DWG Adapter</a>
    </div>
  </div>
</aside>
<section class="center-workspace">
  <div class="canvas-toolbar">
    <button class="canvas-btn" onclick="toggleLeftSidebar()">☰ Left</button>
    <span id="canvasTitle" class="canvas-title">P&ID 001 — Engineering Canvas</span>
    <button class="canvas-btn active" data-canvas="pid1" onclick="switchCanvas('pid1',this)">P&ID 001</button>
    <button class="canvas-btn" data-canvas="plant" onclick="switchCanvas('plant',this)">Plant Model</button>
    <button class="canvas-btn" data-canvas="pid2" onclick="switchCanvas('pid2',this)">P&ID 002</button>
    <button class="canvas-btn" onclick="toggleRightSidebar()">Right ▣</button>
  </div>
  <div id="pidCanvasPane">
    <section class="sheet">
<svg id="pidCanvas" viewBox="0 0 1120 690" ondragover="canvasDragOver(event)" ondrop="canvasDrop(event)" onmousemove="draftMove(event)" onmouseup="draftMoveEnd(event)" onmouseleave="draftMoveEnd(event)">
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
<a href="/engineering-2"><text x="1000" y="410" class="txt" style="fill:#174a77;text-decoration:underline">CONT. PID-DEMO-002</text></a>

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
<g id="draftConnectorLayer"></g>
<g id="draftLayer"></g>

<!-- Title block -->
<text class="title" x="775" y="612">DIGITAL BDEP - P&ID</text>
<text class="txt" x="775" y="629">SEPARATOR + PUMP CONFIGURATION</text>
<text class="txt" x="775" y="646">DRAWING: PID-DEMO-001</text>
<text class="txt" x="945" y="612">REV: A</text>
<text class="txt" x="945" y="629">STATUS: {status}</text>
<text class="txt" x="945" y="646">VIEW: ENGINEERING</text>
</svg>
    </section>
  </div>
  <div id="embedPane" class="embed-pane"><iframe id="workspaceFrame" title="Digital BDEP workspace view"></iframe></div>
</section>
<aside id="rightSidebar" class="side right-sidebar">
<div class="object-head">
<h3 id="objectTag">Digital BDEP Object</h3>
<div id="objectMeta" class="muted">Click any visible equipment, valve, instrument, boundary or line</div>
<div class="object-actions">
<button class="detail-btn" onclick="openDetailModal()">↗ Detailed View</button>
<button class="detail-btn" onclick="popOutDetail()">⧉ Pop out / Calculation Workspace</button>
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
<dialog id="changeDialog">
<div class="dialog-head">
<div><strong>Proposed Drawing / Plant Model Change Set</strong><div class="muted">Draft-only preview. Nothing is applied to the semantic plant model until explicitly promoted through the controlled change workflow.</div></div>
<button class="dialog-close" onclick="document.getElementById('changeDialog').close()">Close</button>
</div>
<div class="dialog-body"><pre id="changeJson" class="change-json"></pre></div>
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
let activeCanvas="pid1";
let draftCounter=0;
let draftConnectionCounter=0;
const draftObjects=[];
const draftConnections=[];
const draftActions=[];
let connectorMode=false;
let connectorSource=null;
let movingDraft=null;
let autoSnap=true;
const svgNS="http://www.w3.org/2000/svg";

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
   id:e.engineering_record_id||e.id,
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
function traceSection(trace){{
 if(!trace)return '';
 let h='<div class="calc-trace"><h4>Full Calculation Trace</h4>';
 h+='<div class="calc-trace-head">'
   +'<div><b>Trace ID:</b> '+esc(trace.trace_id||'—')+'</div>'
   +'<div><b>Type:</b> '+esc(trace.calculation_type||'—')+'</div>'
   +'<div><b>Service:</b> '+esc(trace.service_version||'—')+'</div>'
   +'<div><b>Qualification:</b> '+esc(trace.qualification||'—')+'</div>'
   +'</div>';
 if(trace.input_sources&&trace.input_sources.length)h+='<h5>Input Traceability</h5>'+detailTable(trace.input_sources);
 if(trace.steps&&trace.steps.length){{
   h+='<h5>Equation / Substitution Steps</h5>';
   trace.steps.forEach(s=>{{
     h+='<div class="calc-step"><div class="calc-step-no">Step '+esc(s.step||'')+'</div>'
       +'<div class="calc-step-title">'+esc(s.title||'')+'</div>'
       +'<div><b>Equation:</b> <code>'+esc(s.equation||'—')+'</code></div>'
       +'<div><b>Substitution:</b> <code>'+esc(s.substitution||'—')+'</code></div>'
       +'<div><b>Result:</b> '+formatValue(s.result,s.unit||null)+'</div>'
       +(s.note?'<div class="detail-sub"><b>Note:</b> '+esc(s.note)+'</div>':'')
       +'</div>';
   }});
 }}
 if(trace.selection_checks&&trace.selection_checks.length)h+='<h5>Candidate / Selection Checks</h5>'+detailTable(trace.selection_checks);
 if(trace.validation_checks&&trace.validation_checks.length)h+='<h5>Validation Checks</h5>'+detailTable(trace.validation_checks);
 [['Assumptions','assumptions'],['Limitations / Qualification Gaps','limitations'],['Downstream Consumers','downstream_consumers']].forEach(([title,key])=>{{
   const rows=trace[key]||[];
   if(rows.length)h+='<h5>'+esc(title)+'</h5><ul>'+rows.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>';
 }});
 return h+'</div>';
}}
function calculationDetail(record){{
 const d=((record&&record.metadata)||{{}}).calculation_detail;
 if(!d)return '';
 let h='<div class="detail-section"><h4>Calculation detail</h4>';
 h+='<b>Inputs</b>'+detailList(d.inputs||[]);
 h+='<b>Criteria / Limits</b>'+detailList(d.criteria||[]);
 if(d.case_results&&d.case_results.length)h+='<b>Case Results</b>'+detailTable(d.case_results);
 if(d.relief_scenarios&&d.relief_scenarios.length)h+='<b>Relief Scenario Register</b>'+detailTable(d.relief_scenarios);
 if(d.trace)h+=traceSection(d.trace);
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
 window.open('/workspace/'+encodeURIComponent(selectedId),'_blank','noopener');
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
function canvasUrl(kind){{
 const urls={{
   plant:"/graph",
   pid2:"/engineering-2",
   dashboard:"/dashboard",
   hazop:"/hazop",
   summaries:"/summaries",
   configuration:"/configuration-match/CASE-NORMAL",
   compiler:"/compiler/CASE-NORMAL"
 }};
 return urls[kind]||null;
}}
function canvasLabel(kind){{
 const labels={{
   pid1:"P&ID 001 — Engineering Canvas",
   plant:"Plant Model / Digital Thread",
   pid2:"P&ID 002 — Continuation",
   dashboard:"Project Dashboard",
   hazop:"HAZOP Digital Thread",
   summaries:"Generated BDEP Summaries",
   configuration:"Configuration Match",
   compiler:"Compiler / Plant Data"
 }};
 return labels[kind]||kind;
}}
function switchCanvas(kind,button){{
 activeCanvas=kind;
 const pid=document.getElementById("pidCanvasPane");
 const embed=document.getElementById("embedPane");
 const frame=document.getElementById("workspaceFrame");
 document.getElementById("canvasTitle").textContent=canvasLabel(kind);
 document.querySelectorAll("[data-canvas]").forEach(x=>x.classList.toggle("active",x.dataset.canvas===kind));
 if(kind==="pid1"){{
   pid.style.display="block";
   embed.style.display="none";
   frame.removeAttribute("src");
 }} else {{
   pid.style.display="none";
   embed.style.display="block";
   const url=canvasUrl(kind);
   if(url&&frame.getAttribute("src")!==url)frame.setAttribute("src",url);
 }}
}}
function toggleLeftSidebar(){{document.getElementById("workspaceGrid").classList.toggle("left-hidden");}}
function toggleRightSidebar(){{document.getElementById("workspaceGrid").classList.toggle("right-hidden");}}
function focusInspector(tab){{
 if(activeCanvas!=="pid1")switchCanvas("pid1");
 if(!selectedId&&entities["EQ-V101"])selectedId="EQ-V101";
 setInspectorMode("tabs");
 openTab(tab);
 document.getElementById("rightSidebar").scrollTo({{top:0,behavior:"smooth"}});
}}
function setToolStatus(message){{document.getElementById("toolStatus").textContent=message;}}
function stencilDragStart(ev){{
 ev.dataTransfer.setData("text/digital-bdep-stencil",ev.currentTarget.dataset.stencil);
 ev.dataTransfer.effectAllowed="copy";
 setToolStatus("Dragging "+humanKey(ev.currentTarget.dataset.stencil)+" — drop on P&ID 001.");
}}
function canvasDragOver(ev){{
 if(activeCanvas!=="pid1")return;
 ev.preventDefault();
 ev.dataTransfer.dropEffect="copy";
}}
function svgPointFromEvent(ev){{
 const svg=document.getElementById("pidCanvas");
 const pt=svg.createSVGPoint();
 pt.x=ev.clientX;pt.y=ev.clientY;
 const matrix=svg.getScreenCTM();
 return matrix?pt.matrixTransform(matrix.inverse()):{{x:ev.offsetX,y:ev.offsetY}};
}}
function snap(v){{return autoSnap?Math.round(v/10)*10:v;}}
function nextDraftTag(type){{
 const prefix={{vessel:"V-NEW",pump:"P-NEW",exchanger:"E-NEW",manual_valve:"XV-NEW",control_valve:"CV-NEW",psv:"PSV-NEW",instrument:"I-NEW",boundary:"BND-NEW"}}[type]||"OBJ-NEW";
 return prefix+"-"+draftCounter;
}}
function draftCategory(type){{
 if(["vessel","pump","exchanger"].includes(type))return "equipment";
 if(["manual_valve","control_valve","psv"].includes(type))return "valve";
 if(type==="instrument")return "instrument";
 if(type==="boundary")return "boundary";
 return "draft";
}}
function draftMarkup(type,tag){{
 const label='<text class="draft-label" x="0" y="34" text-anchor="middle">'+esc(tag)+'</text>';
 if(type==="vessel")return '<rect class="draft-shape" x="-23" y="-38" width="46" height="76" rx="18"/>'+label;
 if(type==="pump")return '<circle class="draft-shape" cx="0" cy="0" r="22"/><path class="draft-shape" d="M-18 0 C-3 -18 17 -15 22 0 C8 3 2 10 -5 16"/>'+label;
 if(type==="exchanger")return '<rect class="draft-shape" x="-34" y="-22" width="68" height="44" rx="7"/><line class="draft-shape" x1="-26" y1="16" x2="26" y2="-16"/><line class="draft-shape" x1="-26" y1="-16" x2="26" y2="16"/>'+label;
 if(type==="manual_valve")return '<path class="draft-shape" d="M-18 -10 L0 0 L-18 10 Z M18 -10 L0 0 L18 10 Z"/>'+label;
 if(type==="control_valve")return '<path class="draft-shape" d="M-18 -10 L0 0 L-18 10 Z M18 -10 L0 0 L18 10 Z"/><line class="draft-shape" x1="0" y1="0" x2="0" y2="-22"/><path class="draft-shape" d="M-11 -22 Q0 -37 11 -22"/><line class="draft-shape" x1="-11" y1="-22" x2="11" y2="-22"/>'+label;
 if(type==="psv")return '<path class="draft-shape" d="M-13 8 L13 8 L0 -14 Z"/><line class="draft-shape" x1="0" y1="-14" x2="0" y2="-27"/><line class="draft-shape" x1="-8" y1="-27" x2="8" y2="-27"/>'+label;
 if(type==="instrument")return '<circle class="draft-shape" cx="0" cy="0" r="14"/><text class="draft-label" x="0" y="3" text-anchor="middle">I</text>'+label;
 if(type==="boundary")return '<path class="draft-shape" d="M-18 -7 H8 L18 0 L8 7 H-18 Z"/>'+label;
 return '<circle class="draft-shape" cx="0" cy="0" r="12"/>'+label;
}}
function canvasDrop(ev){{
 if(activeCanvas!=="pid1")return;
 ev.preventDefault();
 const type=ev.dataTransfer.getData("text/digital-bdep-stencil");
 if(!type)return;
 const p=svgPointFromEvent(ev);
 createDraftObject(type,snap(Math.max(55,Math.min(1060,p.x))),snap(Math.max(55,Math.min(560,p.y))));
}}
function createDraftObject(type,x,y){{
 draftCounter+=1;
 const id="DRAFT-OBJ-"+draftCounter;
 const tag=nextDraftTag(type);
 const g=document.createElementNS(svgNS,"g");
 g.setAttribute("id","svg-"+id);
 g.setAttribute("class","draft-object selectable");
 g.setAttribute("data-object-id",id);
 g.setAttribute("transform","translate("+x+" "+y+")");
 g.setAttribute("onmousedown","draftMoveStart(event,'"+id+"')");
 g.setAttribute("onclick","selectEntity('"+id+"')");
 g.innerHTML=draftMarkup(type,tag);
 document.getElementById("draftLayer").appendChild(g);
 const obj={{id,type,tag,x,y,category:draftCategory(type),object_type:"provisional_"+type,service:"Provisional sketch object",status:"DRAFT"}};
 draftObjects.push(obj);
 draftActions.push({{action:"add_object",id}});
 entities[id]={{id,tag,category:obj.category,object_type:obj.object_type,service:obj.service,properties:{{draft:true}},children:[],relationships:[],connected_lines:[],status:"DRAFT"}};
 selectEntity(id);
 setToolStatus(tag+" added as a provisional draft object. Drag to reposition or connect it.");
}}
function draftMoveStart(ev,id){{if(ev.button!==0)return;movingDraft=id;ev.stopPropagation();}}
function draftMove(ev){{
 if(!movingDraft)return;
 ev.preventDefault();
 const p=svgPointFromEvent(ev);
 const obj=draftObjects.find(x=>x.id===movingDraft);
 if(!obj)return;
 obj.x=snap(Math.max(55,Math.min(1060,p.x)));
 obj.y=snap(Math.max(55,Math.min(560,p.y)));
 document.getElementById("svg-"+obj.id).setAttribute("transform","translate("+obj.x+" "+obj.y+")");
 redrawDraftConnections();
}}
function draftMoveEnd(){{movingDraft=null;}}
function entityElement(id){{
 const safe=(window.CSS&&CSS.escape)?CSS.escape(id):id.replace(/"/g,"");
 return document.querySelector('[data-object-id="'+safe+'"]')||document.querySelector('[data-route-entity-id="'+safe+'"]');
}}
function entityCenter(id){{
 const el=entityElement(id);
 if(!el||typeof el.getBBox!=="function")return null;
 if(el.classList&&el.classList.contains("draft-object")){{
   const obj=draftObjects.find(x=>x.id===id);
   return obj?{{x:obj.x,y:obj.y}}:null;
 }}
 const b=el.getBBox();
 return {{x:b.x+b.width/2,y:b.y+b.height/2}};
}}
function connectorKindSuggestion(sourceId,targetId){{
 const a=entityFor(sourceId)||{{}},b=entityFor(targetId)||{{}};
 const inst=a.category==="instrument"||b.category==="instrument";
 const control=(a.object_type||"").includes("control")||(b.object_type||"").includes("control");
 return (inst||control)?"signal":"process";
}}
function toggleConnectorMode(){{
 connectorMode=!connectorMode;
 connectorSource=null;
 document.getElementById("connectorBtn").classList.toggle("active",connectorMode);
 setToolStatus(connectorMode?"Guided Connector ON — select source entity, then target entity.":"Guided Connector OFF.");
}}
function guidedSelect(id){{
 if(!connectorMode)return false;
 if(!connectorSource){{
   connectorSource=id;
   setToolStatus("Connector source: "+(entityFor(id)?.tag||id)+". Now select the target.");
   return true;
 }}
 if(connectorSource===id){{setToolStatus("Target must be different from source.");return true;}}
 createDraftConnection(connectorSource,id);
 connectorSource=null;
 connectorMode=false;
 document.getElementById("connectorBtn").classList.remove("active");
 return true;
}}
function createDraftConnection(sourceId,targetId){{
 const s=entityCenter(sourceId),t=entityCenter(targetId);
 if(!s||!t){{setToolStatus("Could not resolve visible anchors for the requested connection.");return;}}
 draftConnectionCounter+=1;
 const id="DRAFT-CONN-"+draftConnectionCounter;
 const kind=connectorKindSuggestion(sourceId,targetId);
 const conn={{id,source_id:sourceId,target_id:targetId,kind,status:"DRAFT"}};
 draftConnections.push(conn);
 draftActions.push({{action:"add_connection",id}});
 entities[id]={{id,tag:id,category:"connection",object_type:"provisional_"+kind+"_connection",service:"Provisional guided connector",from:{{id:sourceId,label:entityFor(sourceId)?.tag||sourceId}},to:{{id:targetId,label:entityFor(targetId)?.tag||targetId}},through:[],path:[],connected_lines:[],status:"DRAFT"}};
 redrawDraftConnections();
 setToolStatus("Guided connector created. Suggested type: "+kind.toUpperCase()+". Auto-correct can snap and orthogonalize it.");
 selectEntity(id);
}}
function redrawDraftConnections(){{
 const layer=document.getElementById("draftConnectorLayer");
 layer.innerHTML="";
 draftConnections.forEach(conn=>{{
   const s=entityCenter(conn.source_id),t=entityCenter(conn.target_id);
   if(!s||!t)return;
   const mid=snap((s.x+t.x)/2);
   const poly=document.createElementNS(svgNS,"polyline");
   poly.setAttribute("class","draft-connector "+(conn.kind==="signal"?"signal-kind":""));
   poly.setAttribute("points",s.x+","+s.y+" "+mid+","+s.y+" "+mid+","+t.y+" "+t.x+","+t.y);
   poly.setAttribute("data-route-entity-id",conn.id);
   poly.setAttribute("onclick","selectEntity('"+conn.id+"')");
   layer.appendChild(poly);
 }});
}}
function autoCorrectDrafts(){{
 const occupied=[];
 draftObjects.forEach(obj=>{{
   obj.x=snap(Math.max(60,Math.min(1050,obj.x)));
   obj.y=snap(Math.max(60,Math.min(555,obj.y)));
   let guard=0;
   while(occupied.some(p=>Math.abs(p.x-obj.x)<55&&Math.abs(p.y-obj.y)<45)&&guard<8){{obj.y=snap(Math.min(555,obj.y+60));guard+=1;}}
   occupied.push({{x:obj.x,y:obj.y}});
   const el=document.getElementById("svg-"+obj.id);
   if(el)el.setAttribute("transform","translate("+obj.x+" "+obj.y+")");
 }});
 redrawDraftConnections();
 setToolStatus("Auto-correct complete: grid snap, drawing-boundary clamp, basic overlap separation and orthogonal connector routing applied.");
}}
function validateDrafts(){{
 const issues=[];
 draftObjects.forEach(obj=>{{
   const connected=draftConnections.some(c=>c.source_id===obj.id||c.target_id===obj.id);
   if(!connected)issues.push(obj.tag+" is not connected.");
   if(obj.x<50||obj.x>1070||obj.y<50||obj.y>570)issues.push(obj.tag+" is outside the usable drawing zone.");
 }});
 for(let i=0;i<draftObjects.length;i++)for(let j=i+1;j<draftObjects.length;j++){{
   const a=draftObjects[i],b=draftObjects[j];
   if(Math.abs(a.x-b.x)<45&&Math.abs(a.y-b.y)<35)issues.push(a.tag+" overlaps "+b.tag+".");
 }}
 setToolStatus(issues.length?("Draft validation: "+issues.length+" issue(s) — "+issues.slice(0,4).join(" | ")):("Draft validation GREEN — "+draftObjects.length+" provisional object(s), "+draftConnections.length+" connector(s)."));
 return issues;
}}
function removeDraftObject(id){{
 const idx=draftObjects.findIndex(x=>x.id===id);
 if(idx>=0)draftObjects.splice(idx,1);
 document.getElementById("svg-"+id)?.remove();
 delete entities[id];
 for(let i=draftConnections.length-1;i>=0;i--)if(draftConnections[i].source_id===id||draftConnections[i].target_id===id){{delete entities[draftConnections[i].id];draftConnections.splice(i,1);}}
 redrawDraftConnections();
}}
function removeDraftConnection(id){{
 const idx=draftConnections.findIndex(x=>x.id===id);
 if(idx>=0)draftConnections.splice(idx,1);
 delete entities[id];
 redrawDraftConnections();
}}
function undoDraft(){{
 const action=draftActions.pop();
 if(!action){{setToolStatus("Nothing to undo.");return;}}
 if(action.action==="add_object")removeDraftObject(action.id);else if(action.action==="add_connection")removeDraftConnection(action.id);
 if(!entityFor(selectedId)&&entities["EQ-V101"])selectEntity("EQ-V101");
 setToolStatus("Undid "+humanKey(action.action)+".");
}}
function clearDrafts(){{
 [...draftObjects].forEach(x=>delete entities[x.id]);
 [...draftConnections].forEach(x=>delete entities[x.id]);
 draftObjects.length=0;draftConnections.length=0;draftActions.length=0;
 document.getElementById("draftLayer").innerHTML="";
 document.getElementById("draftConnectorLayer").innerHTML="";
 if(entities["EQ-V101"])selectEntity("EQ-V101");
 setToolStatus("All provisional sketch objects and connectors cleared. Published engineering model unchanged.");
}}
function prepareChangeSet(){{
 const issues=validateDrafts();
 const payload={{
   status:"PROPOSED_NOT_APPLIED",
   drawing_id:"PID-DEMO-001",
   base_revision:"A",
   objects:draftObjects.map(x=>({{id:x.id,provisional_tag:x.tag,type:x.type,category:x.category,position:{{x:x.x,y:x.y}}}})),
   connections:draftConnections.map(x=>({{id:x.id,source:x.source_id,target:x.target_id,suggested_kind:x.kind}})),
   validation:{{issue_count:issues.length,issues}},
   promotion_rule:"Requires explicit controlled engineering change/publish workflow before semantic Plant Model write-back"
 }};
 document.getElementById("changeJson").textContent=JSON.stringify(payload,null,2);
 document.getElementById("changeDialog").showModal();
}}
function selectEntity(id){{
 if(!entityFor(id))return;
 const usedByConnector=guidedSelect(id);
 selectedId=id;activeTab="overview";render();setInspectorMode(inspectorMode);
 if(usedByConnector)return;
}}
function selectObject(id){{selectEntity(id);}}
renderPublishBar();
if(entities["EQ-V101"])selectEntity("EQ-V101");
</script>
</body></html>"""
