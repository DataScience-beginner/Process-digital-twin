"""M2: multi-stroke network, crossing handling and source-route evidence."""
from __future__ import annotations

from app.models import PlantModel
from app.pid_digitization import accepted_plant_draft
from app.pid_network import propose_network_connections
from app.pid_pipeline import build_pid_extraction
from scripts.generate_pid_corpus import generate


def _symbol(tag, box, category_type):
    return {
        "tag": tag, "tag_id": f"ID-{tag}", "page": 1,
        "bbox": box, "symbol_type_from_tag": category_type,
        "geometry_id": f"SYM-{tag}",
    }


def _segment(n, x1, y1, x2, y2, style="solid"):
    return {
        "id": f"SEG-{n}", "page": 1,
        "start": [x1, y1], "end": [x2, y2],
        "bbox": [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)],
        "length": abs(x2 - x1) + abs(y2 - y1),
        "stroke_style": style,
    }


def test_three_stroke_elbows_and_crossings_do_not_invent_a_junction():
    symbols = [
        _symbol("V-101", [0, 0, 20, 40], "vertical_separator"),
        _symbol("FCV-101", [50, 50, 70, 70], "control_valve"),
        _symbol("P-101", [100, 0, 120, 40], "centrifugal_pump"),
        _symbol("PT-101", [38, 80, 48, 100], "pressure_transmitter"),
    ]
    segments = [
        _segment(1, 20, 20, 35, 20),
        _segment(2, 35, 20, 35, 60),
        _segment(3, 35, 60, 50, 60),
        _segment(4, 70, 60, 85, 60),
        _segment(5, 85, 60, 85, 20),
        _segment(6, 85, 20, 100, 20),
        _segment(7, 43, 74, 43, 90),  # interior crossing on stroke 3
        _segment(8, 20, 30, 60, 30, "dashed"),
    ]
    result = propose_network_connections(symbols, segments, "abc")
    edges = result["connection_proposals"]
    process_pairs = {
        frozenset([edge["tag_a"], edge["tag_b"]])
        for edge in edges if edge["type"] == "process_candidate"
    }
    assert process_pairs == {
        frozenset(["V-101", "FCV-101"]),
        frozenset(["FCV-101", "P-101"]),
    }, edges
    assert not any("PT-101" in (edge["tag_a"], edge["tag_b"]) for edge in edges)
    assert result["diagnostics"]["skipped_dashed_segments"] == 1
    assert all(edge["hops"] == 3 for edge in edges)
    assert all(len(edge["source_route_points"]) == 4 for edge in edges)
    assert all(edge["review_status"] == "unreviewed" for edge in edges)


def test_real_generated_pdf_elbow_fixture_traces_multi_stroke_routes(tmp_path):
    generate(tmp_path)
    _, out = build_pid_extraction(
        (tmp_path / "elbow_crossing.pdf").read_bytes(), "elbow_crossing.pdf"
    )
    candidate = out["connection_proposals"]
    pairs = {
        frozenset([edge["tag_a"], edge["tag_b"]]): edge
        for edge in candidate if edge["type"] == "process_candidate"
    }
    for pair in [
        frozenset(["V-101", "FCV-101"]),
        frozenset(["FCV-101", "P-101"]),
    ]:
        assert pair in pairs, candidate
        assert pairs[pair]["hops"] >= 3
        assert len(pairs[pair]["source_segment_ids"]) >= 3
    for item in out["candidates"]:
        item["review_status"] = "accepted"
    draft = accepted_plant_draft("IMPORT-M2", "BDEP-DEMO-004",
                                 out["candidates"], candidate)
    assert draft["plant_model"]["connections"] == []
    # Simulate distinct engineer approval only after reviewing source.
    for pair in [
        frozenset(["V-101", "FCV-101"]),
        frozenset(["FCV-101", "P-101"]),
    ]:
        pairs[pair].update(review_status="accepted",
                           direction="a_to_b", reviewed_by="engineer-01")
    draft = accepted_plant_draft("IMPORT-M2", "BDEP-DEMO-004",
                                 out["candidates"], candidate)
    assert len(draft["plant_model"]["connections"]) >= 2
    assert all(len(e["source_segment_ids"]) >= 3
               for e in draft["edge_source_evidence"])
    model = PlantModel.model_validate(draft["plant_model"])
    assert len(model.connections) >= 2
    assert draft["publish_ready"] is False


def test_crossing_segments_dont_merge_when_both_interiors_intersect():
    symbols = [
        _symbol("P-101", [0, 0, 20, 20], "centrifugal_pump"),
        _symbol("FCV-101", [80, 0, 100, 20], "control_valve"),
        _symbol("V-101", [30, 90, 50, 110], "vertical_separator"),
    ]
    lines = [
        _segment("horizontal", 20, 10, 80, 10),
        _segment("vertical", 40, 60, 40, 90),
        _segment("crossing", 40, -10, 40, 50),  # crossing horizontal internally
    ]
    result = propose_network_connections(symbols, lines, "test")
    edges = result["connection_proposals"]
    assert any({e["tag_a"], e["tag_b"]} == {"P-101", "FCV-101"} for e in edges)
    assert not any("V-101" in (e["tag_a"], e["tag_b"]) for e in edges)
