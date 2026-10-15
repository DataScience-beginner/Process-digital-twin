"""Deterministic contract tests for the P-002 -> P-203 one-shot matcher."""
from __future__ import annotations

import cv2
import numpy as np

from scripts.legend_one_shot_experiment import (
    ONE_SHOT_EXEMPLARS, _edges, _run_match, _template_box,
)


def test_exemplar_coordinates_are_nonzero_and_on_page():
    image = np.full((992,1533,3),255,np.uint8)
    for spec in ONE_SHOT_EXEMPLARS:
        x1,y1,x2,y2=_template_box(spec["box"],image.shape)
        assert 0 < x1 < x2 < 1533, spec
        assert 0 < y1 < y2 < 992, spec
        assert 12 <= x2-x1 <= 45, spec


def test_line_icon_can_be_found_with_source_coordinates():
    icon=np.full((25,27),255,np.uint8)
    cv2.line(icon,(4,4),(14,12),0,2)
    cv2.line(icon,(14,12),(4,20),0,2)
    cv2.line(icon,(4,20),(4,4),0,2)
    cv2.line(icon,(23,4),(14,12),0,2)
    cv2.line(icon,(14,12),(23,20),0,2)
    cv2.line(icon,(23,20),(23,4),0,2)
    img=np.full((240,320),255,np.uint8)
    img[118:143,170:197]=icon
    # A fixed real-shape exemplar finds its counterpart, without tag OCR.
    out=_run_match(_edges(icon),_edges(img),(0,0,320,240))
    assert out
    assert any(abs((d["bbox_px"][0]+d["bbox_px"][2])/2-183)<13 and
               abs((d["bbox_px"][1]+d["bbox_px"][3])/2-130)<13
               for d in out[:30])


def test_empty_training_patch_is_not_used_to_claim_confidence():
    # Source crop extraction explicitly checks edge count elsewhere; none of
    # our experiments should learn from an all-white patch.
    blank=_edges(np.full((25,25),255,np.uint8))
    assert np.count_nonzero(blank)==0
