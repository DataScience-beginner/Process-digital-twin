from __future__ import annotations

import html
import json

from .drafting import STANDARD_PROFILE, master_for
from .models import PlantModel
from .views import DrawingView, Representation, build_demo_pid_view


def _instrument_code(tag: str) -> str:
    return tag.split("-")[0]


def _symbol_svg(obj, rep: Representation) -> str:
    master = master_for(obj)
    x, y = rep.position.x, rep.position.y
    tag = html.escape(obj.tag)
    semantic_id = html.escape(obj.id)
    representation_id = html.escape(rep.representation_id)
    onclick = f"selectObject('{semantic_id}')"
    attrs = (
        f'data-semantic-object-id="{semantic_id}" '
        f'data-representation-id="{representation_id}"'
    )
    w, h = master.width, master.height

    if master.key == "equipment.vertical_separator":
        left, top = x - w / 2, y - h / 2
        right, bottom = x + w / 2, y + h / 2
        return (
            f'<g class="obj" {attrs} onclick="{onclick}">'
            f'<path class="sym" d="M{left},{top+18} Q{x},{top-8} {right},{top+18} '
            f'L{right},{bottom-18} Q{x},{bottom+8} {left},{bottom-18} Z"/>'
            f'<text class="tag" x="{x}" y="{y+4}" text-anchor="middle">{tag}</text>'
            f'</g>'
        )

    if master.key == "equipment.centrifugal_pump":
        return (
            f'<g class="obj" {attrs} onclick="{onclick}">'
            f'<circle class="sym" cx="{x}" cy="{y}" r="24"/>'
            f'<path class="sym" d="M{x-22},{y} C{x-2},{y-22} {x+20},{y-18} {x+24},{y} '
            f'C{x+8},{y+3} {x},{y+12} {x-8},{y+20}"/>'
            f'<text class="tag" x="{x}" y="{y+43}" text-anchor="middle">{tag}</text>'
            f'</g>'
        )

    if master.key.startswith("nozzle."):
        # Nozzle nodes remain semantic/drawing anchors but are not displayed
        # as graph nodes in the conventional engineering view.
        return ""

    if master.key == "valve.isolation_valve":
        return (
            f'<g class="obj" {attrs} onclick="{onclick}">'
            f'<path class="sym" d="M{x-w/2},{y-h/2} L{x},{y} L{x-w/2},{y+h/2} Z '
            f'M{x+w/2},{y-h/2} L{x},{y} L{x+w/2},{y+h/2} Z"/>'
            f'<text class="smalltag" x="{x}" y="{y+25}" text-anchor="middle">{tag}</text></g>'
        )

    if master.key == "valve.check_valve":
        return (
            f'<g class="obj" {attrs} onclick="{onclick}">'
            f'<path class="sym" d="M{x-15},{y-10} L{x+5},{y} L{x-15},{y+10} Z"/>'
            f'<line class="sym" x1="{x+8}" y1="{y-12}" x2="{x+8}" y2="{y+12}"/>'
            f'<text class="smalltag" x="{x}" y="{y+25}" text-anchor="middle">{tag}</text></g>'
        )

    if master.key == "valve.control_valve":
        body_y = y + 6
        return (
            f'<g class="obj" {attrs} onclick="{onclick}">'
            f'<path class="sym" d="M{x-16},{body_y-10} L{x},{body_y} L{x-16},{body_y+10} Z '
            f'M{x+16},{body_y-10} L{x},{body_y} L{x+16},{body_y+10} Z"/>'
            f'<line class="sym" x1="{x}" y1="{body_y-10}" x2="{x}" y2="{y-8}"/>'
            f'<path class="sym" d="M{x-12},{y-8} Q{x},{y-20} {x+12},{y-8} Z"/>'
            f'<text class="smalltag" x="{x}" y="{y+30}" text-anchor="middle">{tag}</text></g>'
        )

    if master.key == "valve.relief_valve":
        return (
            f'<g class="obj" {attrs} onclick="{onclick}">'
            f'<path class="sym" d="M{x-12},{y+10} L{x+12},{y+10} L{x},{y-8} Z"/>'
            f'<line class="sym" x1="{x}" y1="{y-8}" x2="{x}" y2="{y-20}"/>'
            f'<line class="sym" x1="{x-8}" y1="{y-20}" x2="{x+8}" y2="{y-20}"/>'
            f'<text class="smalltag" x="{x+27}" y="{y+3}">{tag}</text></g>'
        )

    if master.key in {"instrument.bubble", "instrument.flow_transmitter_inline"}:
        return (
            f'<g class="obj" {attrs} onclick="{onclick}">'
            f'<circle class="inst" cx="{x}" cy="{y}" r="14"/>'
            f'<text class="insttext" x="{x}" y="{y+3}" text-anchor="middle">{_instrument_code(tag)}</text>'
            f'<text class="smalltag" x="{x}" y="{y+27}" text-anchor="middle">{tag}</text></g>'
        )

    if master.key == "junction.branch":
        return (
            f'<g class="obj" {attrs} onclick="{onclick}">'
            f'<circle cx="{x}" cy="{y}" r="2.8" fill="#000"/></g>'
        )

    if master.key == "junction.boundary":
        return (
            f'<g class="obj" {attrs} onclick="{onclick}">'
            f'<path class="sym" d="M{x-15},{y-7} H{x+7} L{x+15},{y} L{x+7},{y+7} H{x-15} Z"/>'
            f'<text class="smalltag" x="{x}" y="{y+22}" text-anchor="middle">{tag}</text></g>'
        )

    raise KeyError(master.key)


