from __future__ import annotations

import html
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .configurations import demo_pump_installation_model

app = FastAPI(title="Digital BDEP Prototype", version="0.2.0")


@app.get("/api/plant")
def plant_model():
    return demo_pump_installation_model().model_dump(mode="json")


def drawing_view(model):
    # Layout is deliberately separate from the canonical engineering model.
    positions = {
        "EQ-V101": (120, 245),
        "VLV-XV101": (320, 355),
        "EQ-P101": (450, 355),
        "JUNC-P101-DIS": (575, 355),
        "VLV-NRV101": (690, 355),
        "VLV-XV102": (795, 355),
        "BOUND-PRODUCT": (930, 355),
        "INS-FT101": (575, 185),
        "INS-FIC101": (720, 95),
        "VLV-FCV101": (390, 185),
        "INS-PI101S": (405, 285),
        "INS-PI101D": (515, 285),
    }
    return {obj.id: positions[obj.id] for obj in model.objects}


@app.get("/", response_class=HTMLResponse)
def viewer():
    model = demo_pump_installation_model()
    objects = {obj.id: obj.model_dump(mode="json") for obj in model.objects}
    layout = drawing_view(model)
    payload = json.dumps(objects).replace("</", "<\\/")
    project = html.escape(model.project_id)

    def symbol(obj, x, y):
        oid = html.escape(obj.id)
        tag = html.escape(obj.tag)
        click = f"selectObject('{oid}')"
        if obj.category == "equipment" and obj.equipment_type.value == "vertical_separator":
            return f'<g class="obj" onclick="{click}"><rect x="{x-48}" y="{y-120}" width="96" height="220" rx="45" class="equip"/><text x="{x}" y="{y}" class="tag" text-anchor="middle">{tag}</text></g>'
        if obj.category == "equipment":
            return f'<g class="obj" onclick="{click}"><circle cx="{x}" cy="{y}" r="38" class="equip"/><path d="M{x-25} {y} L{x+20} {y-22} L{x+20} {y+22} Z" class="symbol-line"/><text x="{x}" y="{y+62}" class="tag" text-anchor="middle">{tag}</text></g>'
        if obj.category == "valve":
            if obj.valve_type.value == "check_valve":
                shape = f'<path d="M{x-24} {y-18} L{x+8} {y} L{x-24} {y+18} Z M{x+11} {y-20} V{y+20}" class="symbol-line"/>'
            else:
                shape = f'<path d="M{x-24} {y-18} L{x} {y} L{x-24} {y+18} Z M{x+24} {y-18} L{x} {y} L{x+24} {y+18} Z" class="symbol-line"/>'
            return f'<g class="obj" onclick="{click}">{shape}<text x="{x}" y="{y+44}" class="smalltag" text-anchor="middle">{tag}</text></g>'
        if obj.category == "instrument":
            return f'<g class="obj" onclick="{click}"><circle cx="{x}" cy="{y}" r="25" class="instrument"/><text x="{x}" y="{y+4}" class="insttag" text-anchor="middle">{tag.split("-")[0]}</text><text x="{x}" y="{y+42}" class="smalltag" text-anchor="middle">{tag}</text></g>'
        return f'<g class="obj" onclick="{click}"><circle cx="{x}" cy="{y}" r="7" fill="#111"/><text x="{x}" y="{y+28}" class="smalltag" text-anchor="middle">{tag}</text></g>'

    symbols = "".join(symbol(obj, *layout[obj.id]) for obj in model.objects)

    routes = [
        ("process", "M168 345 H296"), ("process", "M344 355 H412"),
        ("process", "M488 355 H568"), ("process", "M582 355 H666"),
        ("process", "M714 355 H771"), ("process", "M819 355 H923"),
        ("process", "M575 348 V210"), ("process", "M550 185 H414"),
        ("process", "M366 185 H168 V270"),
        ("signal", "M600 168 L700 112"), ("signal", "M700 112 L414 168"),
        ("assoc", "M405 310 V333"), ("assoc", "M515 310 V333"),
    ]
    route_svg = "".join(f'<path class="{kind}" d="{d}"/>' for kind, d in routes)

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP Pump Module</title>
<style>
body{{margin:0;font-family:Arial,sans-serif;background:#f3f4f6;color:#111827}}
header{{padding:16px 24px;background:white;border-bottom:1px solid #d1d5db}}
main{{display:grid;grid-template-columns:minmax(760px,1fr) 330px;gap:16px;padding:16px}}
.card{{background:white;border:1px solid #d1d5db;border-radius:10px;overflow:hidden}}
.toolbar{{padding:10px 14px;border-bottom:1px solid #e5e7eb;font-size:13px}}
.canvas{{padding:10px;overflow:auto}}
svg{{width:100%;min-width:980px;height:500px;background:white}}
.process{{stroke:#111827;stroke-width:2.5;fill:none}} .signal{{stroke:#2563eb;stroke-width:1.8;fill:none;stroke-dasharray:8 5}}
.assoc{{stroke:#6b7280;stroke-width:1.5;fill:none;stroke-dasharray:3 4}}
.equip{{fill:white;stroke:#111827;stroke-width:2.2}} .symbol-line{{fill:white;stroke:#111827;stroke-width:2.2}}
.instrument{{fill:white;stroke:#111827;stroke-width:1.8}} .obj{{cursor:pointer}} .obj:hover *{{stroke:#b45309}}
.tag{{font-weight:700;font-size:14px}} .smalltag{{font-size:11px}} .insttag{{font-size:9px;font-weight:700}}
.muted{{color:#6b7280;font-size:12px}} .side{{padding:16px}} .kv{{display:grid;grid-template-columns:105px 1fr;gap:8px;padding:7px 0;border-bottom:1px solid #eee;font-size:12px}}
.section{{margin-top:16px;margin-bottom:6px;font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase}}
.port{{font-size:11px;padding:5px 0;border-bottom:1px dashed #e5e7eb}}
.badge{{display:inline-block;padding:3px 7px;border:1px solid #d1d5db;border-radius:999px;font-size:11px;margin-right:5px}}
</style></head><body>
<header><strong>Digital BDEP — Pump Installation Module</strong><div class="muted">{project} · Python MVP 0.2 · module-generated engineering graph</div></header>
<main><section class="card"><div class="toolbar"><span class="badge">PROCESS</span><span class="badge">SIGNAL</span> Click any object to inspect its canonical plant data.</div>
<div class="canvas"><svg viewBox="0 0 1040 500">
<text x="35" y="35" font-size="12" fill="#6b7280">STANDARD PUMP INSTALLATION WITH MINIMUM-FLOW RECYCLE</text>
{route_svg}{symbols}
<text x="610" y="388" font-size="11">Main discharge →</text>
<text x="470" y="155" font-size="11">Minimum-flow recycle</text>
</svg></div></section>
<aside class="card side"><h3 id="tag">Select object</h3><div id="kind" class="muted"></div><div class="section">Object data</div><div id="details"></div><div class="section">Ports</div><div id="ports"></div><div class="section">Architecture</div><p class="muted">Symbols and coordinates live only in the drawing view. Equipment, valves, instruments, connections and control signals live in the Python plant model.</p></aside></main>
<script>
const objects={payload};
function selectObject(id){{const o=objects[id];document.getElementById('tag').textContent=o.tag;document.getElementById('kind').textContent=o.category+' · '+(o.equipment_type||o.valve_type||o.instrument_type||o.junction_type||'');const rows=[['Permanent ID',o.id],['Service',o.service||'—'],['Status',(o.properties||{{}}).status||'—']];document.getElementById('details').innerHTML=rows.map(r=>'<div class="kv"><span>'+r[0]+'</span><strong>'+r[1]+'</strong></div>').join('');document.getElementById('ports').innerHTML=(o.ports||[]).map(p=>'<div class="port"><strong>'+p.name+'</strong> · '+p.kind+' / '+p.direction+'</div>').join('')||'<div class="muted">No direct ports; semantic association only.</div>';}}
selectObject('EQ-P101');
</script></body></html>"""
