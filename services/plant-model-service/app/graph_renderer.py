from __future__ import annotations

import html
import json
from collections import defaultdict

from .models import PlantModel


def _layout(model: PlantModel) -> dict[str, tuple[int, int]]:
    groups = defaultdict(list)
    for obj in model.objects:
        groups[obj.category].append(obj)

    columns = {
        "equipment": 110,
        "nozzle": 310,
        "valve": 510,
        "instrument": 710,
        "junction": 910,
    }

    positions: dict[str, tuple[int, int]] = {}
    for category, items in groups.items():
        x = columns.get(category, 1050)
        for i, obj in enumerate(sorted(items, key=lambda item: item.tag)):
            positions[obj.id] = (x, 85 + i * 58)
    return positions


def render_graph_html(model: PlantModel) -> str:
    positions = _layout(model)
    objects = {obj.id: obj.model_dump(mode="json") for obj in model.objects}
    payload = json.dumps(objects).replace("</", "<\\/")

    edge_svg = []
    for connection in model.connections:
        sx, sy = positions[connection.source.object_id]
        tx, ty = positions[connection.target.object_id]
        css = "signal-edge" if connection.kind.value == "signal" else "edge"
        edge_svg.append(
            f'<path class="{css}" d="M{sx+55},{sy} C{sx+110},{sy} {tx-110},{ty} {tx-55},{ty}" '
            f'data-semantic-edge-id="{html.escape(connection.id)}"/>'
        )

    for association in model.associations:
        sx, sy = positions[association.subject_id]
        tx, ty = positions[association.target_id]
        edge_svg.append(
            f'<path class="assoc-edge" d="M{sx+55},{sy} C{sx+110},{sy} {tx-110},{ty} {tx-55},{ty}" '
            f'data-semantic-edge-id="{html.escape(association.id)}"/>'
        )

    node_svg = []
    for obj in model.objects:
        x, y = positions[obj.id]
        label = html.escape(obj.tag)
        category = html.escape(obj.category)
        node_svg.append(
            f'<g class="node {category}" onclick="selectObject(\'{html.escape(obj.id)}\')" '
            f'data-semantic-object-id="{html.escape(obj.id)}">'
            f'<rect x="{x-55}" y="{y-18}" width="110" height="36" rx="5"/>'
            f'<text x="{x}" y="{y-2}" text-anchor="middle" class="node-tag">{label}</text>'
            f'<text x="{x}" y="{y+11}" text-anchor="middle" class="node-type">{category}</text>'
            f'</g>'
        )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP Graph View</title>
<style>
body{{margin:0;font-family:Arial,sans-serif;background:#f4f5f7;color:#111827}}
header{{background:white;border-bottom:1px solid #d1d5db;padding:12px 18px;display:flex;justify-content:space-between;align-items:center}}
nav a{{margin-left:12px;color:#1f4f7a;text-decoration:none;font-size:13px}}
main{{display:grid;grid-template-columns:minmax(900px,1fr) 300px;gap:12px;padding:12px}}
.canvas{{background:white;border:1px solid #c8cdd3;overflow:auto}}
.side{{background:white;border:1px solid #c8cdd3;padding:14px}}
svg{{width:100%;min-width:1100px;min-height:780px}}
.edge{{fill:none;stroke:#4b5563;stroke-width:1.2}}
.signal-edge{{fill:none;stroke:#2563eb;stroke-width:1.2;stroke-dasharray:6 4}}
.assoc-edge{{fill:none;stroke:#9ca3af;stroke-width:1;stroke-dasharray:2 3}}
.node rect{{fill:white;stroke:#111827;stroke-width:1.2}}
.node.equipment rect{{stroke-width:2}}
.node.nozzle rect{{stroke-dasharray:4 2}}
.node-tag{{font:700 10px Arial}} .node-type{{font:8px Arial;fill:#6b7280}}
.node{{cursor:pointer}} .node:hover rect{{stroke:#b45309;stroke-width:2}}
.row{{padding:6px 0;border-bottom:1px solid #e5e7eb;font-size:11px}}
.section{{font-size:10px;font-weight:700;text-transform:uppercase;margin-top:14px;color:#6b7280}}
.muted{{font-size:11px;color:#6b7280}}
</style>
</head>
<body>
<header>
<div><strong>Digital BDEP — Graph View</strong><div class="muted">Semantic nodes, edges and digital thread</div></div>
<nav><a href="/engineering">Engineering View</a><a href="/graph"><strong>Graph View</strong></a></nav>
</header>
<main>
<section class="canvas"><svg viewBox="0 0 1100 780">
{''.join(edge_svg)}
{''.join(node_svg)}
</svg></section>
<aside class="side">
<h3 id="tag">Select a node</h3><div id="kind" class="muted"></div>
<div class="section">Semantic object</div><div id="details"></div>
<div class="section">Relationships</div><div id="neighbors"></div>
</aside>
</main>
<script>
const objects={payload};
const adjacency={json.dumps({k: sorted(v) for k,v in model.adjacency().items()})};
function selectObject(id){{
 const o=objects[id];
 document.getElementById('tag').textContent=o.tag;
 document.getElementById('kind').textContent=o.category+' · '+(o.equipment_type||o.valve_type||o.instrument_type||o.junction_type||o.nozzle_type||'');
 document.getElementById('details').innerHTML='<div class="row"><b>ID:</b> '+o.id+'</div><div class="row"><b>Service:</b> '+(o.service||'—')+'</div>';
 document.getElementById('neighbors').innerHTML=(adjacency[id]||[]).map(n=>'<div class="row">'+n+'</div>').join('')||'<div class="row">No relationships</div>';
}}
selectObject('EQ-V101');
</script>
</body></html>"""
