from __future__ import annotations

import html
import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .configurations import demo_vessel_pump_model

app = FastAPI(title="Digital BDEP Prototype", version="0.1.0")


@app.get("/api/plant")
def plant_model():
    return demo_vessel_pump_model().model_dump(mode="json")


@app.get("/", response_class=HTMLResponse)
def viewer():
    model = demo_vessel_pump_model()
    equipment = {item.id: item.model_dump(mode="json") for item in model.equipment}
    data = json.dumps(equipment).replace("</", "<\\/")
    project = html.escape(model.project_id)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP Viewer</title>
<style>
body{{margin:0;font-family:Arial,sans-serif;background:#f5f7fa;color:#172033}}
header{{padding:18px 28px;background:#fff;border-bottom:1px solid #dfe5ec}}
main{{display:grid;grid-template-columns:minmax(650px,1fr) 340px;gap:18px;padding:18px}}
.card{{background:#fff;border:1px solid #dfe5ec;border-radius:14px}}
.toolbar{{padding:12px 16px;border-bottom:1px solid #edf0f4}}
.canvas{{padding:18px;overflow:auto}}
svg{{width:100%;min-width:720px;height:510px;background:#fbfcfe;border:1px solid #edf0f4;border-radius:10px}}
.eq{{cursor:pointer}} .tag{{font-weight:700;font-size:17px;fill:#172033}}
.service{{font-size:12px;fill:#64748b}} .pipe{{stroke:#28384f;stroke-width:4;fill:none}}
.side{{padding:18px}} .kv{{display:grid;grid-template-columns:130px 1fr;gap:8px;padding:9px 0;border-bottom:1px solid #edf0f4;font-size:13px}}
.muted{{color:#6b7788;font-size:12px}} .section{{margin-top:18px;font-size:12px;text-transform:uppercase;color:#7a8798;font-weight:700}}
.port-row{{font-size:12px;padding:7px 0;border-bottom:1px dashed #edf0f4}}
</style></head>
<body>
<header><strong style="font-size:20px">Digital BDEP — Plant Model Viewer</strong><div class="muted">{project} · Python MVP 0.1 · plant graph valid</div></header>
<main>
<section class="card"><div class="toolbar"><strong>PID Concept View</strong> · <span class="muted">click equipment to inspect the plant object</span></div>
<div class="canvas"><svg viewBox="0 0 1000 510">
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#28384f"/></marker></defs>
<text x="52" y="55" font-size="13" fill="#7a8798">PROCESS FLOW →</text>
<g class="eq" onclick="selectEquipment('EQ-000001')">
<rect x="220" y="120" width="150" height="235" rx="72" fill="#eef5ff" stroke="#315f8c" stroke-width="3"/>
<line x1="295" y1="355" x2="295" y2="390" stroke="#315f8c" stroke-width="3"/>
<text class="tag" x="295" y="222" text-anchor="middle">V-101</text>
<text class="service" x="295" y="244" text-anchor="middle">Feed Separator</text></g>
<path class="pipe" d="M295 390 V430 H610 V300" marker-end="url(#arrow)"/>
<text x="448" y="420" text-anchor="middle" font-size="12" fill="#58677a">CONN-000001 · Separator liquid</text>
<g class="eq" onclick="selectEquipment('EQ-000002')">
<circle cx="665" cy="275" r="64" fill="#f1f8f4" stroke="#39735a" stroke-width="3"/>
<path d="M625 275 L695 240 L695 310 Z" fill="none" stroke="#39735a" stroke-width="3"/>
<text class="tag" x="665" y="370" text-anchor="middle">P-101</text>
<text class="service" x="665" y="390" text-anchor="middle">Separator Bottoms Pump</text></g>
<path class="pipe" d="M729 275 H915" marker-end="url(#arrow)"/>
</svg></div></section>
<aside class="card side"><h3 id="sel-tag">V-101</h3><div class="muted" id="sel-type"></div>
<div class="section">Engineering object</div><div id="details"></div>
<div class="section">Ports</div><div id="ports"></div>
<div class="section">Important</div><p class="muted">Coordinates belong to this drawing view only. Engineering connectivity remains in the canonical Python plant model.</p>
</aside></main>
<script>
const equipment = {data};
function selectEquipment(id){{
 const e=equipment[id];
 document.getElementById("sel-tag").textContent=e.tag;
 document.getElementById("sel-type").textContent=e.equipment_type;
 const values=[["Permanent ID",e.id],["Service",e.service||"—"],["Status",e.properties.status||"—"]];
 document.getElementById("details").innerHTML=values.map(([k,v])=>'<div class="kv"><span>'+k+'</span><strong>'+v+'</strong></div>').join("");
 document.getElementById("ports").innerHTML=e.ports.map(p=>'<div class="port-row"><strong>'+p.name+'</strong><br><span class="muted">'+p.kind+' · '+p.direction+'</span></div>').join("");
}}
selectEquipment("EQ-000001");
</script></body></html>"""
