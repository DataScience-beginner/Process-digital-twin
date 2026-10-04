from __future__ import annotations

import html
import json

from .drafting import STANDARD_PROFILE, master_for
from .models import PlantModel


VIEW_POSITIONS = {
    "EQ-V101": (210, 300),
    "INS-PT101": (105, 245),
    "INS-PI101": (105, 300),
    "INS-LT101": (310, 285),
    "INS-LI101": (310, 335),
    "INS-LIC101": (420, 220),
    "VLV-LCV101": (420, 430),
    "VLV-PSV101": (235, 160),
    "BOUND-RELIEF": (235, 95),
    "VLV-VENT101": (150, 160),
    "BOUND-VENT": (82, 160),
    "VLV-DRAIN101": (210, 525),
    "BOUND-DRAIN": (210, 585),
    "VLV-XV101": (535, 430),
    "EQ-P101": (655, 430),
    "JUNC-P101-DIS": (755, 430),
    "VLV-NRV101": (850, 430),
    "VLV-XV102": (940, 430),
    "BOUND-PRODUCT": (1055, 430),
    "INS-FT101": (755, 275),
    "INS-FIC101": (875, 205),
    "VLV-FCV101": (555, 275),
    "INS-PI101S": (610, 360),
    "INS-PI101D": (700, 360),
}


def _instrument_code(tag: str) -> str:
    return tag.split("-")[0]


