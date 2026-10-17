"""Synthetic-only tests.  No copyrighted client glyphs or docs in public GitHub."""
import io
import json

import fitz
import pytest

from app.pid_legend_library import create_inventory, compile_library, propose_glyph_rows
from scripts.build_pid_legend_library import _pages


def fixture_pdf():
    doc=fitz.open()
    p=doc.new_page(width=400,height=300)
    p.draw_line((35,65),(95,65),color=(0,0,0),width=2)
    p.draw_line((55,45),(75,85),color=(0,0,0),width=2)
    p.draw_line((75,45),(55,85),color=(0,0,0),width=2)
    p.insert_text((135,69),"SYNTHETIC VALVE - normally open",fontsize=11)
    other=doc.new_page(width=400,height=300)
    other.insert_text((35,60),"TEST NOTES",fontsize=12)
    raw=doc.tobytes();doc.close();return raw


def manifest(raw):
    m=create_inventory(raw,[1,2],source_name="TEST ONLY.pdf")
    m["pages"][0].update(role="symbol_legend",reviewed_complete=True,expected_symbol_items=1)
    m["pages"][1].update(role="abbreviation",reviewed_complete=True,expected_symbol_items=0)
    m["symbols"]=[{"id":"VALVE_001", "page_1based":1,
        "glyph_bbox_pdf_pt":[30,35,105,95],"label_bbox_pdf_pt":[130,48,390,82],
        "label_verbatim":"SYNTHETIC VALVE - normally open","class_code":"valve_open",
        "review_status":"needs_review"}]
    return m


def test_inventory_rejects_duplicated_or_out_of_range_pages():
    raw=fixture_pdf()
    assert len(create_inventory(raw,[1,2],source_name="f.pdf")["pages"])==2
    with pytest.raises(ValueError):create_inventory(raw,[1,1],source_name="f.pdf")
    with pytest.raises(ValueError):create_inventory(raw,[3],source_name="f.pdf")


def test_wrong_pdf_fails_closed(tmp_path):
    m=manifest(fixture_pdf());changed=fixture_pdf()+b"edited"
    with pytest.raises(ValueError,match="checksum"): compile_library(changed,m,tmp_path)


def test_unreviewed_never_ready(tmp_path):
    raw=fixture_pdf();m=manifest(raw)
    s=compile_library(raw,m,tmp_path)
    assert s["library_readiness"]=="NOT_READY"
    assert s["glyphs_reviewed_and_approved"]==0
    assert (tmp_path/"source_crops/VALVE_001_label.png").exists()
    assert json.loads((tmp_path/"approved.json").read_text())==[]


def test_missing_second_reviewer_refused(tmp_path):
    raw=fixture_pdf();m=manifest(raw)
    m["symbols"][0].update(review_status="approved",glyph_reviewer="engineer_A",label_reviewer="engineer_A",glyph_isolated_confirmed=True,label_paired_confirmed=True)
    with pytest.raises(ValueError,match="distinct reviewers"):compile_library(raw,m,tmp_path)


def test_approved_after_distinct_reviews(tmp_path):
    raw=fixture_pdf();m=manifest(raw)
    m["symbols"][0].update(review_status="approved",glyph_reviewer="engineer_A",label_reviewer="engineer_B",glyph_isolated_confirmed=True,label_paired_confirmed=True)
    s=compile_library(raw,m,tmp_path)
    assert s["glyphs_reviewed_and_approved"]==1
    assert s["pages_approved_complete"]==2
    assert s["library_readiness"]=="READY"
    assert json.loads((tmp_path/"approved.json").read_text())[0]["source_sha256"]==m["source_sha256"]


def test_missing_page_review_blocks_ready(tmp_path):
    raw=fixture_pdf();m=manifest(raw)
    m["symbols"][0].update(review_status="approved",glyph_reviewer="engineer_A",label_reviewer="engineer_B",glyph_isolated_confirmed=True,label_paired_confirmed=True)
    m["pages"][1]["reviewed_complete"]=False
    assert compile_library(raw,m,tmp_path)["library_readiness"]=="NOT_READY"


