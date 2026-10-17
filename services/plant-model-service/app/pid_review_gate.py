"""Source-anchored P&ID review gate. Generic code only; never embed client artwork.

A symbol approval is not a topology approval.  An apparent line crossing is
not a tee.  A pump-port candidate is not yet a pipe route.  Routes enter the
accepted plant graph only with explicit source-verified engineering evidence.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from typing import Any

VALID_SHEET_ROLES = {"SYMBOL_LEGEND", "DETAIL_STANDARD", "INDEX", "COVER", "PID"}


def check_sheet_index(rows: list[dict], expected_pages: set[int]) -> dict[str, Any]:
    """Check classification coverage, NOT glyph/engineering approval."""
    page_nums = [r.get("pdf_page") for r in rows]
    if any(type(n) is not int or n < 1 for n in page_nums) or len(set(page_nums)) != len(page_nums):
        raise ValueError("Each page must have one unique positive source PDF page number")
    if set(page_nums) != expected_pages:
        raise ValueError("Inventory incomplete or contains unexpected pages")
    for r in rows:
        if r.get("role") not in VALID_SHEET_ROLES or not r.get("source_pdf_sha256"):
            raise ValueError("Invalid source role or missing provenance hash")
    counts = {kind: sum(r["role"] == kind for r in rows) for kind in VALID_SHEET_ROLES}
    return {"pages_checked": len(rows), "role_counts": counts,
            "glyph_library_ready": False, "engineering_details_approved": False,
            "notice": "Sheet type completeness does not establish symbol/typical detail mapping completion."}


def propose_local_pump_review(source_sha256: str, page: int,
                              pumps: list[dict]) -> dict[str, Any]:
    """Local review questions; never infer actual routes/directions."""
    if len(source_sha256) != 64 or page < 1:
        raise ValueError("Valid SHA256 and 1-based PDF page required")
    if not pumps:
        raise ValueError("At least one source-localized pump required")
    nodes, ports = [], []
    seen = set()
    for p in pumps:
        ident, tag, c = p["id"], p["tag_proposal"], p["center"]
        if ident in seen or not ident or not tag or len(c) != 2 or not all(isinstance(x,(int,float)) for x in c):
            raise ValueError("Pump identity/center invalid or repeated")
        seen.add(ident)
        nodes.append({"id": ident, "tag_proposal": tag, "center": c,
                      "status": "UNREVIEWED", "source_page": page})
        for side in ("left", "right"):
            ports.append({"id": f"{ident}-{side}", "node_id": ident,
                          "side": side, "candidate_only": True,
                          "status": "UNREVIEWED", "connected_to": None})
    return {"schema": "pid-source-review-gate-v1", "source_sha256": source_sha256,
            "page": page, "nodes": nodes, "ports": ports,
            "approved_nodes": [], "approved_edges": [],
            "engineering_graph_ready": False}


def record_markup_decisions(review: dict, decisions: dict) -> dict:
    """Validate explicit human decisions and record nodes only, never auto edges."""
    if decisions.get("schema") != "pid-review-decisions-v1":
        raise ValueError("Unsupported decisions schema")
    person = decisions.get("reviewer", "")
    if not isinstance(person,str) or not person.strip() or not decisions.get("reviewed_at"):
        raise ValueError("Reviewer identity and timestamp mandatory")
    src = decisions.get("source", {})
    if src.get("source_sha256") != review["source_sha256"]:
        raise ValueError("Wrong P&ID source document")
    revised = deepcopy(review)
    by_id = {x["id"]: x for x in (revised["nodes"] + revised["ports"])}
    seen=set()
    for item in decisions.get("decisions", []):
        i=item.get("id");decision=item.get("decision")
        if i not in by_id or i in seen or decision not in ("CONFIRM", "REJECT", "UNRESOLVED"):
            raise ValueError("Unknown/repeated candidate or unsupported decision")
        seen.add(i)
        by_id[i]["status"]={"CONFIRM":"SOURCE_REVIEWED", "REJECT":"REJECTED", "UNRESOLVED":"UNREVIEWED"}[decision]
        by_id[i]["reviewer"] = person
    revised["approved_nodes"] = [x["id"] for x in revised["nodes"] if x["status"] == "SOURCE_REVIEWED"]
    revised["approved_edges"] = []  # cannot infer edges from local port confirmations
    revised["engineering_graph_ready"] = False
    revised["review_event_sha256"] = sha256(json.dumps(decisions,sort_keys=True).encode()).hexdigest()
    return revised


def accept_verified_route(review: dict, route: dict) -> dict:
    """Require evidence and two actual reviewers before creating a physical edge.

    This is intentionally not called by the offline 6-port markup reviewer.
    A separate pipe-trace workflow must supply the actual source stroke IDs,
    terminal port IDs, and crossing/junction classification decisions.
    """
    if route.get("source_sha256") != review["source_sha256"] or route.get("pdf_page") != review["page"]:
        raise ValueError("Route source/page mismatch")
    n={x['id'] for x in review['nodes'] if x['status'] == 'SOURCE_REVIEWED'}
    src,dst=route.get('source_node'),route.get('target_node')
    if src not in n or dst not in n or src == dst:
        raise ValueError("Routes require two distinct source-reviewed terminal nodes")
    r1=route.get('route_reviewer');r2=route.get('independent_reviewer')
    if not r1 or not r2 or r1==r2 or not route.get('route_reviewed_at'):
        raise ValueError("Separate reviewers and dated approval required")
    if route.get('process_line_confirmed') is not True or route.get('tee_crossing_review_completed') is not True:
        raise ValueError("Line type and junction/crossing evidence required")
    if not route.get('source_stroke_ids') or not all(isinstance(s,str) and s for s in route['source_stroke_ids']):
        raise ValueError("Source stroke IDs required")
    if not route.get('from_port_id') or not route.get('to_port_id'):
        raise ValueError("Both independently identified ports required")
    out=deepcopy(review)
    out['approved_edges'].append({'id':route.get('id'),'from':src,'to':dst,
      'from_port':route['from_port_id'],'to_port':route['to_port_id'],
      'source_stroke_ids':route['source_stroke_ids'],'reviewed_by':[r1,r2],
      'status':'ENGINEERING_ACCEPTED'})
    out['engineering_graph_ready']=False  # complete graph validation is separate
    return out
