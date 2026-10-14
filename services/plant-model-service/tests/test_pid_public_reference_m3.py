"""Reference DEXPI XML inspection does not confuse semantic truth with OCR evidence."""
import pytest

from scripts.benchmark_public_dexpi import summarize_dexpi_xml, get_public_file


def test_minimal_dexpi_structural_summary():
    xml=b'''<?xml version="1.0"?>
    <Model name="Process Reference" xmlns="https://data.dexpi.org/models/2.0.0">
      <Object id="pump_101" type="Plant/Equipment.CentrifugalPump"/>
      <Object id="valve_101" type="Plant/Piping.ControlValve"/>
    </Model>'''
    report=summarize_dexpi_xml(xml)
    assert report["root"]=="Model"
    assert report["object_count"]==2
    assert report["type_counts"]["Plant/Equipment.CentrifugalPump"]==1
    assert report["image_alignment"]=="not_performed"
    assert report["standard_semantic_reference_only"] is True


def test_defensive_xml_parser_rejects_doctype():
    attack=b'''<!DOCTYPE foo [<!ENTITY ext SYSTEM "file:///etc/passwd">]>
    <Model><Object id="foo" name="&ext;"/></Model>'''
    with pytest.raises(ValueError,match="DTD"):
        summarize_dexpi_xml(attack)


def test_external_fetch_rejects_unpinned_hosts():
    with pytest.raises(ValueError,match="pinned"):
        get_public_file("https://example.com/fake.xml")
