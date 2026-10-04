from __future__ import annotations

import html
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .configurations import demo_integrated_configuration_model

app = FastAPI(title="Digital BDEP Prototype", version="0.3.0")


@app.get("/api/plant")
def plant_model():
    return demo_integrated_configuration_model().model_dump(mode="json")


@app.get("/", response_class=HTMLResponse)
def viewer():
    model = demo_integrated_configuration_model()
    objects = {obj.id: obj.model_dump(mode="json") for obj in model.objects}
    payload = json.dumps(objects).replace("</", "<\\/")
    project = html.escape(model.project_id)

    # MVP 0.3 layout remains a view-only mapping. It is not part of the plant model.
    positions = {
        "EQ-V101": (210, 275), "INS-PT101": (105, 180), "INS-PI101": (105, 235),
        "INS-LT101": (315, 235), "INS-LI101": (315, 295), "INS-LIC101": (455, 150),
        "VLV-LCV101": (455, 390), "VLV-PSV101": (210, 90), "BOUND-RELIEF": (210, 35),
        "VLV-VENT101": (130, 90), "BOUND-VENT": (70, 90), "VLV-DRAIN101": (210, 485),
        "BOUND-DRAIN": (210, 535), "VLV-XV101": (565, 390), "EQ-P101": (690, 390),
        "JUNC-P101-DIS": (805, 390), "VLV-NRV101": (910, 390), "VLV-XV102": (1010, 390),
        "BOUND-PRODUCT": (1130, 390), "INS-FT101": (805, 235), "INS-FIC101": (930, 150),
        "VLV-FCV101": (610, 235), "INS-PI101S": (655, 325), "INS-PI101D": (735, 325),
    }

    def symbol(obj):
        x, y = positions[obj.id]
        oid, tag = html.escape(obj.id), html.escape(obj.tag)
        click = f"selectObject('{oid}')"
        if obj.category == "equipment" and obj.equipment_type.value == "vertical_separator":
            return f'<g class="obj" onclick="{click}"><rect x="{x-48}" y="{y-115}" width="96" height="220" rx="44" class="equip"/><text x="{x}" y="{y}" class="tag" text-anchor="middle">{tag}</text></g>'
        if obj.category == "equipment":
            return f'<g class="obj" onclick="{click}"><circle cx="{x}" cy="{y}" r="34" class="equip"/><path d="M{x-22} {y} L{x+18} {y-20} L{x+18} {y+20} Z" class="symbol-line"/><text x="{x}" y="{y+54}" class="tag" text-anchor="middle">{tag}</text></g>'
        if obj.category == "valve":
            if obj.valve_type.value == "check_valve":
                shape = f'<path d="M{x-20} {y-16} L{x+6} {y} L{x-20} {y+16} Z M{x+9} {y-18} V{y+18}" class="symbol-line"/>'
            elif obj.valve_type.value == "relief_valve":
                shape = f'<path d="M{x-18} {y+15} L{x+18} {y+15} L{x} {y-15} Z" class="symbol-line"/>'
            else:
                shape = f'<path d="M{x-20} {y-15} L{x} {y} L{x-20} {y+15} Z M{x+20} {y-15} L{x} {y} L{x+20} {y+15} Z" class="symbol-line"/>'
            return f'<g class="obj" onclick="{click}">{shape}<text x="{x}" y="{y+34}" class="smalltag" text-anchor="middle">{tag}</text></g>'
        if obj.category == "instrument":
            code = tag.split("-")[0]
            return f'<g class="obj" onclick="{click}"><circle cx="{x}" cy="{y}" r="22" class="instrument"/><text x="{x}" y="{y+4}" class="insttag" text-anchor="middle">{code}</text><text x="{x}" y="{y+36}" class="smalltag" text-anchor="middle">{tag}</text></g>'
        return f'<g class="obj" onclick="{click}"><circle cx="{x}" cy="{y}" r="5" fill="#111"/><text x="{x}" y="{y+24}" class="smalltag" text-anchor="middle">{tag}</text></g>'

    symbols = "".join(symbol(obj) for obj in model.objects)

    routes = [
        ("process", "M210 105 V68"), ("process", "M210 112 V130"),
        ("vent", "M162 160 V90 H150"), ("vent", "M110 90 H75"),
        ("drain", "M210 380 V469"), ("drain", "M210 501 V530"),
        ("process", "M258 380 V390 H435"), ("process", "M475 390 H545"),
        ("process", "M585 390 H656"), ("process", "M724 390 H800"),
        ("process", "M810 390 H890"), ("process", "M930 390 H990"), ("process", "M1030 390 H1125"),
        ("process", "M805 385 V255"), ("process", "M783 235 H630"), ("process", "M590 235 H340 V210 H258"),
        ("signal", "M337 235 L435 160"), ("signal", "M455 172 V365"),
        ("signal", "M827 220 L910 165"), ("signal", "M910 165 L630 220"),
        ("assoc", "M127 180 H160"), ("assoc", "M127 235 H160"),
        ("assoc", "M293 235 H260"), ("assoc", "M293 295 H260"),
        ("assoc", "M655 347 V365"), ("assoc", "M735 347 V365"),
    ]
    route_svg = "".join(f'<path class="{kind}" d="{d}"/>' for kind, d in routes)

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP MVP 0.3</title>
<style>
body{{margin:0;font-family:Arial,sans-serif;background:#f3f4f6;color:#111827}}
header{{padding:15px 22px;background:white;border-bottom:1px solid #d1d5db}}
main{{display:grid;grid-template-columns:minmax(850px,1fr) 330px;gap:14px;padding:14px}}
.card{{background:white;border:1px solid #d1d5db;border-radius:8px;overflow:hidden}} .toolbar{{padding:9px 13px;border-bottom:1px solid #e5e7eb;font-size:12px}}
.canvas{{padding:8px;overflow:auto}} svg{{width:100%;min-width:1200px;height:570px;background:white}}
.process{{stroke:#111827;stroke-width:2.3;fill:none}} .signal{{stroke:#2563eb;stroke-width:1.6;fill:none;stroke-dasharray:7 5}}
.assoc{{stroke:#6b7280;stroke-width:1.3;fill:none;stroke-dasharray:3 4}} .vent,.drain{{stroke:#111827;stroke-width:1.8;fill:none}}
.equip{{fill:white;stroke:#111827;stroke-width:2}} .symbol-line{{fill:white;stroke:#111827;stroke-width:2}}
.instrument{{fill:white;stroke:#111827;stroke-width:1.6}} .obj{{cursor:pointer}} .obj:hover *{{stroke:#b45309}}
.tag{{font-weight:700;font-size:13px}} .smalltag{{font-size:9px}} .insttag{{font-size:8px;font-weight:700}}
.muted{{color:#6b7280;font-size:11px}} .side{{padding:14px}} .kv{{display:grid;grid-template-columns:100px 1fr;gap:7px;padding:6px 0;border-bottom:1px solid #eee;font-size:11px}}
.section{{margin-top:14px;margin-bottom:5px;font-size:10px;font-weight:700;color:#6b7280;text-transform:uppercase}} .port{{font-size:10px;padding:4px 0;border-bottom:1px dashed #e5e7eb}}
.badge{{display:inline-block;padding:2px 6px;border:1px solid #d1d5db;border-radius:999px;font-size:10px;margin-right:4px}}
</style></head><body>
<header><strong>Digital BDEP — Integrated Vessel + Pump Configuration</strong><div class="muted">{project} · Python MVP 0.3 · 2 reusable engineering modules</div></header>
<main><section class="card"><div class="toolbar"><span class="badge">PROCESS</span><span class="badge">SIGNAL</span><span class="badge">ASSOCIATION</span> Vessel controls + relief + pump minimum-flow module.</div>
<div class="canvas"><svg viewBox="0 0 1200 570">
<text x="25" y="25" font-size="11" fill="#6b7280">V-101 SEPARATOR MODULE</text><text x="520" y="25" font-size="11" fill="#6b7280">P-101 PUMP MODULE</text>
{route_svg}{symbols}
<text x="315" y="412" font-size="10">Level-controlled liquid outlet</text>
<text x="700" y="205" font-size="10">Minimum-flow recycle</text>
</svg></div></section>
<aside class="card side"><h3 id="tag">V-101</h3><div id="kind" class="muted"></div><div class="section">Canonical object</div><div id="details"></div><div class="section">Ports</div><div id="ports"></div><div class="section">Current milestone</div><p class="muted">The vessel and pump are now reusable engineering modules. Drawing coordinates remain outside the plant model.</p></aside></main>
<script>
const objects={payload};
function selectObject(id){{const o=objects[id];document.getElementById('tag').textContent=o.tag;document.getElementById('kind').textContent=o.category+' · '+(o.equipment_type||o.valve_type||o.instrument_type||o.junction_type||'');const rows=[['Permanent ID',o.id],['Service',o.service||'—'],['Status',(o.properties||{{}}).status||'—']];document.getElementById('details').innerHTML=rows.map(r=>'<div class="kv"><span>'+r[0]+'</span><strong>'+r[1]+'</strong></div>').join('');document.getElementById('ports').innerHTML=(o.ports||[]).map(p=>'<div class="port"><strong>'+p.name+'</strong> · '+p.kind+' / '+p.direction+'</div>').join('')||'<div class="muted">Semantic association; no direct connection port.</div>';}}
selectObject('EQ-V101');
</script></body></html>"""
