"""Unresolved vector T-junction evidence: NEVER merges process paths automatically.

A line endpoint lying on another line's interior may represent a tee. Both
interiors crossing, however, is NOT a junction. These are engineer-review
candidates for the next network-splitting stage.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict

MAX_TEE_PROPOSALS = 2000
JOIN_TOLERANCE = 2.5


def propose_unresolved_tees(segments: list[dict], document_sha256: str) -> list[dict]:
    vertical, horizontal = defaultdict(list), defaultdict(list)
    by_page = defaultdict(list)
    for s in segments:
        if s.get("stroke_style") == "dashed":
            continue
        x1, y1 = s["start"]
        x2, y2 = s["end"]
        if abs(x1 - x2) <= 1.5 and abs(y1 - y2) > 15:
            by_page[s["page"]].append((s, "vertical"))
            vertical[(s["page"], round(x1 / JOIN_TOLERANCE))].append(s)
        elif abs(y1 - y2) <= 1.5 and abs(x1 - x2) > 15:
            by_page[s["page"]].append((s, "horizontal"))
            horizontal[(s["page"], round(y1 / JOIN_TOLERANCE))].append(s)
    proposals = []
    seen = set()
    for page, lines in sorted(by_page.items()):
        for stroke, orientation in lines:
            for p in [stroke["start"], stroke["end"]]:
                opposite = horizontal if orientation == "vertical" else vertical
                coordinate = p[1] if orientation == "vertical" else p[0]
                for index in range(round(coordinate / JOIN_TOLERANCE) - 1,
                                   round(coordinate / JOIN_TOLERANCE) + 2):
                    for host in opposite.get((page, index), []):
                        if host["id"] == stroke["id"]:
                            continue
                        x1, y1 = host["start"]
                        x2, y2 = host["end"]
                        if orientation == "vertical":
                            cross_coordinate = (y1 + y2) / 2
                            offset = abs(p[1] - cross_coordinate)
                            in_host = min(x1, x2) + JOIN_TOLERANCE < p[0] < max(x1, x2) - JOIN_TOLERANCE
                        else:
                            cross_coordinate = (x1 + x2) / 2
                            offset = abs(p[0] - cross_coordinate)
                            in_host = min(y1, y2) + JOIN_TOLERANCE < p[1] < max(y1, y2) - JOIN_TOLERANCE
                        if offset > JOIN_TOLERANCE or not in_host:
                            continue
                        key = (page, stroke["id"], host["id"], round(p[0], 1), round(p[1], 1))
                        if key in seen:
                            continue
                        seen.add(key)
                        if len(proposals) >= MAX_TEE_PROPOSALS:
                            return proposals
                        junction_id = hashlib.sha256(f"{document_sha256}:{key}".encode()).hexdigest()[:16]
                        proposals.append({
                            "id": "TEE-" + junction_id,
                            "page": page,
                            "point": [round(p[0], 2), round(p[1], 2)],
                            "source_bbox": [round(p[0]-6, 2), round(p[1]-6, 2),
                                            round(p[0]+6, 2), round(p[1]+6, 2)],
                            "source_segment_ids": [stroke["id"], host["id"]],
                            "junction_type": "endpoint_to_interior_tee_hypothesis",
                            "connection_state": "not_merged",
                            "review_status": "unreviewed",
                            "requires_human_junction_decision": True,
                        })
    return proposals
