from app.config_matcher import MatchStatus, match_configuration
from app.simulation import publish_demo_simulation


def _facts(required=True):
    return {"pump_minimum_flow_required": required}


def test_demo_pfd_is_exact_match_when_design_basis_is_satisfied():
    publication = publish_demo_simulation("CASE-NORMAL")
    result = match_configuration(publication, design_basis_facts=_facts(True))

    assert result.status == MatchStatus.EXACT
    assert result.configuration_id == "VESSEL_TO_PUMP_STANDARD_V1"
    assert result.node_mapping == {
        "upstream_vessel": "EQ-V101",
        "downstream_pump": "EQ-P101",
    }
    assert result.stream_mapping["edge_0"] == "STR-S102"
    assert "PUMP_MIN_FLOW_STANDARD_V1" in result.engineering_modules


def test_same_topology_without_design_basis_evidence_is_known_variant():
    publication = publish_demo_simulation("CASE-NORMAL")
    result = match_configuration(publication)

    assert result.status == MatchStatus.KNOWN_VARIANT
    assert result.configuration_id == "VESSEL_TO_PUMP_STANDARD_V1"
    assert any(
        check.rule == "pump_minimum_flow_required" and not check.passed
        for check in result.applicability
    )


def test_phase_mismatch_is_known_variant_not_exact():
    publication = publish_demo_simulation("CASE-NORMAL")
    streams = [
        stream.model_copy(update={"phase": "vapor"})
        if stream.id == "STR-S102"
        else stream
        for stream in publication.streams
    ]
    variant = publication.model_copy(update={"streams": streams})
    result = match_configuration(variant, design_basis_facts=_facts(True))

    assert result.status == MatchStatus.KNOWN_VARIANT
    assert result.configuration_id == "VESSEL_TO_PUMP_STANDARD_V1"


def test_unknown_topology_stops_for_engineering_definition():
    publication = publish_demo_simulation("CASE-NORMAL")
    equipment = [
        item.model_copy(update={"equipment_type": "shell_and_tube_exchanger"})
        if item.id == "EQ-P101"
        else item
        for item in publication.equipment
    ]
    unknown = publication.model_copy(update={"equipment": equipment})
    result = match_configuration(unknown, design_basis_facts=_facts(True))

    assert result.status == MatchStatus.UNKNOWN
    assert result.configuration_id is None
    assert result.engineering_modules == []


def test_match_is_tag_independent():
    publication = publish_demo_simulation("CASE-NORMAL")
    equipment = [
        item.model_copy(update={"tag": "V-2301"})
        if item.id == "EQ-V101"
        else item.model_copy(update={"tag": "P-2301"})
        if item.id == "EQ-P101"
        else item
        for item in publication.equipment
    ]
    renamed = publication.model_copy(update={"equipment": equipment})
    result = match_configuration(renamed, design_basis_facts=_facts(True))

    assert result.status == MatchStatus.EXACT
