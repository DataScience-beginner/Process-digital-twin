from __future__ import annotations

import html
from typing import Any


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(_fmt(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_fmt(val)}" for key, val in value.items())
    return str(value)


def _ref_button(ref: dict[str, Any]) -> str:
    return (
        f'<span class="node">{html.escape(ref.get("label") or ref.get("id", ""))}'
        f'<small>{html.escape((ref.get("relation") or "").replace("_", " "))}</small></span>'
    )


def _path(entity: dict[str, Any]) -> str:
    refs = entity.get("path") or []
    if not refs:
        return '<div class="empty">No path available.</div>'
    return '<div class="path">' + '<span class="arrow">→</span>'.join(
        _ref_button(ref) for ref in refs
    ) + '</div>'


def _kv(value: Any) -> str:
    if not isinstance(value, dict):
        return f'<div class="value">{html.escape(_fmt(value))}</div>'
    rows = "".join(
        f'<tr><td>{html.escape(str(key).replace("_", " ").title())}</td>'
        f'<td>{html.escape(_fmt(val))}</td></tr>'
        for key, val in value.items()
    )
    return f'<table><tbody>{rows}</tbody></table>'


def _calc(entity: dict[str, Any]) -> str:
    metadata = entity.get("record_metadata") or {}
    detail = metadata.get("calculation_detail") if isinstance(metadata, dict) else None
    if not isinstance(detail, dict):
        return ""

    sections = []
    for title, key in [
        ("Inputs", "inputs"),
        ("Criteria / Limits", "criteria"),
        ("Outputs", "outputs"),
    ]:
        rows = detail.get(key) or []
        if rows:
            body = "".join(
                f'<tr><td>{html.escape(str(row.get("name") or row.get("criterion_id") or "Item"))}</td>'
                f'<td>{html.escape(_fmt(row.get("value")))} {html.escape(str(row.get("unit") or ""))}</td></tr>'
                for row in rows
            )
            sections.append(f'<section><h3>{title}</h3><table><tbody>{body}</tbody></table></section>')

    cases = detail.get("case_results") or []
    if cases:
        keys = []
        for row in cases:
            for key in row:
                if key not in keys:
                    keys.append(key)
        head = "".join(f"<th>{html.escape(key.replace('_',' ').title())}</th>" for key in keys)
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(_fmt(row.get(key)))}</td>" for key in keys) + "</tr>"
            for row in cases
        )
        sections.append(f'<section><h3>Case Results</h3><div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></section>')

    governing = detail.get("governing_case")
    reason = detail.get("governing_reason")
    if governing or reason:
        sections.append(
            '<div class="notice"><b>Governing case:</b> '
            + html.escape(_fmt(governing))
            + '<br><b>Reason:</b> '
            + html.escape(_fmt(reason))
            + '</div>'
        )

    method = detail.get("method")
    if method:
        sections.append('<div class="method"><b>Method:</b> ' + html.escape(_fmt(method)) + '</div>')
    return "".join(sections)


def render_entity_detail_html(entity: dict[str, Any]) -> str:
    line_number = entity.get("line_number")
    stream_number = entity.get("stream_number")
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(entity.get("tag") or entity["id"])} — Digital BDEP Entity Detail</title>
<style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#eef1f4;color:#111}}
header{{background:#fff;border-bottom:1px solid #bbb;padding:14px 18px;display:flex;justify-content:space-between}}
header a{{font-size:12px;color:#174a77;text-decoration:none}}
main{{max-width:1300px;margin:auto;padding:14px}}
.hero,section,.panel{{background:#fff;border:1px solid #aaa;padding:14px;margin-bottom:10px}}
.hero h1{{margin:0;font-size:21px}} .muted{{font-size:10px;color:#64748b;margin-top:4px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
table{{border-collapse:collapse;width:100%;font-size:10px}} th,td{{border:1px solid #ddd;padding:6px;text-align:left;vertical-align:top}} th{{background:#f1f5f9}}
.path{{display:flex;flex-wrap:wrap;align-items:center;gap:5px}} .node{{border:1px solid #94a3b8;border-radius:999px;padding:6px 8px;font-size:10px;background:#fff}}
.node small{{display:block;color:#64748b;font-size:8px}} .arrow{{color:#64748b}}
.notice{{background:#fffbeb;border:1px solid #fde68a;padding:9px;font-size:10px;line-height:1.5}} .method{{background:#f8fafc;border:1px solid #e5e7eb;padding:8px;font-size:10px}}
h2{{font-size:14px;margin:0 0 9px}} h3{{font-size:11px;margin:0 0 7px}} .scroll{{overflow:auto}} .empty{{font-size:10px;color:#64748b}}
@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header><strong>Digital BDEP — Line / Connection Detail</strong><a href="/engineering">Engineering View</a></header>
<main>
<div class="hero">
<h1>{html.escape(entity.get("tag") or entity["id"])}</h1>
<div class="muted">{html.escape(entity.get("object_type") or entity.get("category") or "")} · {html.escape(entity.get("service") or "")}</div>
<div class="muted">Entity ID: {html.escape(entity["id"])}</div>
</div>

<div class="grid">
<section><h2>Definition</h2>
<table><tbody>
<tr><td>Line / connection number</td><td>{html.escape(_fmt(line_number or entity.get("tag")))}</td></tr>
<tr><td>Stream number</td><td>{html.escape(_fmt(stream_number))}</td></tr>
<tr><td>Status</td><td>{html.escape(_fmt(entity.get("status")))}</td></tr>
<tr><td>Semantic edges</td><td>{html.escape(_fmt(entity.get("semantic_edge_ids")))}</td></tr>
</tbody></table></section>
<section><h2>Published Engineering Output</h2>{_kv(entity.get("record_value"))}</section>
</div>

<section><h2>Connected Path</h2>{_path(entity)}</section>
{_calc(entity)}
</main>
</body></html>"""
