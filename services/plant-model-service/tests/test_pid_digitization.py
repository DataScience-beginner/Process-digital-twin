"""Tests for the conservative first stage of legacy P&ID digitization."""
import fitz
import pytest

from app.models import PlantModel
from app.pid_digitization import accepted_plant_draft, extract_pid_pdf


def make_pdf(tags="V-101 P-101 FCV-101 PSV-101 PT 101 FT-101"):
    document = fitz.open()
    page = document.new_page(width=800, height=400)
    if tags:
        page.insert_text((70, 50), tags)
    content = document.tobytes()
    document.close()
    return content


def test_extract_pdf_tag_candidates_with_source_coordinates():
    result = extract_pid_pdf(make_pdf())
    tags = {c["tag"] for c in result["candidates"]}
    assert {"V-101", "P-101", "FCV-101", "PSV-101", "PT-101", "FT-101"} <= tags
    assert result["topology_status"] == "not_reconstructed"
    assert result["review_required"] is True
    assert all(len(c["bbox"]) == 4 for c in result["candidates"])


def test_accepted_tags_produce_valid_but_unconnected_plant_draft():
    result = extract_pid_pdf(make_pdf())
    for candidate in result["candidates"]:
        candidate["review_status"] = "accepted"
    draft = accepted_plant_draft("PID-TEST", "BDEP-DEMO-004", result["candidates"])
    assert draft["publish_ready"] is False
    assert draft["plant_model"]["connections"] == []
    model = PlantModel.model_validate(draft["plant_model"])
    assert len(model.objects) >= 6


def test_no_text_page_warns_that_ocr_is_not_available():
    result = extract_pid_pdf(make_pdf(""))
    assert not result["candidates"]
    assert any("OCR" in warning for warning in result["warnings"])


def test_invalid_file_is_rejected():
    with pytest.raises(ValueError):
        extract_pid_pdf(b"not a PDF")