def _route_svg(view: DrawingView) -> str:
    paths = []
    class_map = {
        "process": "process",
        "signal": "signal",
        "association": "assoc",
    }
    for route in view.routes:
        points = route.points
        d = f"M{points[0].x},{points[0].y}" + "".join(
            f" L{point.x},{point.y}" for point in points[1:]
        )
        css_class = class_map.get(route.line_style, "assoc")
        paths.append(
            f'<path class="{css_class}" d="{d}" '
            f'data-semantic-edge-id="{html.escape(route.semantic_edge_id)}" '
            f'data-route-id="{html.escape(route.route_id)}"/>'
        )
    return "".join(paths)


def _sheet_frame(project_id: str) -> str:
    p = STANDARD_PROFILE
    w, h, m = p.sheet_width, p.sheet_height, p.margin
    inner_w, inner_h = w - 2*m, h - 2*m
    col_w = inner_w / p.grid_columns
    row_h = (inner_h - p.title_block_height) / p.grid_rows

    grid = []
    for i in range(p.grid_columns):
        x = m + col_w * (i + 0.5)
        grid.append(f'<text class="gridtxt" x="{x}" y="{m-8}" text-anchor="middle">{i+1}</text>')
        grid.append(f'<text class="gridtxt" x="{x}" y="{h-m+14}" text-anchor="middle">{i+1}</text>')

    letters = "ABCDE"
    for i in range(p.grid_rows):
        y = m + row_h * (i + 0.5)
        grid.append(f'<text class="gridtxt" x="{m-12}" y="{y+3}" text-anchor="middle">{letters[i]}</text>')
        grid.append(f'<text class="gridtxt" x="{w-m+12}" y="{y+3}" text-anchor="middle">{letters[i]}</text>')

    title_y = h - m - p.title_block_height
    return (
        f'<rect class="border" x="{m}" y="{m}" width="{inner_w}" height="{inner_h}"/>'
        + "".join(grid)
        + f'<line class="border" x1="{m}" y1="{title_y}" x2="{w-m}" y2="{title_y}"/>'
        + f'<line class="border" x1="{w-390}" y1="{title_y}" x2="{w-390}" y2="{h-m}"/>'
        + f'<line class="thin" x1="{w-245}" y1="{title_y}" x2="{w-245}" y2="{h-m}"/>'
        + f'<text class="title" x="{w-375}" y="{title_y+24}">DIGITAL BDEP - P&ID CONCEPT</text>'
        + f'<text class="title2" x="{w-375}" y="{title_y+45}">PROCESS & INSTRUMENTATION DIAGRAM</text>'
        + f'<text class="title2" x="{w-375}" y="{title_y+64}">PROJECT: {html.escape(project_id)}</text>'
        + f'<text class="smalltag" x="{w-230}" y="{title_y+24}">DRAWING: PID-DEMO-001</text>'
        + f'<text class="smalltag" x="{w-230}" y="{title_y+43}">REV: A</text>'
        + f'<text class="smalltag" x="{w-230}" y="{title_y+62}">STATUS: DEVELOPMENT</text>'
    )