def test_invalid_crop_or_wrong_page_fail(tmp_path):
    raw=fixture_pdf();m=manifest(raw);m["symbols"][0]["glyph_bbox_pdf_pt"]=[350,30,450,80]
    with pytest.raises(ValueError,match="outside"):compile_library(raw,m,tmp_path)
    m=manifest(raw);m["symbols"][0]["label_bbox_pdf_pt"]=[45,45,80,72]
    with pytest.raises(ValueError,match="overlaps"):compile_library(raw,m,tmp_path)
    m=manifest(raw);m["symbols"][0]["page_1based"]=9
    with pytest.raises(ValueError,match="unregistered"):compile_library(raw,m,tmp_path)


def test_full_range_input():
    assert _pages("2,4-6")==[2,4,5,6]
    with pytest.raises(ValueError):_pages("5-3")


def test_ink_row_proposals_are_not_auto_labeled_or_approved():
    pytest.importorskip("numpy")
    raw=fixture_pdf()
    result=propose_glyph_rows(raw,1,(30,105),(130,390),(30,100),id_prefix="TEST")
    assert len(result)>=1
    assert all(x["review_status"]=="needs_review" and not x["label_verbatim"] for x in result)
    assert all(x["glyph_bbox_pdf_pt"][0]==30 for x in result)

def test_row_proposer_rejects_mixed_columns():
    pytest.importorskip("numpy")
    with pytest.raises(ValueError,match="overlap"):
        propose_glyph_rows(fixture_pdf(),1,(30,130),(105,390),(30,100))


def test_review_html_is_offline_and_does_not_self_approve(tmp_path):
    from scripts.build_pid_legend_review_html import build_html
    raw=fixture_pdf();m=manifest(raw)
    compile_library(raw,m,tmp_path)
    s=build_html(m,tmp_path)
    assert "data:image/png;base64," in s
    assert "NO" not in s[:20]  # HTML, not a status write
    assert '"review_status": "needs_review"' in s
    assert "Export annotated inventory JSON" in s
    assert "https://" not in s  # no CDNs/external assets


def test_approved_requires_explicit_class_code(tmp_path):
    raw=fixture_pdf(); m=manifest(raw)
    m["symbols"][0].update(review_status="approved",class_code="",
        glyph_reviewer="engineer_A",label_reviewer="engineer_B",
        glyph_isolated_confirmed=True,label_paired_confirmed=True)
    with pytest.raises(ValueError,match="nonempty class"):
        compile_library(raw,m,tmp_path)


def test_owner_mapping_approval_is_preserved_but_not_full_gate(tmp_path):
    raw = fixture_pdf()
    m = manifest(raw)
    m["symbols"][0]["owner_mapping_approval"] = {
        "status": "approved", "reviewer_role": "project_owner",
        "review_date": "2026-10-17", "evidence": "explicit user message",
    }
    summary = compile_library(raw, m, tmp_path)
    assert summary["glyphs_project_owner_approved"] == 1
    assert summary["glyphs_reviewed_and_approved"] == 0
    assert summary["library_readiness"] == "NOT_READY"
    item = json.loads((tmp_path / "worklist.json").read_text())[0]
    assert item["owner_mapping_approval"]["status"] == "approved"


def test_owner_approval_requires_traceable_evidence(tmp_path):
    raw = fixture_pdf()
    m = manifest(raw)
    m["symbols"][0]["owner_mapping_approval"] = {
        "status": "approved", "reviewer_role": "project_owner",
        "review_date": "2026-10-17", "evidence": "",
    }
    with pytest.raises(ValueError, match="owner mapping approval evidence"):
        compile_library(raw, m, tmp_path)
