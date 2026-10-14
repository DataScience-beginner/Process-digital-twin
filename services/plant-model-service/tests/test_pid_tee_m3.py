"""M3: fail-closed engineer-approved tees and route review invalidation."""
from datetime import datetime, timezone

from app.pid_junction_review import reviewed_network
from app.pid_junctions import propose_unresolved_tees


def symbol(tag, box, kind):
    return {
        "tag": tag, "tag_id": tag, "page": 1, "bbox": box,
        "symbol_type_from_tag": kind, "geometry_id": "SHAPE-" + tag,
    }


def segment(sid, p, q):
    return {
        "id": sid, "page": 1, "start": p, "end": q,
        "bbox": [min(p[0], q[0]), min(p[1], q[1]),
                 max(p[0], q[0]), max(p[1], q[1])],
        "length": abs(p[0]-q[0])+abs(p[1]-q[1]),
        "stroke_style": "solid",
    }


def test_tee_joins_two_topology_paths_only_when_human_approves():
    symbols = [
        symbol("V-101", [0,0,20,20], "vertical_separator"),
        symbol("FCV-101", [90,0,110,20], "control_valve"),
        symbol("P-102", [45,80,65,100], "centrifugal_pump"),
    ]
    lines = [
        segment("trunk", [20,10], [90,10]),
        segment("branch", [55,10], [55,80]),
    ]
    tees = propose_unresolved_tees(lines, "source-sha")
    assert len(tees) == 1
    before = reviewed_network(symbols, lines, tees, "source-sha")
    before_pairs = {
        frozenset([r["tag_a"], r["tag_b"]])
        for r in before["connection_proposals"]
    }
    assert before_pairs == {frozenset(["V-101","FCV-101"])}
    tee = tees[0]
    tee.update({
        "review_status": "accepted",
        "reviewed_by": "engineer-01",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    })
    after = reviewed_network(symbols, lines, tees, "source-sha")
    pairs = {
        frozenset([r["tag_a"], r["tag_b"]])
        for r in after["connection_proposals"]
    }
    assert {frozenset(["V-101", "P-102"]),
            frozenset(["FCV-101", "P-102"])} <= pairs
    assert after["junction_decisions"]["approved_tee_ids_applied"] == [tee["id"]]
    assert all(edge["review_status"] == "unreviewed"
               for edge in after["connection_proposals"])
    approved = [r for r in after["connection_proposals"] if r["approved_tee_ids"]]
    assert approved
    assert all("trunk" in r["source_segment_ids"] for r in approved)
    assert all(r["source_route_points"] for r in approved)


def test_invalid_interior_crossing_cannot_be_approved():
    sym = [symbol("V-101", [0,0,20,20], "vertical_separator")]
    lines = [
        segment("h", [20,50], [90,50]),
        segment("v", [50,0], [50,100]),
    ]
    forged_tee = {
        "id": "FAKE-TEE", "page": 1, "point": [50,50],
        "source_segment_ids": ["h", "v"],
        "review_status": "accepted", "reviewed_by": "engineer",
        "reviewed_at": "2026-10-15T08:00:00Z",
    }
    result = reviewed_network(sym, lines, [forged_tee], "source-sha")
    assert not result["junction_decisions"]["approved_tee_ids_applied"]
    assert result["junction_decisions"]["not_applied"]
    assert not result["connection_proposals"]


def test_wrong_page_and_unreviewed_tee_are_not_used():
    sym = [
        symbol("V-101", [0,0,20,20], "vertical_separator"),
        symbol("FCV-101", [90,0,110,20], "control_valve"),
    ]
    lines = [
        segment("h", [20,10], [90,10]),
        segment("v", [50,10], [50,80]),
    ]
    tees = propose_unresolved_tees(lines, "source-sha")
    assert len(tees) == 1
    x = dict(tees[0])
    x.update(review_status="accepted", reviewed_by="engineer",
             reviewed_at="2026-10-15T09:00:00Z", page=2)
    result = reviewed_network(sym, lines, [x], "source-sha")
    assert result["junction_decisions"]["not_applied"]
    assert not result["junction_decisions"]["approved_tee_ids_applied"]
    assert all(item["review_status"] == "unreviewed" for item in result["connection_proposals"])
