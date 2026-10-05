from app.configurations import demo_integrated_configuration_model


def test_integrated_model_has_two_modules():
    model = demo_integrated_configuration_model()
    templates = {m.template for m in model.modules}
    assert "VERTICAL_SEPARATOR_STANDARD_WITH_LEVEL_CONTROL_AND_RELIEF" in templates
    assert "CENTRIFUGAL_PUMP_STANDARD_WITH_MIN_FLOW" in templates


def test_vessel_module_contains_control_relief_and_nozzle_nodes():
    model = demo_integrated_configuration_model()
    tags = {obj.tag for obj in model.objects}
    expected = {
        "PT-101", "PI-101", "LT-101", "LI-101", "LIC-101",
        "LCV-101", "PSV-101", "V-101/N-LIQ", "V-101/N-PSV",
    }
    assert expected <= tags


def test_level_control_loop_is_explicit():
    model = demo_integrated_configuration_model()
    signal_ids = {c.id for c in model.connections if c.kind == "signal"}
    assert {"S-LEVEL-01", "S-LEVEL-02"} <= signal_ids


def test_psv_protects_vessel():
    model = demo_integrated_configuration_model()
    matches = [
        a for a in model.associations
        if a.subject_id == "VLV-PSV101"
        and a.relationship == "protects"
        and a.target_id == "EQ-V101"
    ]
    assert len(matches) == 1


def test_vessel_liquid_outlet_reaches_pump_through_nozzle_nodes():
    model = demo_integrated_configuration_model()
    path = {(c.source.object_id, c.target.object_id) for c in model.connections}
    assert ("NOZ-V101-LIQ", "VLV-LCV101") in path
    assert ("VLV-LCV101", "VLV-XV101") in path
    assert ("VLV-XV101", "NOZ-P101-SUC") in path
    assert ("NOZ-P101-DIS", "JUNC-P101-DIS") in path
