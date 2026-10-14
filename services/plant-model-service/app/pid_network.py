"""Conservative multi-segment piping-route proposals from source drawing geometry.

Rules:
- Only physical segment ENDPOINTS can connect; geometric crossings cannot.
- A connection path terminates at the next recognized symbol.
- Dashed strokes are treated as signal/annotation and excluded from process routes.
- No inference of direction, P&ID intent, off-sheet continuity, or hydraulic class.
- All topology remains engineer-unreviewed evidence.
"""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict, deque

SNAP_TOLERANCE_PTS = 3.0
SYMBOL_ATTACH_TOLERANCE_PTS = 8.0
MAX_PATH_HOPS = 120
MAX_VISITS_PER_SOURCE = 2500
MAX_PROPOSALS = 5000


def _distance(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _dist_to_box(p, box) -> float:
    return math.hypot(max(box[0] - p[0], p[0] - box[2], 0),
                      max(box[1] - p[1], p[1] - box[3], 0))


def _bbox_all(boxes):
    return [
        round(min(box[0] for box in boxes), 2),
        round(min(box[1] for box in boxes), 2),
        round(max(box[2] for box in boxes), 2),
        round(max(box[3] for box in boxes), 2),
    ]


def _kind(a: dict, b: dict) -> str:
    types = (a.get("symbol_type_from_tag") or "",
             b.get("symbol_type_from_tag") or "")
    if any(token in t for t in types
           for token in ("transmitter", "indicator", "controller")):
        return "instrument_tap_candidate"
    return "process_candidate"


def propose_network_connections(symbols: list[dict], segments: list[dict],
                                source_sha256: str) -> dict:
    """Produce source-evidenced multi-segment route hypotheses.

    Connected components are constructed strictly from snapped endpoints;
    endpoint-to-stroke T intersections and stroke-to-stroke crossings are NOT
    silently treated as junctions.
    """
    connections, stats = [], {
        "total_line_segments": len(segments), "usable_process_segments": 0,
        "skipped_dashed_segments": 0, "ambiguous_symbol_attachments": 0,
        "endpoint_components": 0, "routes_proposed": 0,
        "limitations": [
            "Crossings are never joined without an explicit reviewed connection.",
            "Endpoint-on-interior T junctions are not yet joined.",
            "Only source-evidenced snapped multi-segment routes are proposed.",
            "Proposed edges and orientations require engineering review.",
        ],
    }
    # Independent graph per drawing sheet: never invent cross-sheet continuity.
    by_page = defaultdict(list)
    for segment in segments:
        if segment.get("stroke_style") == "dashed":
            stats["skipped_dashed_segments"] += 1
            continue
        if segment.get("length", 0) < 15:
            continue
        by_page[segment["page"]].append(segment)
    found_keys = set()
    for page, lines in sorted(by_page.items()):
        nodes = []
        buckets = defaultdict(list)
        adjacency = defaultdict(list)
        page_symbols = [s for s in symbols
                        if s.get("page") == page and s.get("geometry_id")
                        and s.get("symbol_type_from_tag")]
        if not page_symbols:
            continue

        def get_node(point):
            cx = round(point[0] / SNAP_TOLERANCE_PTS)
            cy = round(point[1] / SNAP_TOLERANCE_PTS)
            best, best_dist = None, SNAP_TOLERANCE_PTS + 0.01
            for x in range(cx - 1, cx + 2):
                for y in range(cy - 1, cy + 2):
                    for j in buckets[(x, y)]:
                        d = _distance(point, nodes[j])
                        if d < best_dist:
                            best, best_dist = j, d
            if best is not None:
                return best
            idx = len(nodes)
            nodes.append([float(point[0]), float(point[1])])
            buckets[(cx, cy)].append(idx)
            return idx

        for seg in lines:
            a, b = get_node(seg["start"]), get_node(seg["end"])
            if a == b:
                continue
            adjacency[a].append((b, seg))
            adjacency[b].append((a, seg))
            stats["usable_process_segments"] += 1

        # Each geometry endpoint is allowed at most one unambiguous symbol
        # attachment. Avoid co-located tag labels yielding false connections.
        node_attachments = defaultdict(list)
        symbol_starts = defaultdict(set)
        for node_idx, location in enumerate(nodes):
            nearby = sorted(
                ((s, _dist_to_box(location, s["bbox"])) for s in page_symbols
                 if _dist_to_box(location, s["bbox"]) <= SYMBOL_ATTACH_TOLERANCE_PTS),
                key=lambda pair: pair[1],
            )
            if not nearby:
                continue
            if len(nearby) > 1 and nearby[1][1] <= nearby[0][1] + 2:
                stats["ambiguous_symbol_attachments"] += 1
                continue
            symbol = nearby[0][0]
            node_attachments[node_idx].append(symbol)
            symbol_starts[symbol["tag_id"]].add(node_idx)

        # BFS from each symbol's perimeter. A recognized destination symbol
        # terminates the path; we do not "see through" pumps or control valves.
        symbol_by_id = {s["tag_id"]: s for s in page_symbols}
        for source_id, start_nodes in sorted(symbol_starts.items()):
            source = symbol_by_id[source_id]
            best_by_target = {}
            visited = set(start_nodes)
            queue = deque((node, (), (node,)) for node in sorted(start_nodes))
            while queue and len(visited) <= MAX_VISITS_PER_SOURCE:
                node, route, route_nodes = queue.popleft()
                targets = [s for s in node_attachments.get(node, [])
                           if s["tag_id"] != source_id]
                if targets and route:
                    for target in targets:
                        key = tuple(sorted((source["tag"], target["tag"])))
                        best = best_by_target.get(key)
                        if best is None or len(route) < len(best[0]):
                            best_by_target[key] = (route, route_nodes, target)
                    continue
                if len(route) >= MAX_PATH_HOPS:
                    continue
                for neighbor, segment in adjacency[node]:
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    queue.append(
                        (neighbor, (*route, segment),
                         (*route_nodes, neighbor))
                    )
            for key, (route, route_nodes, target) in best_by_target.items():
                scoped_key = (page, key)
                if scoped_key in found_keys:
                    continue
                if len(connections) >= MAX_PROPOSALS:
                    stats["limitations"].append("Proposal limit reached; split input")
                    break
                found_keys.add(scoped_key)
                source_seg_ids = []
                for source_seg in route:
                    for original_id in source_seg.get("source_stroke_ids", [source_seg["id"]]):
                        if not source_seg_ids or source_seg_ids[-1] != original_id:
                            source_seg_ids.append(original_id)
                box = _bbox_all([s["bbox"] for s in route])
                evidence = f'{source_sha256}:{page}:{key}:{source_seg_ids}'
                connections.append({
                    "id": "LINK-" + hashlib.sha256(evidence.encode()).hexdigest()[:16],
                    "page": page, "tag_a": source["tag"],
                    "tag_b": target["tag"], "tag_id_a": source_id,
                    "tag_id_b": target["tag_id"],
                    "type": _kind(source, target),
                    "source_segment_ids": source_seg_ids,
                    "route_piece_ids": [stroke["id"] for stroke in route],
                    "approved_tee_ids": sorted({
                        t for stroke in route for t in stroke.get("approved_tee_ids", [])
                    }),
                    "source_route_points": [
                        [round(nodes[n][0], 2), round(nodes[n][1], 2)]
                        for n in route_nodes
                    ],
                    "source_bbox": box,
                    "hops": len(route),
                    "trace_method": "endpoint_snapped_path_graph",
                    "confidence": "geometry_hypothesis_unverified",
                    "review_status": "unreviewed",
                    "direction": "unverified",
                })
        stats["endpoint_components"] += len(nodes)
    stats["routes_proposed"] = len(connections)
    return {"connection_proposals": connections, "diagnostics": stats}
