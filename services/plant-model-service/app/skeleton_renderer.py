from __future__ import annotations

import html

from .drafter import DrafterPlan
from .models import PlantModel


def _polyline(route) -> str:
    points = " ".join(f"{p.x},{p.y}" for p in route.points)
    edge_ids = ",".join(route.semantic_edge_ids)
    return (
        f'<polyline class="pipe" points="{points}" '
        f'data-semantic-edge-ids="{html.escape(edge_ids)}" '
        f'data-route-role="{html.escape(route.role)}"/>'
    )


def render_drafter_skeleton_html(model: PlantModel, plan: DrafterPlan) -> str:
    p = plan.objects

    status_rows = "".join(
        f'<div class="issue {issue.severity.lower()}"><b>{issue.severity}</b> · {html.escape(issue.message)}</div>'
        for issue in plan.issues
    ) or '<div class="issue green"><b>GREEN</b> · Skeleton routing checks passed.</div>'

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP Drafter Skeleton</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#e7e9ec;color:#111}}
header{{background:#fff;border-bottom:1px solid #aaa;padding:11px 16px;display:flex;justify-content:space-between}}
header a{{margin-left:14px;color:#174a77;text-decoration:none;font-size:12px}}
main{{display:grid;grid-template-columns:minmax(880px,1fr) 290px;gap:12px;padding:12px}}
.sheet{{background:#fff;border:1px solid #777;overflow:auto}}
.side{{background:#fff;border:1px solid #aaa;padding:14px}}
svg{{width:100%;min-width:1120px;height:auto;background:#fff}}
.border{{fill:none;stroke:#000;stroke-width:1.1}}
.pipe{{fill:none;stroke:#000;stroke-width:1.6;stroke-linecap:square;stroke-linejoin:miter}}
.sym{{fill:#fff;stroke:#000;stroke-width:1.5;stroke-linejoin:miter}}
.tag{{font:700 11px Arial}} .txt{{font:8px Arial}} .note{{font:7px Arial}}
.issue{{padding:7px 0;border-bottom:1px solid #ddd;font-size:11px}}
.green{{color:#166534}} .amber{{color:#92400e}} .red{{color:#991b1b}}
.muted{{font-size:11px;color:#666}} .section{{font-size:10px;font-weight:700;text-transform:uppercase;margin-top:14px}}
.pass{{font-size:10px;padding:4px 0}}
</style>
</head>
<body>
<header>
<div><strong>Digital BDEP — Drafter Skeleton</strong><div class="muted">MVP 0.5A · process skeleton before instrumentation</div></div>
<nav><a href="/engineering">Engineering View</a><a href="/graph">Graph View</a></nav>
</header>
<main>
<section class="sheet">
<svg viewBox="0 0 1120 690">
<rect class="border" x="24" y="24" width="1072" height="642"/>
<line class="border" x1="24" y1="590" x2="1096" y2="590"/>

<!-- Routes are drawn first so symbols sit cleanly on top -->
{''.join(_polyline(route) for route in plan.routes)}

<!-- Separator -->
<path class="sym" d="M184 233 Q220 207 256 233 L256 367 Q220 393 184 367 Z"/>
<line class="sym" x1="220" y1="393" x2="220" y2="405"/>
<text x="220" y="304" text-anchor="middle" class="tag">V-101</text>

<!-- LCV -->
<g data-semantic-object-id="VLV-LCV101">
<path class="sym" d="M376 419 L395 430 L376 441 Z M414 419 L395 430 L414 441 Z"/>
<line class="sym" x1="395" y1="430" x2="395" y2="407"/>
<path class="sym" d="M383 407 Q395 390 407 407"/>
<line class="sym" x1="383" y1="407" x2="407" y2="407"/>
<text x="395" y="458" text-anchor="middle" class="txt">LCV-101</text>
</g>

<!-- suction XV -->
<g data-semantic-object-id="VLV-XV101">
<path class="sym" d="M518 419 L535 430 L518 441 Z M552 419 L535 430 L552 441 Z"/>
<text x="535" y="458" text-anchor="middle" class="txt">XV-101</text>
</g>

<!-- Pump -->
<g data-semantic-object-id="EQ-P101">
<circle class="sym" cx="690" cy="430" r="26"/>
<path class="sym" d="M668 430 C688 408 712 412 716 430 C700 433 692 442 684 450"/>
<text x="690" y="474" text-anchor="middle" class="tag">P-101</text>
</g>

<!-- discharge branch -->
<circle cx="785" cy="430" r="3" fill="#000"/>

<!-- NRV -->
<g data-semantic-object-id="VLV-NRV101">
<path class="sym" d="M848 420 L872 430 L848 440 Z"/>
<line class="sym" x1="875" y1="418" x2="875" y2="442"/>
<text x="863" y="458" text-anchor="middle" class="txt">NRV-101</text>
</g>

<!-- discharge XV -->
<g data-semantic-object-id="VLV-XV102">
<path class="sym" d="M938 419 L955 430 L938 441 Z M972 419 L955 430 L972 441 Z"/>
<text x="955" y="458" text-anchor="middle" class="txt">XV-102</text>
</g>

<!-- product boundary -->
<path class="sym" d="M1046 423 H1066 L1076 430 L1066 437 H1046 Z"/>
<text x="1060" y="458" text-anchor="middle" class="txt">TO PROCESS</text>

<!-- recycle FCV -->
<g data-semantic-object-id="VLV-FCV101">
<path class="sym" d="M501 244 L520 255 L501 266 Z M539 244 L520 255 L539 266 Z"/>
<line class="sym" x1="520" y1="255" x2="520" y2="232"/>
<path class="sym" d="M508 232 Q520 215 532 232"/>
<line class="sym" x1="508" y1="232" x2="532" y2="232"/>
<text x="520" y="284" text-anchor="middle" class="txt">FCV-101</text>
</g>

<!-- line identifiers -->
<text x="282" y="418" class="txt">L-V101-LIQ</text>
<text x="738" y="418" class="txt">L-P101-DIS</text>
<text x="590" y="244" class="txt">L-P101-REC</text>

<!-- explanatory labels -->
<text x="52" y="80" class="txt">PROCESS SKELETON: PRIMARY FLOW IS PROTECTED BEFORE INSTRUMENTATION IS ADDED</text>
<text x="52" y="615" class="note">MVP 0.5A: equipment placement → nozzle orientation → primary piping → recycle corridor → inline components → cleanup.</text>
<text x="790" y="620" class="tag">PID-DEMO-001-SKELETON</text>
<text x="790" y="640" class="txt">STATUS: {plan.status}</text>
</svg>
</section>
<aside class="side">
<h3>Drafting passes</h3>
{''.join(f'<div class="pass">✓ {html.escape(item.value.replace("_"," ").title())}</div>' for item in plan.passes_completed)}
<div class="section">Quality gate</div>
{status_rows}
<div class="section">What is intentionally hidden</div>
<div class="issue">PT / PI / LT / LI / LIC / FIC and signal routing are deferred to MVP 0.5B.</div>
<div class="issue">Semantic nozzle nodes remain in the digital thread but are not shown as graph circles here.</div>
</aside>
</main>
</body></html>"""
