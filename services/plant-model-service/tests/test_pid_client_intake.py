"""Source-set preflight, legend discovery and fail-closed drawing intake."""
from __future__ import annotations

import fitz
import pytest

from app.pid_client_intake import (
    preflight_pdf, extract_single_page,
)


def fixture_pdf():
    doc = fitz.open()
    page = doc.new_page(width=850, height=550)
    page.insert_text((50, 40), "DRAWING INDEX — PROJECT XYZ")
    page.insert_text((50, 75), "P&ID SHEET P-101")
    legend = doc.new_page(width=850, height=550)
    legend.insert_text((660, 420), "LEGENDS, ABBREVIATIONS AND SYMBOLS")
    legend.insert_text((65, 95), "CHECK VALVE")
    legend.insert_text((60, 150), "BALL VALVE")
    legend.insert_text((60, 190), "PUMP, CENTRIFUGAL")
    drawing = doc.new_page(width=850, height=550)
    drawing.insert_text((680, 440), "HEADWORKS P&ID")
    drawing.insert_text((690, 490), "P-101")
    sh = drawing.new_shape()
    sh.draw_circle(fitz.Point(170, 180), 30)
    sh.draw_rect(fitz.Rect(300, 110, 390, 230))
    sh.draw_line((200, 180), (300, 180))
    sh.finish(color=(0, 0, 0), width=2)
    sh.commit()
    drawing.insert_text((152, 246), "P-101")
    drawing.insert_text((324, 158), "V-101")
    contents = doc.tobytes()
    doc.close()
    return contents


def test_preflight_identifies_index_legends_and_pid_as_distinct_pages():
    output = preflight_pdf(fixture_pdf(), "Plant-PID-Set.pdf")
    assert output["page_count"] == 3
    roles = [p["role"] for p in output["pages"]]
    assert roles == ["index", "legend", "pid"], roles
    labels = {term["label"] for term in output["legend_terms"]}
    assert {"CHECK VALVE", "BALL VALVE", "PUMP, CENTRIFUGAL"} <= labels
    assert all(entry["source_pdf_sha256"] == output["source_sha256"]
               for entry in output["legend_terms"])
    assert output["pages"][2]["role_review_status"] == "unreviewed"
    assert output["pipeline_status"] == "preflight_only_no_graph"


def test_copy_only_selected_drawing_retains_source_geometry_and_text():
    original = fixture_pdf()
    page_data = extract_single_page(original, 3)
    assert page_data.startswith(b"%PDF-")
    with fitz.open(stream=page_data, filetype="pdf") as page_pdf:
        assert len(page_pdf) == 1
        assert page_pdf[0].rect.width == 850
        assert "V-101" in page_pdf[0].get_text()
        assert page_pdf[0].get_drawings()


def test_preflight_rejects_invalid_data():
    with pytest.raises(ValueError):
        preflight_pdf(b"not_pdf", "junk.pdf")
