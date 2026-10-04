import pytest

from app.config_matcher import MatchStatus, match_configuration
from app.configurations import demo_integrated_configuration_model
from app.simulation import publish_demo_simulation
from app.drafter import build_drafter_instrumented
from app.topology_compiler import CompilationBlocked, compile_engineering_topology


def _exact_match(publication):
    return match_configuration(
        publication,
        design_basis_facts={"pump_minimum_flow_required": True},
    )


def test_exact_match_compiles_pid_semantic_topology():
    publication = publish_demo_simulation("CASE-NORMAL")
    match = _exact_match(publication)
    result = compile_engineering_topology(publication, match)

    ids = {obj.id for obj in result.plant_model.objects}
    for expected in [
        "EQ-V101",
        "EQ-P101",
        "VLV-LCV101",
        "VLV-PSV101",
        "INS-PT101",
        "INS-LT101",
        "INS-LIC101",
        "INS-FT101",
        "INS-FIC101",
        "VLV-FCV101",
        "VLV-NRV101",
    ]:
        assert expected in ids


def test_compiled_graph_is_semantically_equivalent_to_approved_reference():
    publication = publish_demo_simulation("CASE-NORMAL")
    compiled = compile_engineering_topology(
        publication,
        _exact_match(publication),
    ).plant_model
    reference = demo_integrated_configuration_model()

    assert {obj.id for obj in compiled.objects} == {obj.id for obj in reference.objects}
    assert {item.id for item in compiled.connections} == {
        item.id for item in reference.connections
    }
    assert {item.id for item in compiled.associations} == {
        item.id for item in reference.associations
    }


def test_pfd_stream_is_traceable_to_pid_connections():
    publication = publish_demo_simulation("CASE-NORMAL")
    result = compile_engineering_topology(publication, _exact_match(publication))

    assert result.source_stream_to_pid_connections["STR-S102"] == [
        "C-LIQ-01",
        "C-LIQ-02",
        "C-SUC-02",
    ]


def test_all_approved_modules_have_compilation_trace():
    publication = publish_demo_simulation("CASE-NORMAL")
    match = _exact_match(publication)
    result = compile_engineering_topology(publication, match)

    traced = {item.module_id for item in result.module_expansions}
    assert traced == set(match.engineering_modules)
    assert next(
        item for item in result.module_expansions
        if item.module_id == "PUMP_MIN_FLOW_STANDARD_V1"
    ).created_connection_ids == [
        "C-REC-01",
        "C-REC-02",
        "C-REC-03",
        "S-FLOW-01",
        "S-FLOW-02",
    ]


def test_simulation_does_not_contain_pid_objects_but_compiler_creates_them():
    publication = publish_demo_simulation("CASE-NORMAL")
    raw = publication.model_dump_json()
    assert "VLV-LCV101" not in raw
    assert "VLV-PSV101" not in raw
    assert "INS-FIC101" not in raw

    result = compile_engineering_topology(publication, _exact_match(publication))
    compiled_ids = {obj.id for obj in result.plant_model.objects}
    assert {"VLV-LCV101", "VLV-PSV101", "INS-FIC101"} <= compiled_ids


def test_known_variant_is_blocked_from_compilation():
    publication = publish_demo_simulation("CASE-NORMAL")
    variant_match = match_configuration(publication)
    assert variant_match.status == MatchStatus.KNOWN_VARIANT

    with pytest.raises(CompilationBlocked, match="requires EXACT match"):
        compile_engineering_topology(publication, variant_match)


def test_unknown_configuration_is_blocked_from_compilation():
    publication = publish_demo_simulation("CASE-NORMAL")
    equipment = [
        item.model_copy(update={"equipment_type": "shell_and_tube_exchanger"})
        if item.id == "EQ-P101"
        else item
        for item in publication.equipment
    ]
    unknown_publication = publication.model_copy(update={"equipment": equipment})
    unknown_match = match_configuration(
        unknown_publication,
        design_basis_facts={"pump_minimum_flow_required": True},
    )
    assert unknown_match.status == MatchStatus.UNKNOWN

    with pytest.raises(CompilationBlocked, match="requires EXACT match"):
        compile_engineering_topology(unknown_publication, unknown_match)



def test_compiled_model_drives_existing_drafter_with_connected_routes():
    publication = publish_demo_simulation("CASE-NORMAL")
    result = compile_engineering_topology(publication, _exact_match(publication))
    plan = build_drafter_instrumented(result.plant_model)

    roles = {route.role for route in plan.routes}
    assert {
        "primary_suction",
        "primary_discharge",
        "minimum_flow_recycle",
        "psv_relief",
        "vessel_vent",
        "vessel_drain",
        "pressure_to_pt",
        "pressure_to_pi",
        "level_to_lt",
        "level_to_li",
        "pump_suction_pi",
        "pump_discharge_pi",
        "level_signal",
        "level_control_signal",
        "flow_signal",
        "flow_control_signal",
    } <= roles
    assert plan.status == "GREEN"
