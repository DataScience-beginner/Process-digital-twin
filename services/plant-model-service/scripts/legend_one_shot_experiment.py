"""M6: genuine one-shot visual-symbol experiment using a real client legend.

ONE source training sheet only: P-002 (original PDF page 7).
INDEPENDENT test sheet: P-203 (original PDF page 12).
Fixed manually inspected crop boxes come from reviewing publisher PDF, not
from a model or target-sheet extraction result.

A few examples can train a template bank (instance-based/one-shot matcher),
NOT a robust industry-ready deep-learning object detector.

Produces:
 - symbol exemplar crops and identity metadata
 - candidate matches with source page and bounding boxes
 - original P&ID overlay annotated with detected candidates
 - *unverified* detections only; precision requires independently signed labels

The source engineering PDF is never copied into the report/output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import fitz
import numpy as np
from PIL import Image
from app.pid_legend_shape_model import train_circular_instrument, find_circular_instruments

SOURCE_URL = (
    "https://www.epa.gov/system/files/documents/2021-08/"
    "pahala-wwtp-design-build-drawings-2021-07-23.pdf"
)
LEGEND_PDF_PAGE = 7
TARGET_PDF_PAGE = 12
SCREEN_REFERENCE_SIZE = (1533.0, 992.0)
RENDER_WIDTH = 2000

# These coordinates are SOURCE-PAGE VISUAL ANNOTATIONS IN SCREEN REFERENCE
# SPACE, initially estimated by a human from the *real* P-002 legend.
# Crops need optical verification against actual rendered page before a final
# engineering accuracy claim; this is a controlled exploratory experiment.
ONE_SHOT_EXEMPLARS = [
    {"name": "gate_valve_open", "box": [884, 86, 911, 111],
     "label": "GATE VALVE — normally open", "family": "valve"},
    {"name": "ball_valve_open", "box": [884, 138, 913, 164],
     "label": "BALL VALVE — normally open", "family": "valve"},
    {"name": "globe_valve_open", "box": [884, 165, 913, 194],
     "label": "GLOBE VALVE — normally open", "family": "valve"},
    {"name": "single_variable_instrument", "box": [1005, 798, 1040, 835],
     "label": "SINGLE VARIABLE INSTRUMENT", "family": "instrument"},
]
SCALES = [0.48, 0.57, 0.67, 0.78, 0.91, 1.00, 1.05, 1.18, 1.32]
THRESHOLD = 0.63
MAX_PER_CLASS = 55
PROCESS_REGION = (0.065, 0.105, 0.887, 0.84)


def page_render(page: fitz.Page, width: int = RENDER_WIDTH) -> tuple[np.ndarray, float]:
    scale = width / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    image = np.frombuffer(pix.samples, np.uint8)
    image = image.reshape((pix.height, pix.width, pix.n))
    rgb = image[:, :, :3] if pix.n >= 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    return rgb.copy(), scale


def _template_box(raw_box, image_shape):
    h, w = image_shape[:2]
    sx, sy = w / SCREEN_REFERENCE_SIZE[0], h / SCREEN_REFERENCE_SIZE[1]
    x1,y1,x2,y2 = raw_box
    return (max(0, int(round(x1*sx))), max(0, int(round(y1*sy))),
            min(w, int(round(x2*sx))), min(h, int(round(y2*sy))))


def _edges(gray: np.ndarray) -> np.ndarray:
    blur=cv2.GaussianBlur(gray,(3,3),.5)
    return cv2.Canny(blur,50,140)


def _one_shot_bank(legend_rgb: np.ndarray, directory: Path) -> list[dict]:
    gray=cv2.cvtColor(legend_rgb,cv2.COLOR_RGB2GRAY)
    bank=[]
    for spec in ONE_SHOT_EXEMPLARS:
        x1,y1,x2,y2=_template_box(spec["box"],legend_rgb.shape)
        crop=gray[y1:y2,x1:x2].copy()
        if min(crop.shape)<9:
            raise ValueError("Unusable source legend crop "+spec["name"])
        edges=_edges(crop)
        if np.count_nonzero(edges)<8:
            raise ValueError("Empty source legend symbol "+spec["name"])
        cv2.imwrite(str(directory/f'legend_{spec["name"]}.png'),crop)
        bank.append({**spec,"pixel_box":[x1,y1,x2,y2],
                     "shape":list(crop.shape),"template":edges,
                     "edge_pixels":int(np.count_nonzero(edges))})
    return bank


def _run_match(template: np.ndarray, target_edges: np.ndarray,
               region: tuple[int,int,int,int]) -> list[dict]:
    x_min,y_min,x_max,y_max=region
    scan=target_edges[y_min:y_max,x_min:x_max]
    matches=[]
    for scale in SCALES:
        tw=max(8,int(round(template.shape[1]*scale)))
        th=max(8,int(round(template.shape[0]*scale)))
        if tw>scan.shape[1] or th>scan.shape[0]:
            continue
        changed=cv2.resize(template,(tw,th),interpolation=cv2.INTER_AREA)
        if np.count_nonzero(changed)<5:
            continue
        for turn,shape in ((0,changed),(90,cv2.rotate(changed,cv2.ROTATE_90_CLOCKWISE))):
            nh,nw=shape.shape
            if nh>scan.shape[0] or nw>scan.shape[1]:
                continue
            result=cv2.matchTemplate(scan,shape,cv2.TM_CCOEFF_NORMED)
            # Fixed score threshold and local maxima (no test label tuning).
            mask=(result>=THRESHOLD)&(result>=cv2.dilate(result,np.ones((7,7),np.uint8))-0.0001)
            ys,xs=np.nonzero(mask)
            for y,x in zip(ys,xs):
                matches.append({
                    "score":float(result[y,x]),"rotation_deg":turn,
                    "scale":scale,"bbox_px":[int(x+x_min),int(y+y_min),
                                           int(x+x_min+nw),int(y+y_min+nh)],
                })
    matches.sort(key=lambda v:v["score"],reverse=True)
    kept=[]
    for m in matches:
        box=m["bbox_px"]
        cx=(box[0]+box[2])/2
        cy=(box[1]+box[3])/2
        if any(math.hypot(cx-(v["bbox_px"][0]+v["bbox_px"][2])/2,
                          cy-(v["bbox_px"][1]+v["bbox_px"][3])/2)
               <max(9,min(box[2]-box[0],box[3]-box[1])*.75)
               for v in kept):
            continue
        kept.append(m)
        if len(kept)>=MAX_PER_CLASS:
            break
    return kept


def run_one_shot_reference(pdf_bytes: bytes, out: Path,
                           *, render_width: int = RENDER_WIDTH) -> dict[str,Any]:
    out.mkdir(parents=True,exist_ok=True)
    sha=hashlib.sha256(pdf_bytes).hexdigest()
    with fitz.open(stream=pdf_bytes,filetype="pdf") as pdf:
        if len(pdf)<TARGET_PDF_PAGE:
            raise ValueError("Pāhala original requires 12 pages")
        legend_img,legend_scale=page_render(pdf[LEGEND_PDF_PAGE-1],render_width)
        target_img,target_scale=page_render(pdf[TARGET_PDF_PAGE-1],render_width)
        legend_rect=pdf[LEGEND_PDF_PAGE-1].rect
        target_rect=pdf[TARGET_PDF_PAGE-1].rect
    cv2.imwrite(str(out/"legend_source_page_preview.png"),
                cv2.cvtColor(legend_img,cv2.COLOR_RGB2BGR))
    bank=_one_shot_bank(legend_img,out)
    source=cv2.cvtColor(target_img,cv2.COLOR_RGB2GRAY)
    edges=_edges(source)
    h,w=edges.shape
    region=(int(PROCESS_REGION[0]*w),int(PROCESS_REGION[1]*h),
            int(PROCESS_REGION[2]*w),int(PROCESS_REGION[3]*h))
    result_img=cv2.cvtColor(target_img.copy(),cv2.COLOR_RGB2BGR)
    color_by_class = [
        (5,65,224),(32,160,40),(255,85,40),(200,25,160)
    ]
    classes=[]
    all_matches=[]
    for class_index,exemplar in enumerate(bank):
        raw=_run_match(exemplar["template"],edges,region)
        predicted=[]
        for item in raw:
            x1,y1,x2,y2=item["bbox_px"]
            # Correct source-space evidence from target image pixels into
            # original PDF points and normalized page references.
            bbox_pdf=[round(x1/target_scale,2),round(y1/target_scale,2),
                      round(x2/target_scale,2),round(y2/target_scale,2)]
            det={
                "class":exemplar["name"],"label":exemplar["label"],
                "source_pdf_page":TARGET_PDF_PAGE,
                "source_pdf_sha256":sha,
                "bbox_pdf_points":bbox_pdf,
                "bbox_render_pixels":item["bbox_px"],
                "template_similarity":round(item["score"],5),
                "scale":item["scale"],"rotation_deg":item["rotation_deg"],
                "status":"unverified_visual_hypothesis",
            }
            predicted.append(det)
            all_matches.append(det)
        classes.append({
            "name":exemplar["name"],"family":exemplar["family"],
            "training_source_original_page":LEGEND_PDF_PAGE,
            "training_source_bbox_ref_image":exemplar["box"],
            "training_source_bbox_render_pixels":exemplar["pixel_box"],
            "edge_pixels":exemplar["edge_pixels"],
            "hypotheses_above_threshold":len(predicted),
            "top_5_scores":[x["template_similarity"] for x in predicted[:5]],
        })
        for det in predicted[:35]:
            x1,y1,x2,y2=det["bbox_render_pixels"]
            cv2.rectangle(result_img,(x1,y1),(x2,y2),
                          color_by_class[class_index],2)
    cv2.imwrite(str(out/"p203_legend_match_overlay.png"),result_img)
    # Follow-up model: a *separate* geometry descriptor learned directly
    # from the P-002 circular instrument example. It is insensitive to the
    # literal XXX or client loop number inside the actual instrument bubble.
    instrument_training_crop=cv2.imread(
        str(out/"legend_single_variable_instrument.png"),cv2.IMREAD_GRAYSCALE
    )
    trained_circle_model=train_circular_instrument(instrument_training_crop)
    (out/"trained_p002_instrument_geometry.json").write_text(
        json.dumps(trained_circle_model,indent=2)
    )
    circle_proposals=find_circular_instruments(source,trained_circle_model)
    instrument_overlay=cv2.cvtColor(target_img.copy(),cv2.COLOR_RGB2BGR)
    for j,item in enumerate(circle_proposals,1):
        cx,cy=item["center_px"]
        r=item["radius_px"]
        cv2.circle(instrument_overlay,(cx,cy),r,(0,130,10),2)
        cv2.rectangle(instrument_overlay,(cx-r,cy-r),(cx+r,cy+r),
                      (0,140,20),1)
        item["source_pdf_page"]=TARGET_PDF_PAGE
        item["source_pdf_sha256"]=sha
        item["bbox_pdf_points"]=[
            round(v/target_scale,2) for v in item["bbox_render_pixels"]
        ]
    cv2.imwrite(str(out/"p203_instrument_bubble_geometry_overlay.png"),
                instrument_overlay)
    # An exploratory visual spot-check was performed on P-203; these
    # locations are *not* independent held-out gold data, so do not report
    # them as measured precision or industrial recall.
    inspected_anchors_2000=[
        [547,209],[589,266],[631,266],[672,263],[757,263],
        [1182,266],[1225,264],[1352,267],[714,337],
        [1182,805],[1226,805],[1437,872],[1437,900],
    ]
    scale_anchor=render_width/2000
    anchors=[
        [int(x*scale_anchor),int(y*scale_anchor)]
        for x,y in inspected_anchors_2000
    ]
    spot_hits=sum(any(
        math.hypot(a[0]-item["center_px"][0],a[1]-item["center_px"][1])
        <=max(9,9*scale_anchor) for item in circle_proposals
    ) for a in anchors)
    # Include only candidate list, no copyrighted source page pixels in JSON.
    report={
        "experiment":"Pahala P-002 legend → P-203 actual P&ID",
        "source":SOURCE_URL,"source_sha256":sha,
        "training_source_page":LEGEND_PDF_PAGE,
        "test_source_page":TARGET_PDF_PAGE,
        "legend_page_pdf_dimensions":[legend_rect.width,legend_rect.height],
        "target_page_pdf_dimensions":[target_rect.width,target_rect.height],
        "one_shot_template_exemplars":len(bank),
        "template_matcher":"multi-scale 0/90-degree Canny edge normalized correlation",
        "selection_threshold":THRESHOLD,
        "target_search_region_fraction":PROCESS_REGION,
        "classes":classes,
        "total_hypotheses":len(all_matches),
        "detections":all_matches,
        "legend_calibrated_instrument_bubble_model":trained_circle_model,
        "instrument_bubble_candidates":circle_proposals,
        "instrument_bubble_count":len(circle_proposals),
        "manual_exploratory_spotcheck":{
            "num_p203_locations_chosen_after_viewing_test_page":len(anchors),
            "candidate_center_matches_within_9px":spot_hits,
            "not_independent_gold":True,
            "calibration_tuned_on_test_page":True,
            "do_not_report_as_precision_recall":True,
        },
        "precision_recall":"NOT MEASURED: engineer-verified bounding-box ground truth absent",
        "safety":"NO automatic digital plant publication",
        "critical_notes":[
            "Similarity score is NOT probability or calibrated ML confidence.",
            "One P&ID legend exemplar per class is not a trained deep detector.",
            "Manually estimated training crop coordinates must be inspected.",
            "Potential false positives must be independently reviewed.",
        ],
        "generated_files":[
            "p203_legend_match_overlay.png",
            "legend_source_page_preview.png",
            "p203_instrument_bubble_geometry_overlay.png",
            "trained_p002_instrument_geometry.json",
        ],
    }
    (out/"legend_one_shot_report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({
        "training_source_page":LEGEND_PDF_PAGE,
        "testing_source_page":TARGET_PDF_PAGE,
        "classes":[{"name":x["name"],"hits":x["hypotheses_above_threshold"],
                    "scores":x["top_5_scores"]} for x in classes],
        "total_hypotheses":len(all_matches),
        "instrument_bubble_candidates":len(circle_proposals),
        "manual_visual_spotcheck_not_independent":spot_hits,
        "accuracy":"not verified",
    },indent=2))
    return report


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--render-width",type=int,default=2000)
    args=parser.parse_args()
    if not 800 <= args.render_width <= 3500:
        parser.error("render width must be 800–3500 px")
    run_one_shot_reference(args.source.read_bytes(),args.out,
                           render_width=args.render_width)


if __name__=="__main__":
    main()