def render_pid_html(model: PlantModel) -> str:
    view = build_demo_pid_view(model)
    object_data = {obj.id: obj.model_dump(mode="json") for obj in model.objects}
    payload = json.dumps(object_data).replace("</", "<\\/")

    reps_by_id = {rep.semantic_object_id: rep for rep in view.representations}
    symbols = "".join(
        _symbol_svg(obj, reps_by_id[obj.id])
        for obj in model.objects
        if obj.id in reps_by_id
    )
    routes = _route_svg(view)

    annotations = """
    <text class="linetag" x="315" y="414">L-V101-LIQ</text>
    <text class="linetag" x="790" y="417">L-P101-DIS</text>
    <text class="linetag" x="650" y="263">L-P101-REC</text>
    <text class="note" x="55" y="640">NOTES:</text>
    <text class="note" x="55" y="655">1. DEVELOPMENT P&ID - SYMBOLS AND DRAFTING CONVENTIONS UNDER QUALIFICATION.</text>
    <text class="note" x="55" y="670">2. DIGITAL THREAD METADATA IS AVAILABLE IN THE GRAPH VIEW.</text>
    """

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP Engineering View</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#e5e7eb;color:#111}}
header{{padding:12px 18px;background:#fff;border-bottom:1px solid #aaa}}
main{{display:grid;grid-template-columns:minmax(900px,1fr) 300px;gap:12px;padding:12px}}
.viewer{{background:#fff;border:1px solid #999;overflow:auto}} .side{{background:#fff;border:1px solid #aaa;padding:14px}}
svg{{width:100%;min-width:1180px;height:auto;background:#fff}}
.border{{fill:none;stroke:#000;stroke-width:1.2}} .thin{{stroke:#000;stroke-width:.7}}
.sym{{fill:none;stroke:#000;stroke-width:1.5;stroke-linejoin:miter;stroke-linecap:square}}
.inst{{fill:#fff;stroke:#000;stroke-width:1.3}} .nozzle-dot{{fill:#fff;stroke:#000;stroke-width:1}}
.process{{fill:none;stroke:#000;stroke-width:1.5;stroke-linecap:square;stroke-linejoin:miter}}
.signal{{fill:none;stroke:#000;stroke-width:1.0;stroke-dasharray:7 4}}
.assoc{{fill:none;stroke:#000;stroke-width:.8;stroke-dasharray:2 3}}
.tag{{font:700 11px Arial}} .smalltag{{font:8px Arial}} .insttext{{font:700 8px Arial}}
.linetag{{font:8px Arial}} .note{{font:7px Arial}} .gridtxt{{font:7px Arial}}
.title{{font:700 10px Arial}} .title2{{font:8px Arial}} .obj{{cursor:pointer}}
.obj:hover .sym,.obj:hover .inst,.obj:hover .nozzle-dot{{stroke:#555;stroke-width:2}}
.muted{{font-size:11px;color:#666}} .row{{padding:6px 0;border-bottom:1px solid #ddd;font-size:11px}}
.section{{font-size:10px;font-weight:700;margin-top:14px;text-transform:uppercase}}
</style>
</head>
<body>
<header style="display:flex;justify-content:space-between;align-items:center"><div><strong>Digital BDEP — Engineering View</strong><span class="muted"> · Conventional P&ID presentation</span></div><nav><a href="/engineering" style="margin-right:12px"><strong>Engineering View</strong></a><a href="/graph">Graph View</a></nav></header>
<main>
<section class="viewer"><svg viewBox="0 0 1180 760">
{_sheet_frame(model.project_id)}
{routes}
{symbols}
{annotations}
</svg></section>
<aside class="side">
<h3 id="tag">V-101</h3><div id="kind" class="muted"></div>
<div class="section">Semantic object</div><div id="details"></div>
<div class="section">Ports / node</div><div id="ports"></div>
<div class="section">Engineering view</div>
<div class="row">Conventional P&ID presentation</div>
<div class="row">Digital-thread metadata hidden from the drawing</div>
<div class="row"><a href="/graph">Open Graph View</a></div>
</aside>
</main>
<script>
const objects={payload};
function selectObject(id){{
 const o=objects[id];
 document.getElementById('tag').textContent=o.tag;
 document.getElementById('kind').textContent=o.category+' · '+(o.equipment_type||o.valve_type||o.instrument_type||o.junction_type||o.nozzle_type||'');
 document.getElementById('details').innerHTML='<div class="row"><b>ID:</b> '+o.id+'</div><div class="row"><b>Service:</b> '+(o.service||'—')+'</div>';
 document.getElementById('ports').innerHTML=(o.ports||[]).map(p=>'<div class="row"><b>'+p.name+'</b> · '+p.kind+' / '+p.direction+'</div>').join('')||'<div class="row">No direct port</div>';
}}
selectObject('EQ-V101');
</script>
</body></html>"""
