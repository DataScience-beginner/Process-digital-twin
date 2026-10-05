from __future__ import annotations

import html

from .continuation import continuation_section


def render_continuation_pid_html() -> str:
    section = continuation_section()
    ref = section["incoming_reference"]
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(section["drawing_id"])} — {html.escape(section["title"])}</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#e7e9ec;color:#111}}
header{{background:#fff;border-bottom:1px solid #aaa;padding:11px 16px;display:flex;justify-content:space-between}}
header a{{font-size:11px;color:#174a77;text-decoration:none;margin-left:12px}}
main{{padding:12px}} .sheet{{background:#fff;border:1px solid #777;overflow:auto}}
svg{{width:100%;min-width:1120px;height:auto;background:#fff}}
.border{{fill:none;stroke:#000;stroke-width:1.1}} .pipe{{fill:none;stroke:#000;stroke-width:1.6;stroke-linejoin:miter}}
.signal{{fill:none;stroke:#000;stroke-width:1;stroke-dasharray:7 4}} .sym{{fill:#fff;stroke:#000;stroke-width:1.5}}
.inst{{fill:#fff;stroke:#000;stroke-width:1.2}} .tag{{font:700 11px Arial}} .txt{{font:8px Arial}} .itxt{{font:700 8px Arial}}
.note{{font-size:9px;color:#475569;background:#fffbeb;border:1px solid #fde68a;padding:8px;margin-top:8px}}
.click{{cursor:pointer}} .click:hover .sym,.click:hover .inst{{stroke:#1d4ed8;stroke-width:2.2}}
</style>
</head>
<body>
<header>
<div><strong>{html.escape(section["drawing_id"])} — {html.escape(section["title"])}</strong><div style="font-size:9px;color:#64748b">Approved demo continuation template · same semantic line continues from sheet 1</div></div>
<nav><a href="/engineering">PID-DEMO-001</a><a href="/summaries">Summaries</a><a href="/hazop">HAZOP</a></nav>
</header>
<main>
<section class="sheet">
<svg viewBox="0 0 1120 690">
<rect class="border" x="24" y="24" width="1072" height="642"/><line class="border" x1="24" y1="590" x2="1096" y2="590"/>

<!-- Incoming continuation: same semantic LINE-1103 -->
<path class="sym" d="M52 323 H82 L92 330 L82 337 H52 Z"/>
<text x="52" y="310" class="txt">FROM PID-DEMO-001</text>
<text x="52" y="350" class="txt">6&quot;-HC-1103-CS150</text>
<polyline class="pipe" points="92,330 180,330 214,330 315,330 430,330 510,330 596,330"/>

<!-- XV-201 -->
<g class="click">
<path class="sym" d="M180 319 L197 330 L180 341 Z M214 319 L197 330 L214 341 Z"/>
<text x="197" y="357" text-anchor="middle" class="txt">XV-201</text>
</g>

<!-- E-201 cooler -->
<g class="click">
<rect class="sym" x="315" y="295" width="115" height="70" rx="8"/>
<line class="sym" x1="325" y1="350" x2="420" y2="310"/>
<line class="sym" x1="325" y1="310" x2="420" y2="350"/>
<text x="372" y="388" text-anchor="middle" class="tag">E-201</text>
<text x="372" y="402" text-anchor="middle" class="txt">PRODUCT COOLER</text>
</g>

<!-- TI -->
<line class="sym" x1="495" y1="330" x2="495" y2="272"/>
<g class="click"><circle class="inst" cx="495" cy="258" r="14"/><text class="itxt" x="495" y="261" text-anchor="middle">TI</text><text class="txt" x="495" y="286" text-anchor="middle">TI-201</text></g>

<!-- V-201 -->
<g class="click">
<path class="sym" d="M596 233 Q640 205 684 233 L684 397 Q640 425 596 397 Z"/>
<text x="640" y="318" text-anchor="middle" class="tag">V-201</text>
</g>

<!-- level instruments and control -->
<line class="sym" x1="684" y1="305" x2="735" y2="305"/>
<g class="click"><circle class="inst" cx="750" cy="305" r="14"/><text class="itxt" x="750" y="308" text-anchor="middle">LT</text><text class="txt" x="750" y="332" text-anchor="middle">LT-201</text></g>
<g class="click"><circle class="inst" cx="850" cy="225" r="14"/><text class="itxt" x="850" y="228" text-anchor="middle">LIC</text><text class="txt" x="850" y="252" text-anchor="middle">LIC-201</text></g>
<polyline class="signal" points="764,305 790,305 790,225 836,225"/>
<polyline class="signal" points="850,239 850,445 760,445"/>

<!-- liquid product -->
<polyline class="pipe" points="640,412 640,445 741,445 779,445 960,445"/>
<g class="click">
<path class="sym" d="M741 434 L760 445 L741 456 Z M779 434 L760 445 L779 456 Z"/>
<line class="sym" x1="760" y1="445" x2="760" y2="422"/><path class="sym" d="M748 422 Q760 405 772 422"/><line class="sym" x1="748" y1="422" x2="772" y2="422"/>
<text x="760" y="475" text-anchor="middle" class="txt">LCV-201</text>
</g>
<path class="sym" d="M960 438 H982 L992 445 L982 452 H960 Z"/>
<text x="830" y="435" class="txt">4&quot;-HC-1201-CS150</text><text x="998" y="448" class="txt">TO PRODUCT</text>

<!-- vapor product -->
<polyline class="pipe" points="640,220 640,145 960,145"/>
<path class="sym" d="M960 138 H982 L992 145 L982 152 H960 Z"/>
<text x="715" y="135" class="txt">4&quot;-VG-1202-CS150</text><text x="998" y="148" class="txt">TO VAPOR SYSTEM</text>

<!-- title -->
<text x="50" y="615" class="txt">Continuation reference: {html.escape(ref["from_drawing"])} / {html.escape(ref["from_connector"])} → {html.escape(ref["to_drawing"])} / {html.escape(ref["to_connector"])}</text>
<text x="790" y="620" class="tag">{html.escape(section["drawing_id"])}</text>
<text x="790" y="640" class="txt">DOWNSTREAM CONDITIONING / PRODUCT SEPARATION</text>
</svg>
</section>
<div class="note">{html.escape(section["governance_note"])}</div>
</main>
</body></html>"""
