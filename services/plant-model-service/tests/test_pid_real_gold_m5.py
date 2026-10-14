"""Real P&ID benchmark methodology and mixed text/image extraction guards."""
from __future__ import annotations

import pytest

from app.pid_mixed_ocr import _candidate
from scripts.evaluate_real_pid_gold import assess_annotated_evidence


def _token(word, box, confidence=86, line=(1,1,1)):
    return {"word":word, "bbox":box, "ocr_confidence":confidence, "line":line}


def test_stacked_instrument_loops_preserve_source_bbox():
    test=[
        _token("FIT", [102, 90, 131, 104]),
        _token("070186", [96, 111, 140, 128],line=(1,1,2)),
    ]
    c=_candidate("a"*64, 1, test,
                 "local_tesseract_mixed_vertical_stack")
    assert c["tag"]=="FIT-070186"
    assert c["source_method"]=="local_tesseract_mixed_vertical_stack"
    assert c["bbox"]==[96,90,140,128]
    assert c["review_status"]=="unreviewed"
    assert c["inferred_vertical_stack"]


def test_unmapped_client_loop_not_silently_invented_as_instrument_type():
    c=_candidate("b"*64, 2, [
        _token("FAL",[20,40,50,55]),
        _token("070186",[16,60,70,78]),
    ],"local_tesseract_mixed_vertical_stack")
    assert c is not None
    assert c["tag"]=="FAL-070186"
    assert c["category"]=="unmapped"
    assert c["object_type"] is None


def test_gold_metrics_remain_unavailable_without_independent_review():
    gold={"source_sha256":"a","tasks":[{
        "source_pdf_page":9,"source_pdf_sha256":"a",
        "annotation_status":"EMPTY_REQUIRES_INDEPENDENT_ENGINEER_GOLD",
        "annotator":None,"independent_second_reviewer":None,
        "confirmed_tags":[],"confirmed_connections":[],
    }]}
    predicted={"source_sha256":"a","sheets":[{
        "original_source_page":9,"tags":[{"tag":"PT-100"}],
        "connection_hypotheses":[],
    }]}
    score=assess_annotated_evidence(gold,predicted)
    assert score["verified_sheets_scored"]==0
    assert not score["industrial_accuracy_claim_allowed"]
    assert len(score["unverified_sheets"])==1


def test_gold_scored_only_after_two_distinct_engineer_reviews():
    gold={"source_sha256":"a","tasks":[{
        "source_pdf_page":9,"source_pdf_sha256":"a",
        "annotation_status":"independently_verified",
        "annotator":"process-eng-1",
        "independent_second_reviewer":"instrument-eng-2",
        "confirmed_tags":[{"tag":"PT-100"},{"tag":"FCV-100"}],
        "confirmed_connections":[{
            "source_tag":"PT-100","target_tag":"FCV-100"
        }],
    }]}
    predicted={"source_sha256":"a","sheets":[{
        "original_source_page":9,
        "tags":[{"tag":"PT-100"},{"tag":"PT-101"}],
        "connection_hypotheses":[],
    }]}
    score=assess_annotated_evidence(gold,predicted)
    assert score["results"][0]["tag_identity"]["TP"]==1
    assert score["results"][0]["tag_identity"]["FP"]==1
    assert score["results"][0]["tag_identity"]["FN"]==1
    assert score["results"][0]["undirected_connection_identity"]["FN"]==1
    assert not score["industrial_accuracy_claim_allowed"]


def test_cannot_assess_different_source_revisions():
    with pytest.raises(ValueError,match="do not match"):
        assess_annotated_evidence({"source_sha256":"x","tasks":[]},
                                  {"source_sha256":"y","sheets":[]})
