"""Geometric evidence extraction and conservative topology proposals for vector PDFs.

Not a trained symbol detector. Reported connections are *hypotheses* requiring
source-page engineering review, not verified plant topology.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any

import fitz

MAX_DRAWINGS_PER_PAGE = 12000
MAX_SEGMENTS_PER_PAGE = 20000
GEOMETRY_MATCH_DISTANCE = 85.0
ENDPOINT_SNAP_DISTANCE = 11.0


def _roundbox(rect) -> list[float]:
    return [round(float(rect.x0), 2), round(float(rect.y0), 2),
            round(float(rect.x1), 2), round(float(rect.y1), 2)]


def _point(p) -> list[float]:
    return [round(float(p.x), 2), round(float(p.y), 2)]


def _rect_distance(a: list[float], b: list[float]) -> float:
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)


def _point_rect_distance(p: list[float], rect: list[float]) -> float:
    return math.hypot(max(rect[0] - p[0], p[0] - rect[2], 0),
                      max(rect[1] - p[1], p[1] - rect[3], 0))


def _length(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def extract_vector_evidence(pdf: bytes) -> dict[str, list]:
    """Return segment and simple closed-geometry evidence with PDF coordinates."""
    segments, primitives, warnings = [], [], []
    with fitz.open(stream=pdf, filetype="pdf") as document:
        for p, page in enumerate(document, 1):
            drawings = page.get_drawings()
            if len(drawings) > MAX_DRAWINGS_PER_PAGE:
                warnings.append(f"Page {p}: drawing count limit reached")
            for dnum, d in enumerate(drawings[:MAX_DRAWINGS_PER_PAGE]):
                rect = d.get("rect")
                commands = d.get("items", [])
                if rect is None:
                    continue
                # PyMuPDF groups many independent shapes under one draw path.
                # Interpret individual commands/subpaths, NEVER the entire
                # path bbox as a symbol (which might cover a whole drawing).
                for j, cmd in enumerate(commands):
                    symbol_kind, symbol_box = None, None
                    if cmd[0] == "re":
                        local = _roundbox(cmd[1])
                        if local[2] - local[0] > 12 and local[3] - local[1] > 12:
                            symbol_kind, symbol_box = "rectangle", local
                    elif cmd[0] == "c":
                        if j + 3 < len(commands) and all(
                            c[0] == "c" for c in commands[j:j + 4]
                        ) and (j == 0 or commands[j - 1][0] != "c"):
                            control = [pt for c in commands[j:j + 4] for pt in c[1:]]
                            xs = [float(pt.x) for pt in control]
                            ys = [float(pt.y) for pt in control]
                            local = [round(min(xs), 2), round(min(ys), 2),
                                     round(max(xs), 2), round(max(ys), 2)]
                            w, h = local[2] - local[0], local[3] - local[1]
                            if 8 < w < 220 and .78 <= w / max(h, .01) <= 1.22:
                                symbol_kind, symbol_box = "circle", local
                    elif cmd[0] == "l" and j + 2 < len(commands):
                        triplet = commands[j:j + 3]
                        if all(c[0] == "l" for c in triplet):
                            joined = all(
                                _length(_point(triplet[k][2]), _point(triplet[k+1][1])) < 2
                                for k in (0, 1)
                            )
                            closed = _length(_point(triplet[2][2]), _point(triplet[0][1])) < 2
                            if joined and closed:
                                pts = [_point(c[1]) for c in triplet]
                                xs, ys = [pt[0] for pt in pts], [pt[1] for pt in pts]
                                local = [min(xs), min(ys), max(xs), max(ys)]
                                if 10 < max(local[2]-local[0], local[3]-local[1]) < 105:
                                    symbol_kind, symbol_box = "triangle", local
                    if symbol_kind:
                        primitives.append({
                            "id": f"PG{p}-D{dnum}-S{j}",
                            "page": p, "type": symbol_kind,
                            "bbox": symbol_box, "source": "pdf_vector_path",
                        })
                for cmd_num, command in enumerate(commands):
                    if command[0] != "l":
                        continue
                    a, b = _point(command[1]), _point(command[2])
                    length = _length(a, b)
                    if length < 15 or len(segments) >= MAX_SEGMENTS_PER_PAGE:
                        continue
                    # Only near-orthogonal segments are candidates for initial
                    # process-line graph reconstruction. Diagonals are retained
                    # as symbol evidence above and not silently interpreted.
                    if abs(a[0] - b[0]) > 1.5 and abs(a[1] - b[1]) > 1.5:
                        continue
                    segments.append({
                        "id": f"PG{p}-D{dnum}-L{cmd_num}",
                        "page": p, "start": a, "end": b,
                        "bbox": [min(a[0], b[0]), min(a[1], b[1]),
                                 max(a[0], b[0]), max(a[1], b[1])],
                        "length": round(length, 2),
                        "source": "pdf_vector_path",
                    })
            if len(segments) >= MAX_SEGMENTS_PER_PAGE:
                warnings.append(f"Vector segment limit reached on page {p}")
                break
    return {"segments": segments, "primitives": primitives, "warnings": warnings}


def detect_symbol_hypotheses(tags: list[dict], primitives: list[dict]) -> list[dict]:
    """Tie visually observed basic geometries to textual engineering tag classes."""
    result = []
    preferred = {
        "centrifugal_pump": ("circle",),
        "vertical_separator": ("rectangle",),
        "pressure_transmitter": ("circle",),
        "pressure_indicator": ("circle",),
        "flow_transmitter": ("circle",),
        "level_transmitter": ("circle",),
        "level_indicator": ("circle",),
        "level_controller": ("circle",),
        "flow_controller": ("circle",),
        "control_valve": ("triangle",),
        "relief_valve": ("triangle",),
        "isolation_valve": ("triangle",),
        "check_valve": ("triangle",),
    }
    for tag in tags:
        geometry = [g for g in primitives
                    if g["page"] == tag["page"]
                    and g["type"] in preferred.get(tag["object_type"], ())
                    and _rect_distance(tag["bbox"], g["bbox"]) <= GEOMETRY_MATCH_DISTANCE]
        geometry.sort(key=lambda g: _rect_distance(tag["bbox"], g["bbox"]))
        best = geometry[0] if geometry else None
        result.append({
            "tag_id": tag["id"], "tag": tag["tag"], "page": tag["page"],
            "symbol_type_from_tag": tag["object_type"],
            "visual_geometry": best["type"] if best else None,
            "geometry_id": best["id"] if best else None,
            "bbox": best["bbox"] if best else tag["bbox"],
            "detection_method": "tag_and_vector_geometry_heuristic" if best else "tag_only",
            "confidence": "hypothesis_unverified",
            "review_status": "unreviewed",
        })
    return result


def propose_connections(
    symbols: list[dict], segments: list[dict], document_sha256: str
) -> list[dict]:
    """Find direct vector strokes whose endpoints touch two *different* symbols.

    Conservative one-segment inference only; not multi-segment path tracing.
    Crossings are never interpreted as junctions.
    """
    result, dedup = [], set()
    eligible = [s for s in symbols if s["geometry_id"]]
    for line in segments:
        if line["length"] < 23:
            continue
        at_start = sorted(
            ((s, _point_rect_distance(line["start"], s["bbox"])) for s in eligible
             if s["page"] == line["page"]),
            key=lambda entry: entry[1],
        )
        at_end = sorted(
            ((s, _point_rect_distance(line["end"], s["bbox"])) for s in eligible
             if s["page"] == line["page"]),
            key=lambda entry: entry[1],
        )
        if not at_start or not at_end:
            continue
        a, da = at_start[0]
        b, db = at_end[0]
        if a["tag_id"] == b["tag_id"] or max(da, db) > ENDPOINT_SNAP_DISTANCE:
            continue
        # Ambiguous: two equally near symbols at an endpoint.
        if (len(at_start) > 1 and at_start[1][1] <= da + 2) or (
            len(at_end) > 1 and at_end[1][1] <= db + 2
        ):
            continue
        key = (line["page"], tuple(sorted((a["tag"], b["tag"]))))
        if key in dedup:
            continue
        dedup.add(key)
        proof = f'{document_sha256}:{line["id"]}:{key}'
        result.append({
            "id": "LINK-" + hashlib.sha256(proof.encode()).hexdigest()[:16],
            "tag_a": a["tag"], "tag_b": b["tag"],
            "tag_id_a": a["tag_id"], "tag_id_b": b["tag_id"],
            "page": line["page"], "source_segment_ids": [line["id"]],
            "source_bbox": line["bbox"], "type": "process_candidate",
            "direction": "unverified", "review_status": "unreviewed",
            "confidence": "geometric_hypothesis_only",
        })
    return result
