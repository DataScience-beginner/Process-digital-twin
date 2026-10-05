from app.config_match_renderer import render_configuration_match_html
from app.config_matcher import MatchStatus, match_configuration
from app.simulation import publish_demo_simulation


def test_match_view_shows_exact_configuration_and_modules():
    publication = publish_demo_simulation("CASE-NORMAL")
    result = match_configuration(
        publication,
        design_basis_facts={"pump_minimum_flow_required": True},
    )
    html = render_configuration_match_html(publication, result)

    assert result.status == MatchStatus.EXACT
    assert "EXACT" in html
    assert "VESSEL_TO_PUMP_STANDARD_V1" in html
    assert "VESSEL_LEVEL_CONTROL_01" in html
    assert "PUMP_MIN_FLOW_STANDARD_V1" in html
    assert "S-102" in html


def test_match_view_states_that_pid_is_not_yet_instantiated():
    publication = publish_demo_simulation("CASE-NORMAL")
    result = match_configuration(
        publication,
        design_basis_facts={"pump_minimum_flow_required": True},
    )
    html = render_configuration_match_html(publication, result)

    assert "does not yet instantiate P&ID valves" in html