def _symbol_svg(obj, x: int, y: int) -> str:
    master = master_for(obj)
    tag = html.escape(obj.tag)
    oid = html.escape(obj.id)
    onclick = f"selectObject('{oid}')"
    w, h = master.width, master.height

    if master.key == "equipment.vertical_separator":
        left, top = x - w / 2, y - h / 2
        right, bottom = x + w / 2, y + h / 2
        return (
            f'<g class="obj" onclick="{onclick}">'
            f'<path class="sym" d="M{left},{top+18} Q{x},{top-8} {right},{top+18} '
            f'L{right},{bottom-18} Q{x},{bottom+8} {left},{bottom-18} Z"/>'
            f'<line class="nozzle" x1="{left-16}" y1="{y-14}" x2="{left}" y2="{y-14}"/>'
            f'<line class="nozzle" x1="{x}" y1="{top-14}" x2="{x}" y2="{top}"/>'
            f'<line class="nozzle" x1="{x}" y1="{bottom}" x2="{x}" y2="{bottom+18}"/>'
            f'<line class="nozzle" x1="{right}" y1="{y-38}" x2="{right+16}" y2="{y-38}"/>'
            f'<text class="tag" x="{x}" y="{y+4}" text-anchor="middle">{tag}</text>'
            f'</g>'
        )

    if master.key == "equipment.centrifugal_pump":
        return (
            f'<g class="obj" onclick="{onclick}">'
            f'<circle class="sym" cx="{x}" cy="{y}" r="24"/>'
            f'<path class="sym" d="M{x-22},{y} C{x-2},{y-22} {x+20},{y-18} {x+24},{y} '
            f'C{x+8},{y+3} {x},{y+12} {x-8},{y+20}"/>'
            f'<line class="sym" x1="{x+24}" y1="{y}" x2="{x+39}" y2="{y}"/>'
            f'<text class="tag" x="{x}" y="{y+43}" text-anchor="middle">{tag}</text>'
            f'</g>'
        )

    if master.key == "valve.isolation_valve":
        return (
            f'<g class="obj" onclick="{onclick}">'
            f'<path class="sym" d="M{x-w/2},{y-h/2} L{x},{y} L{x-w/2},{y+h/2} Z '
            f'M{x+w/2},{y-h/2} L{x},{y} L{x+w/2},{y+h/2} Z"/>'
            f'<text class="smalltag" x="{x}" y="{y+25}" text-anchor="middle">{tag}</text></g>'
        )

    if master.key == "valve.check_valve":
        return (
            f'<g class="obj" onclick="{onclick}">'
            f'<path class="sym" d="M{x-15},{y-10} L{x+5},{y} L{x-15},{y+10} Z"/>'
            f'<line class="sym" x1="{x+8}" y1="{y-12}" x2="{x+8}" y2="{y+12}"/>'
            f'<text class="smalltag" x="{x}" y="{y+25}" text-anchor="middle">{tag}</text></g>'
        )

    if master.key == "valve.control_valve":
        return (
            f'<g class="obj" onclick="{onclick}">'
            f'<path class="sym" d="M{x-16},{y+8} L{x},{y+18} L{x-16},{y+28} Z '
            f'M{x+16},{y+8} L{x},{y+18} L{x+16},{y+28} Z"/>'
            f'<line class="sym" x1="{x}" y1="{y+8}" x2="{x}" y2="{y}"/>'
            f'<path class="sym" d="M{x-12},{y} Q{x},{y-12} {x+12},{y} Z"/>'
            f'<text class="smalltag" x="{x}" y="{y+42}" text-anchor="middle">{tag}</text></g>'
        )

    if master.key == "valve.relief_valve":
        return (
            f'<g class="obj" onclick="{onclick}">'
            f'<path class="sym" d="M{x-12},{y+12} L{x+12},{y+12} L{x},{y-8} Z"/>'
            f'<line class="sym" x1="{x}" y1="{y-8}" x2="{x}" y2="{y-22}"/>'
            f'<path class="sym" d="M{x-8},{y-22} H{x+8}"/>'
            f'<text class="smalltag" x="{x+28}" y="{y+4}">{tag}</text></g>'
        )

    if master.key == "instrument.flow_transmitter_inline":
        return (
            f'<g class="obj" onclick="{onclick}"><circle class="inst" cx="{x}" cy="{y}" r="14"/>'
            f'<text class="insttext" x="{x}" y="{y+3}" text-anchor="middle">{_instrument_code(tag)}</text>'
            f'<text class="smalltag" x="{x}" y="{y+28}" text-anchor="middle">{tag}</text></g>'
        )

    if master.key == "instrument.bubble":
        return (
            f'<g class="obj" onclick="{onclick}"><circle class="inst" cx="{x}" cy="{y}" r="14"/>'
            f'<text class="insttext" x="{x}" y="{y+3}" text-anchor="middle">{_instrument_code(tag)}</text>'
            f'<text class="smalltag" x="{x}" y="{y+27}" text-anchor="middle">{tag}</text></g>'
        )

    if master.key == "junction.branch":
        return f'<g class="obj" onclick="{onclick}"><circle cx="{x}" cy="{y}" r="2.8" fill="#000"/></g>'

    if master.key == "junction.boundary":
        return (
            f'<g class="obj" onclick="{onclick}">'
            f'<path class="sym" d="M{x-15},{y-7} H{x+7} L{x+15},{y} L{x+7},{y+7} H{x-15} Z"/>'
            f'<text class="smalltag" x="{x}" y="{y+22}" text-anchor="middle">{tag}</text></g>'
        )

    raise KeyError(master.key)


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
        + f'<text class="title2" x="{w-375}" y="{title_y+45}">SEPARATOR & PUMP CONFIGURATION</text>'
        + f'<text class="title2" x="{w-375}" y="{title_y+64}">PROJECT: {html.escape(project_id)}</text>'
        + f'<text class="smalltag" x="{w-230}" y="{title_y+24}">DRAWING: PID-DEMO-001</text>'
        + f'<text class="smalltag" x="{w-230}" y="{title_y+43}">REV: A</text>'
        + f'<text class="smalltag" x="{w-230}" y="{title_y+62}">STATUS: DEVELOPMENT</text>'
    )


