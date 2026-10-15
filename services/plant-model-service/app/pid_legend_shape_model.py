"""Legend-conditioned structural detector for *circular* instrument bubbles.

This is deliberately a small data-driven feature detector, NOT a YOLO/CNN
model. It calibrates the expected ring radius using an actual P-002 legend
exemplar and finds corresponding circular rings on actual P-203. Lettering
inside the ring is allowed to vary.

NOTE: Hough-vote cutoff below was explored using P-203 itself and is NOT a
hold-out accuracy estimate. A separate drawing is required for validation.
"""
from __future__ import annotations

import cv2
import numpy as np

HOUGH_VOTE_THRESHOLD = 20
SOURCE_SCOPE = (0.175, 0.12, 0.75, 0.78)


def train_circular_instrument(legend_gray: np.ndarray) -> dict:
    """Learn one template's circular geometry without hard-coding its radius."""
    h,w=legend_gray.shape
    candidates=cv2.HoughCircles(
        cv2.medianBlur(legend_gray,3),cv2.HOUGH_GRADIENT,
        dp=1.0,minDist=12,param1=100,param2=12,
        minRadius=max(5,int(min(h,w)*.19)),
        maxRadius=max(8,int(min(h,w)*.52)),
    )
    if candidates is None:
        raise ValueError("Legend crop does not contain a detectable instrument ring")
    bubbles=candidates[0]
    cx,cy=(w/2,h/2)
    sorted_circles=sorted(bubbles,key=lambda c: (
        (float(c[0])-cx)**2+(float(c[1])-cy)**2
    ))
    x,y,r=sorted_circles[0]
    if not (min(h,w)*.18<=r<=min(h,w)*.53):
        raise ValueError("Unexpected legend ring radius")
    return {
        "family":"instrument",
        "symbol":"single_variable_instrument_circle",
        "template_radius_px":round(float(r),2),
        "template_center_px":[round(float(x),2),round(float(y),2)],
        "radius_scale_range":[.62,1.50],
        "algorithm":"legend-calibrated Hough circle geometry",
        "trained_with_actual_legend":True,
        "trained_model_type":"one_shot_analytical_feature_model",
        "trained_neural_network":False,
    }


def find_circular_instruments(target_gray: np.ndarray,
                              legend_model: dict) -> list[dict]:
    h,w=target_gray.shape
    src_r=legend_model["template_radius_px"]
    min_r=int(round(src_r*legend_model["radius_scale_range"][0]))
    max_r=int(round(src_r*legend_model["radius_scale_range"][1]))
    if min_r<5 or max_r<=min_r:
        raise ValueError("Invalid source-calibrated search radius")
    detected=cv2.HoughCircles(
        cv2.medianBlur(target_gray,3),
        cv2.HOUGH_GRADIENT,dp=1.1,minDist=18,
        param1=120,param2=HOUGH_VOTE_THRESHOLD,
        minRadius=min_r,maxRadius=max_r,
    )
    if detected is None:
        return []
    x0,y0,x1,y1=SOURCE_SCOPE
    results=[]
    for cx,cy,r in np.rint(detected[0]).astype(int):
        if not (x0*w<=cx<=x1*w and y0*h<=cy<=y1*h):
            continue
        results.append({
            "class":"instrument_bubble_candidate",
            "center_px":[int(cx),int(cy)],
            "radius_px":int(r),
            "bbox_render_pixels":[int(cx-r),int(cy-r),int(cx+r),int(cy+r)],
            "classification_source":"legend_circular_shape_geometry",
            "confidence":"uncalibrated_candidate",
            "status":"unreviewed",
        })
    return sorted(results,key=lambda c:(c["center_px"][1],c["center_px"][0]))
