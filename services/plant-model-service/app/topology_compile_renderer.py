from __future__ import annotations

import html

from .topology_compiler import CompilationResult


def render_compilation_trace_html(result: CompilationResult) -> str:
    module_rows = "".join(
        f"""
        <div class="module">
          <div class="module-title">{html.escape(expansion.module_id)}</div>
          <div><b>Objects:</b> {html.escape(", ".join(expansion.created_object_ids) or "—")}</div>
          <div><b>Connections:</b> {html.escape(", ".join(expansion.created_connection_ids) or "—")}</div>
          <div><b>Associations:</b> {html.escape(", ".join(expansion.created_association_ids) or "—")}</div>
        </div>
        """
        for expansion in result.module_expansions
    )

    stream_rows = "".join(
        f"""
        <div class="mapping">
          <div class="stream">{html.escape(stream_id)}</div>
          <div class="arrow">→</div>
          <div>{html.escape(" → ".join(connection_ids))}</div>
        </div>
        """
        for stream_id, connection_ids in result.source_stream_to_pid_connections.items()
    ) or '<div class="empty">No stream mappings.</div>'

    model = result.plant_model

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP Topology Compiler</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#e7e9ec;color:#111}}
header{{background:#fff;border-bottom:1px solid #aaa;padding:12px 16px;display:flex;justify-content:space-between}}
header a{{font-size:12px;color:#174a77;text-decoration:none;margin-left:14px}}
main{{padding:12px;display:grid;grid-template-columns:360px 1fr;gap:12px}}
.panel{{background:#fff;border:1px solid #aaa;padding:16px}}
.title{{font-weight:700;font-size:15px}} .muted{{font-size:11px;color:#666}}
.section{{font-size:10px;font-weight:700;text-transform:uppercase;margin-top:16px;margin-bottom:6px}}
.metric{{font-size:11px;padding:6px 0;border-bottom:1px solid #eee}}
.module{{border:1px solid #cbd5e1;border-radius:5px;padding:9px;margin:7px 0;font-size:10px}}
.module-title{{font-weight:700;margin-bottom:6px}}
.module div{{margin:3px 0;line-height:1.35}}
.mapping{{display:grid;grid-template-columns:100px 30px 1fr;align-items:center;border:1px solid #ddd;border-radius:5px;padding:8px;margin:7px 0;font-size:10px}}
.stream{{font-weight:700}} .arrow{{text-align:center;font-size:15px}}
.badge{{display:inline-block;background:#dcfce7;color:#166534;font-weight:700;font-size:11px;padding:6px 10px;border-radius:999px}}
.flow{{border:1px solid #d1d5db;border-radius:5px;padding:12px;font:12px monospace;line-height:1.7;background:#fafafa}}
.empty{{font-size:10px;color:#666}}
</style>
</head>
<body>
<header>
<div><strong>Digital BDEP — Engineering Topology Compiler</strong><div class="muted">MVP 0.8 · approved configuration → P&ID semantic graph</div></div>
<nav><a href="/configuration-match/CASE-NORMAL">Matcher</a><a href="/engineering">Generated P&ID</a><a href="/graph">Graph View</a></nav>
</header>
<main>
<section class="panel">
<div class="badge">COMPILED</div>
<div class="section">Provenance</div>
<div class="metric"><b>Configuration:</b> {html.escape(result.configuration_id)}</div>
<div class="metric"><b>Version:</b> {html.escape(result.configuration_version)}</div>
<div class="metric"><b>Design Basis:</b> {html.escape(result.source_design_basis_id)} Rev {html.escape(result.source_design_basis_revision)}</div>
<div class="metric"><b>Design case:</b> {html.escape(result.source_design_case_id)}</div>
<div class="metric"><b>Simulation:</b> {html.escape(result.source_simulation_case_id)}</div>

<div class="section">Compiled semantic graph</div>
<div class="metric"><b>Objects:</b> {len(model.objects)}</div>
<div class="metric"><b>Connections:</b> {len(model.connections)}</div>
<div class="metric"><b>Associations:</b> {len(model.associations)}</div>

<div class="section">Execution chain</div>
<div class="flow">
Design Basis<br>
↓<br>
Simulation / PFD<br>
↓<br>
EXACT configuration match<br>
↓<br>
Approved module expansion<br>
↓<br>
P&ID semantic graph<br>
↓<br>
Drafter engine
</div>
</section>

<section class="panel">
<div class="title">PFD process flow retained through P&ID expansion</div>
<div class="muted">A source simulation stream remains traceable to the semantic connections that implement it on the P&ID.</div>
{stream_rows}

<div class="section">Approved module expansion trace</div>
{module_rows}
</section>
</main>
</body>
</html>"""
