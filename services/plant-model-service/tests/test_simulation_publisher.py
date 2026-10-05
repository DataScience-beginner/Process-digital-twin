from app.simulation import publish_demo_simulation


def test_simulation_publication_has_pfd_level_equipment_only():
    publication = publish_demo_simulation("CASE-NORMAL")
    ids = {item.id for item in publication.equipment}
    assert ids == {"EQ-V101", "EQ-P101"}
    serialized = publication.model_dump_json()
    for forbidden in ["PSV-101", "LCV-101", "FT-101", "FIC-101", "FCV-101"]:
        assert forbidden not in serialized


def test_simulation_publishes_vessel_to_pump_process_flow():
    publication = publish_demo_simulation("CASE-NORMAL")
    s102 = next(stream for stream in publication.streams if stream.simulator_stream_id == "S-102")
    assert s102.source_equipment_id == "EQ-V101"
    assert s102.destination_equipment_id == "EQ-P101"
    assert s102.phase == "liquid"


def test_cases_change_process_conditions_without_changing_topology():
    normal = publish_demo_simulation("CASE-NORMAL")
    maximum = publish_demo_simulation("CASE-MAX")
    turndown = publish_demo_simulation("CASE-TURNDOWN")

    normal_edges = normal.pfd_edges()
    assert maximum.pfd_edges() == normal_edges
    assert turndown.pfd_edges() == normal_edges

    normal_feed = next(s for s in normal.streams if s.simulator_stream_id == "S-100")
    max_feed = next(s for s in maximum.streams if s.simulator_stream_id == "S-100")
    min_feed = next(s for s in turndown.streams if s.simulator_stream_id == "S-100")
    assert min_feed.mass_flow < normal_feed.mass_flow < max_feed.mass_flow


def test_simulation_is_traceable_to_design_basis_revision():
    publication = publish_demo_simulation("CASE-MAX")
    assert publication.design_basis_id == "DB-001"
    assert publication.design_basis_revision == "A"
    assert publication.design_case_id == "CASE-MAX"
