from __future__ import annotations

import html

from .config_matcher import ConfigurationMatch
from .simulation import SimulationPublication


def render_configuration_match_html(
    publication: SimulationPublication,
    match: ConfigurationMatch,
) -> str:
    by_id = {item.id: item for item in publication.equipment}
    vessel = by_id.get(match.node_mapping.get("upstream_vessel", ""))
    pump = by_id.get(match.node_mapping.get("downstream_pump", ""))
    matched_stream_id = match.stream_mapping.get("edge_0")
    matched_stream = next(
        (stream for stream in publication.streams if stream.id == matched_stream_id),
        None,
    )

    status_class = {
        "exact": "green",
        "known_variant": "amber",
        "unknown": "red",
    }[match.status.value]

    modules = "".join(
        f'<div class="module">{html.escape(module)}</div>'
        for module in match.engineering_modules
    ) or '<div class="empty">No engineering modules released for compilation.</div>'

    checks = "".join(
        (
            f'<div class="check {"pass" if check.passed else "fail"}">'
            f'<b>{html.escape(check.rule)}</b>'
            f'<span>{"PASS" if check.passed else "REVIEW"}</span>'
            f'<small>actual={html.escape(str(check.actual))} · '
            f'expected={html.escape(str(check.expected))}</small></div>'
        )
        for check in match.applicability
    ) or '<div class="empty">No applicability rules.</div>'

    stream_label = matched_stream.simulator_stream_id if matched_stream else "—"
    stream_number = matched_stream.stream_number if matched_stream else "—"
    phase = matched_stream.phase if matched_stream else "—"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP Configuration Matcher</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#e7e9ec;color:#111}}
header{{background:#fff;border-bottom:1px solid #aaa;padding:12px 16px;display:flex;justify-content:space-between}}
header a{{font-size:12px;color:#174a77;text-decoration:none;margin-left:14px}}
main{{display:grid;grid-template-columns:minmax(720px,1fr) 390px;gap:12px;padding:12px}}
.panel{{background:#fff;border:1px solid #888}}
.side{{background:#fff;border:1px solid #aaa;padding:16px}}
svg{{width:100%;height:auto;background:#fff}}
.eq{{fill:#fff;stroke:#111;stroke-width:1.6}}
.pipe{{fill:none;stroke:#111;stroke-width:1.8}}
.tag{{font:700 14px Arial}} .txt{{font:10px Arial}} .small{{font:9px Arial;fill:#555}}
.badge{{display:inline-block;padding:6px 10px;border-radius:999px;font-size:11px;font-weight:700}}
.green{{background:#dcfce7;color:#166534}} .amber{{background:#fef3c7;color:#92400e}} .red{{background:#fee2e2;color:#991b1b}}
.section{{font-size:10px;font-weight:700;text-transform:uppercase;margin-top:16px;margin-bottom:6px}}
.module{{border:1px solid #d1d5db;border-radius:4px;padding:7px;margin:5px 0;font-size:10px}}
.check{{border:1px solid #ddd;border-radius:4px;padding:7px;margin:5px 0;display:grid;grid-template-columns:1fr auto;gap:4px;font-size:10px}}
.check small{{grid-column:1/3;color:#666}} .check.pass span{{color:#166534;font-weight:700}} .check.fail span{{color:#92400e;font-weight:700}}
.metric{{font-size:11px;padding:6px 0;border-bottom:1px solid #eee}} .muted{{font-size:11px;color:#666}}
.empty{{font-size:10px;color:#666;padding:8px 0}}
</style>
</head>
<body>
<header>
<div><strong>Digital BDEP — Process Configuration Matcher</strong>
<div class="muted">MVP 0.7 · simulation/PFD topology → approved configuration</div></div>
<nav><a href="/engineering">Engineering View</a><a href="/graph">Graph View</a></nav>
</header>
<main>
<section class="panel">
<svg viewBox="0 0 860 520">
<text x="40" y="48" class="tag">Simulation-derived PFD topology</text>
<text x="40" y="72" class="small">No PSV / LCV / instrumentation is used for matching.</text>

<!-- Feed boundary -->
<path class="pipe" d="M55 250 H170"/>
<polygon class="eq" points="55,242 78,242 88,250 78,258 55,258"/>
<text x="55" y="280" class="txt">1100 · S-100 FEED</text>

<!-- Vessel -->
<path class="eq" d="M170 170 Q215 145 260 170 L260 330 Q215 355 170 330 Z"/>
<text x="215" y="255" text-anchor="middle" class="tag">{html.escape(vessel.tag if vessel else "V-?")}</text>
<text x="215" y="372" text-anchor="middle" class="small">{html.escape(vessel.equipment_type if vessel else "")}</text>

<!-- Vapor -->
<path class="pipe" d="M215 158 V95 H335"/>
<text x="245" y="88" class="txt">1101 · S-101 vapor</text>

<!-- Liquid stream -->
<path class="pipe" d="M215 343 V420 H530"/>
<text x="315" y="407" class="txt">{html.escape(stream_number)} · {html.escape(stream_label)} · {html.escape(phase)}</text>

<!-- Pump -->
<circle class="eq" cx="585" cy="420" r="38"/>
<path class="eq" d="M552 420 C578 390 610 395 623 420 C602 424 590 437 579 449"/>
<text x="585" y="478" text-anchor="middle" class="tag">{html.escape(pump.tag if pump else "P-?")}</text>
<text x="585" y="497" text-anchor="middle" class="small">{html.escape(pump.equipment_type if pump else "")}</text>

<!-- Pump discharge -->
<path class="pipe" d="M623 420 H785"/>
<polygon class="eq" points="760,412 785,412 798,420 785,428 760,428"/>
<text x="685" y="407" class="txt">1103 · S-103</text>

<!-- Matcher boundary -->
<rect x="130" y="125" width="555" height="390" fill="none" stroke="#777" stroke-width="1" stroke-dasharray="6 5"/>
<text x="142" y="145" class="small">Topology matcher evaluates equipment types + directed stream connectivity + phase</text>
</svg>
</section>
<aside class="side">
<div class="badge {status_class}">{html.escape(match.status.value.upper().replace("_", " "))}</div>

<div class="section">Approved configuration</div>
<div class="metric"><b>ID:</b> {html.escape(match.configuration_id or "No match")}</div>
<div class="metric"><b>Version:</b> {html.escape(match.configuration_version or "—")}</div>
<div class="metric"><b>Case:</b> {html.escape(publication.design_case_id)}</div>
<div class="metric"><b>Simulation:</b> {html.escape(publication.simulation_case_id)}</div>

<div class="section">Why</div>
<div class="metric">{html.escape(match.reason)}</div>

<div class="section">Node mapping</div>
<div class="metric">upstream_vessel → {html.escape(match.node_mapping.get("upstream_vessel", "—"))}</div>
<div class="metric">downstream_pump → {html.escape(match.node_mapping.get("downstream_pump", "—"))}</div>
<div class="metric">connecting stream → {html.escape(stream_label)}</div>

<div class="section">Design Basis applicability</div>
{checks}

<div class="section">Modules permitted for MVP 0.8 compiler</div>
{modules}

<div class="section">Important rule</div>
<div class="metric">The matcher identifies an approved configuration. It does not yet instantiate P&ID valves, instruments or protection devices.</div>
</aside>
</main>
</body></html>"""