def render_pid_html(model: PlantModel) -> str:
    object_data = {obj.id: obj.model_dump(mode="json") for obj in model.objects}
    payload = json.dumps(object_data).replace("</", "<\\/")
    symbols = "".join(_symbol_svg(obj, *VIEW_POSITIONS[obj.id]) for obj in model.objects)

    routes = [
        ("process", "M246 385 H403"), ("process", "M437 448 H518"),
        ("process", "M552 430 H631"), ("process", "M694 430 H752"),
        ("process", "M758 430 H833"), ("process", "M867 430 H923"),
        ("process", "M957 430 H1040"),
        ("process", "M755 427 V290"), ("process", "M741 275 H574"),
        ("process", "M536 293 H335 V253 H246"),
        ("process", "M235 215 V182"), ("process", "M235 138 V110"),
        ("process", "M174 215 H167"), ("process", "M133 160 H97"),
        ("process", "M210 385 V514"), ("process", "M210 536 V572"),
        ("signal", "M310 271 L420 234"), ("signal", "M420 234 V408"),
        ("signal", "M755 258 L875 219"), ("signal", "M875 219 L555 258"),
        ("assoc", "M119 245 H174"), ("assoc", "M119 300 H174"),
        ("assoc", "M296 285 H246"), ("assoc", "M296 335 H246"),
        ("assoc", "M610 374 V404"), ("assoc", "M700 374 V404"),
    ]
    route_svg = "".join(f'<path class="{kind}" d="{d}"/>' for kind, d in routes)

    annotations = """
    <text class="linetag" x="315" y="416">L-V101-LIQ</text>
    <text class="linetag" x="790" y="417">L-P101-DIS</text>
    <text class="linetag" x="650" y="263">L-P101-REC</text>
    <text class="note" x="55" y="640">NOTES:</text>
    <text class="note" x="55" y="655">1. DEVELOPMENT VIEW - SYMBOL MASTERS AND DRAFTING PROFILE UNDER QUALIFICATION.</text>
    <text class="note" x="55" y="670">2. ENGINEERING OBJECTS AND CONNECTIVITY ARE CONTROLLED BY THE CANONICAL PLANT MODEL.</text>
    """

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP Engineering P&ID</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#e5e7eb;color:#111}}
header{{padding:12px 18px;background:#fff;border-bottom:1px solid #aaa}}
main{{display:grid;grid-template-columns:minmax(900px,1fr) 300px;gap:12px;padding:12px}}
.viewer{{background:#fff;border:1px solid #999;overflow:auto}} .side{{background:#fff;border:1px solid #aaa;padding:14px}}
svg{{width:100%;min-width:1180px;height:auto;background:#fff}}
.border{{fill:none;stroke:#000;stroke-width:1.2}} .thin{{stroke:#000;stroke-width:.7}}
.sym{{fill:none;stroke:#000;stroke-width:1.5;stroke-linejoin:miter;stroke-linecap:square}}
.nozzle{{stroke:#000;stroke-width:1.5}} .inst{{fill:#fff;stroke:#000;stroke-width:1.3}}
.process{{fill:none;stroke:#000;stroke-width:1.5;stroke-linecap:square;stroke-linejoin:miter}}
.signal{{fill:none;stroke:#000;stroke-width:1.0;stroke-dasharray:7 4}}
.assoc{{fill:none;stroke:#000;stroke-width:.8;stroke-dasharray:2 3}}
.tag{{font:700 11px Arial}} .smalltag{{font:8px Arial}} .insttext{{font:700 8px Arial}}
.linetag{{font:8px Arial}} .note{{font:7px Arial}} .gridtxt{{font:7px Arial}}
.title{{font:700 10px Arial}} .title2{{font:8px Arial}} .obj{{cursor:pointer}}
.obj:hover .sym,.obj:hover .inst,.obj:hover .nozzle{{stroke:#555;stroke-width:2}}
.muted{{font-size:11px;color:#666}} .row{{padding:6px 0;border-bottom:1px solid #ddd;font-size:11px}}
.section{{font-size:10px;font-weight:700;margin-top:14px;text-transform:uppercase}}
</style>
</head>
<body>
<header><strong>Digital BDEP — Engineering Drawing Baseline</strong><span class="muted"> · MVP 0.3B</span></header>
<main>
<section class="viewer"><svg viewBox="0 0 1180 760">
{_sheet_frame(model.project_id)}
{route_svg}
{symbols}
{annotations}
</svg></section>
<aside class="side">
<h3 id="tag">V-101</h3><div id="kind" class="muted"></div>
<div class="section">Engineering object</div><div id="details"></div>
<div class="section">Ports</div><div id="ports"></div>
<div class="section">Drafting profile</div>
<div class="row">Monochrome engineering sheet</div>
<div class="row">Symbol registry driven</div>
<div class="row">Orthogonal routing baseline</div>
<div class="row">Border / grid / title block reserved</div>
</aside>
</main>
<script>
const objects={payload};
function selectObject(id){{
 const o=objects[id];
 document.getElementById('tag').textContent=o.tag;
 document.getElementById('kind').textContent=o.category+' · '+(o.equipment_type||o.valve_type||o.instrument_type||o.junction_type||'');
 document.getElementById('details').innerHTML='<div class="row"><b>ID:</b> '+o.id+'</div><div class="row"><b>Service:</b> '+(o.service||'—')+'</div>';
 document.getElementById('ports').innerHTML=(o.ports||[]).map(p=>'<div class="row"><b>'+p.name+'</b> · '+p.kind+' / '+p.direction+'</div>').join('')||'<div class="row">Semantic association only</div>';
}}
selectObject('EQ-V101');
</script>
</body></html>"""
