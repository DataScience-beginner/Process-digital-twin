"""Engineered junction decisions applied to a *copy* of P&ID line evidence.

Never join a crossing just because two strokes touch in a drawing. Only
source-verified endpoint-to-interior tee proposals approved by an engineer
may split an underlying host segment and create a shared graph node.
"""
from __future__ import annotations

import math
from copy import deepcopy
from collections import defaultdict

from .pid_network import propose_network_connections

EPSILON = 2.5
MIN_SPLIT_LENGTH = 3.0


def _distance(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _on_interior(point: list[float], seg: dict) -> bool:
    a, b = seg["start"], seg["end"]
    width = _distance(a, b)
    if width < 2 * MIN_SPLIT_LENGTH:
        return False
    cross = abs((point[0] - a[0]) * (b[1] - a[1]) -
                (point[1] - a[1]) * (b[0] - a[0])) / width
    dot = ((point[0]-a[0])*(b[0]-a[0]) +
           (point[1]-a[1])*(b[1]-a[1])) / (width * width)
    return cross <= EPSILON and MIN_SPLIT_LENGTH/width < dot < 1 - MIN_SPLIT_LENGTH/width


def _is_valid_endpoint(point: list[float], seg: dict) -> bool:
    return any(_distance(point, p) <= EPSILON for p in
               (seg["start"], seg["end"]))


def _pieces(seg: dict, points: list[tuple[list[float], str]]) -> list[dict]:
    a, b = seg["start"], seg["end"]
    length = _distance(a, b)
    ordered = sorted(points, key=lambda item: (
        ((item[0][0]-a[0]) * (b[0]-a[0]) +
         (item[0][1]-a[1]) * (b[1]-a[1])) / (length*length)
    ))
    vertices = [a] + [point for point, _ in ordered] + [b]
    out = []
    for idx in range(len(vertices) - 1):
        start, end = vertices[idx], vertices[idx+1]
        if _distance(start, end) < MIN_SPLIT_LENGTH:
            continue
        new_seg = deepcopy(seg)
        new_seg["id"] = f'{seg["id"]}#split{idx}'
        new_seg["start"] = start
        new_seg["end"] = end
        new_seg["bbox"] = [
            min(start[0], end[0]), min(start[1], end[1]),
            max(start[0], end[0]), max(start[1], end[1]),
        ]
        new_seg["length"] = round(_distance(start, end), 2)
        new_seg["source_stroke_ids"] = seg.get("source_stroke_ids", [seg["id"]])
        new_seg["approved_tee_ids"] = [tee_id for _, tee_id in ordered]
        out.append(new_seg)
    return out


def reviewed_network(symbols: list[dict], segments: list[dict],
                     tees: list[dict], document_sha256: str) -> dict:
    """Rebuild route proposals using only explicitly approved tees.

    Rebuilt proposals are always UNREVIEWED, even if old routes were approved.
    The caller must not transfer old route approvals to changed paths.
    """
    originals = {s["id"]: s for s in segments}
    splits = defaultdict(list)
    applied, rejected = [], []
    for tee in tees:
        if tee.get("review_status") != "accepted":
            continue
        tee_id = tee["id"]
        if not tee.get("reviewed_by") or not tee.get("reviewed_at"):
            rejected.append({"tee_id": tee_id, "reason": "missing engineering reviewer or date"})
            continue
        ids = tee.get("source_segment_ids", [])
        if len(ids) != 2 or any(x not in originals for x in ids):
            rejected.append({"tee_id": tee_id, "reason": "missing original source stroke"})
            continue
        s1, s2 = (originals[ids[0]], originals[ids[1]])
        point = tee.get("point", [])
        if len(point) != 2 or s1["page"] != s2["page"] or tee["page"] != s1["page"]:
            rejected.append({"tee_id": tee_id, "reason": "invalid page/coordinate"})
            continue
        if s1.get("stroke_style") == "dashed" or s2.get("stroke_style") == "dashed":
            rejected.append({"tee_id": tee_id, "reason": "signal stroke cannot be auto-joined"})
            continue
        # Exactly one host contains the point in its INTERIOR and the other
        # has a true ENDPOINT at it. Interior/interior crosses fail closed.
        matches = [
            (host, branch) for host, branch in ((s1,s2),(s2,s1))
            if _on_interior(point, host) and _is_valid_endpoint(point, branch)
        ]
        if len(matches) != 1:
            rejected.append({"tee_id": tee_id, "reason": "not endpoint-to-interior geometry"})
            continue
        host, _ = matches[0]
        splits[host["id"]].append((point, tee_id))
        applied.append(tee_id)

    adjusted = []
    for seg in segments:
        points = splits.get(seg["id"], [])
        if not points:
            adjusted.append(deepcopy(seg))
            continue
        # Reject close, duplicate split points rather than producing tiny,
        # invalid strokes or uncertain graph joins.
        accepted_points = []
        for point, tee_id in points:
            if any(_distance(point, other) < MIN_SPLIT_LENGTH for other, _ in accepted_points):
                rejected.append({"tee_id": tee_id, "reason": "duplicate/nearby tee"})
                if tee_id in applied:
                    applied.remove(tee_id)
                continue
            accepted_points.append((point, tee_id))
        if accepted_points:
            adjusted.extend(_pieces(seg, accepted_points))
        else:
            adjusted.append(deepcopy(seg))

    result = propose_network_connections(symbols, adjusted, document_sha256)
    result["junction_decisions"] = {
        "approved_tee_ids_applied": sorted(applied),
        "not_applied": rejected,
        "route_reviews_reset": True,
    }
    return result
