"""Versioned, client-isolated P&ID symbol learning (no automatic engineering approval).

This small model is a HOG/shape nearest-exemplar *baseline*, not a foundation
model. Rights, source provenance, two-person QA and document-level evaluation
are mandatory gates. Model confidence is uncalibrated similarity, not probability.

Never copy a client's scanned glyphs or trained weights to a public repository.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


class ModelGateError(ValueError):
    pass


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_json_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
    tmp.replace(path)


def _record_image(root: Path, rec: dict) -> Path:
    reference = rec.get('image_path')
    if not isinstance(reference, str) or not reference or Path(reference).is_absolute():
        raise ModelGateError('Training image must be relative to private dataset root')
    source = (root / reference).resolve()
    if not source.is_relative_to(root.resolve()) or not source.is_file():
        raise ModelGateError('Image missing or outside isolated private dataset')
    if _digest(source.read_bytes()) != rec.get('image_sha256'):
        raise ModelGateError(f'Image SHA256 mismatch: {rec.get("record_id")}')
    return source


def _validate_review(rec: dict) -> None:
    required = ('record_id', 'concept_id', 'client_id', 'drawing_group', 'source_sha256')
    if not all(isinstance(rec.get(k), str) and rec[k].strip() for k in required):
        raise ModelGateError('Missing record ID/concept/client/drawing group/source hash')
    if len(rec['source_sha256']) != 64 or any(c not in '0123456789abcdef' for c in rec['source_sha256']):
        raise ModelGateError('Invalid source checksum')
    if rec.get('owner_approved') is not True or rec.get('independent_qa_passed') is not True:
        raise ModelGateError('Owner approval and separate engineering QA required')
    if rec.get('rights_confirmed_for_ml') is not True:
        raise ModelGateError('Source rights for ML training not confirmed')
    a, b = rec.get('owner_reviewer'), rec.get('independent_reviewer')
    if not a or not b or a.strip().casefold() == b.strip().casefold():
        raise ModelGateError('Distinct, traceable owner and independent reviewer IDs required')
    if rec.get('symbol_is_atomic') is not True or rec.get('quality_flags'):
        raise ModelGateError('Composite or flagged source cannot become a recognition template')


def shape_features(image: Path) -> list[float]:
    """Compact translation/scale normalised descriptor for black technical glyphs.

    This is an exploratory baseline; rotations need independent QA of orientation
    meaning before augmentation and prediction is always review-only.
    """
    import cv2
    im = cv2.imread(str(image), cv2.IMREAD_GRAYSCALE)
    if im is None or im.size == 0:
        raise ModelGateError('Unreadable image')
    ink = (im < 170).astype(np.uint8)
    ys, xs = np.where(ink)
    if len(xs) < 10:
        raise ModelGateError('Source glyph has insufficient visible ink')
    x0, x1 = xs.min(), xs.max() + 1
    y0, y1 = ys.min(), ys.max() + 1
    crop = ink[y0:y1, x0:x1] * 255
    h, w = crop.shape
    factor = 48.0 / max(h, w)
    w2 = max(1, int(round(w * factor)))
    h2 = max(1, int(round(h * factor)))
    resized = cv2.resize(crop, (w2, h2), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((64, 64), dtype=np.uint8)
    ox, oy = (64 - w2) // 2, (64 - h2) // 2
    canvas[oy:oy + h2, ox:ox + w2] = resized
    hog = cv2.HOGDescriptor((64, 64), (16, 16), (8, 8), (8, 8), 9)
    hvec = hog.compute(canvas).ravel().astype(np.float32)
    # Blend structural occupancy bins with HOG for simple drafting glyphs.
    small = cv2.resize(canvas, (12, 12), interpolation=cv2.INTER_AREA).flatten().astype(np.float32) / 255.0
    fv = np.concatenate((hvec, 0.65 * small))
    norm = float(np.linalg.norm(fv))
    if norm == 0:
        raise ModelGateError('Empty model descriptor')
    return (fv / norm).round(6).tolist()


def build_model(records: list[dict], dataset_root: Path, out_path: Path, *, client_id: str) -> dict:
    """Build an immutable new model version from reviewed, authorized images.

    Test images are NOT permitted in the training input. Every new piece of user
    feedback must pass approval and be included in a future versioned retrain.
    """
    if not client_id or not isinstance(records, list) or len(records) < 2:
        raise ModelGateError('Need client and at least two reviewed examples')
    seen: set[str] = set()
    items = []
    for rec in records:
        _validate_review(rec)
        if rec['client_id'] != client_id or rec['record_id'] in seen:
            raise ModelGateError('Cross-client record or duplicate record ID')
        if rec.get('dataset_split') != 'train':
            raise ModelGateError('Non-training/holdout example in training set')
        seen.add(rec['record_id'])
        src = _record_image(dataset_root, rec)
        items.append({'record_id':rec['record_id'], 'concept_id':rec['concept_id'],
                      'drawing_group':rec['drawing_group'], 'source_sha256':rec['source_sha256'],
                      'image_sha256':rec['image_sha256'], 'feature':shape_features(src)})
    if len({r['concept_id'] for r in items}) < 2:
        raise ModelGateError('Two or more approved concepts needed for classifier baseline')
    signature = {'schema':'pid-symbol-embedding-baseline-v1','client_id':client_id,
                 'algorithm':'normalised HOG + 12x12 occupancy nearest reviewed exemplar',
                 'status':'TRAINED_UNCALIBRATED_NOT_DEPLOYABLE',
                 'examples':sorted(items,key=lambda r:r['record_id']),
                 'requirements':{'holdout_by':'entire document/drawing group',
                                 'engineering_validation':'still required',
                                 'meaning_of_score':'cosine similarity, NOT calibrated probability'}}
    payload=json.dumps(signature,sort_keys=True,separators=(',',':')).encode()
    signature['version_sha256']=_digest(payload)
    _safe_json_write(out_path,signature)
    return {'version':signature['version_sha256'], 'examples':len(items),
            'concepts':len({r['concept_id'] for r in items}), 'status':signature['status']}


def predict_review_only(model: dict, image: Path, *, client_id: str,
                        min_similarity: float=0.90, min_margin: float=0.03, limit: int=3) -> dict:
    if client_id != model['client_id']:
        raise ModelGateError('Client model must not be queried with a different client')
    feat = np.asarray(shape_features(image), dtype=np.float32)
    scores = {}
    for example in model['examples']:
        cos = float(np.dot(feat,np.asarray(example['feature'],dtype=np.float32)))
        name=example['concept_id'];scores[name]=max(scores.get(name,-1.0),cos)
    ranked=sorted(scores.items(),key=lambda t:t[1],reverse=True)
    if not ranked:
        raise ModelGateError('Empty fitted model')
    best=ranked[0];second=ranked[1][1] if len(ranked)>1 else -1.0
    eligible = best[1]>=min_similarity and best[1]-second>=min_margin
    return {'status':'UNVERIFIED_MODEL_PROPOSAL' if eligible else 'UNKNOWN_REQUIRES_REVIEW',
            'proposed_concept_id':best[0] if eligible else None,
            'best_similarity_not_probability':round(best[1],5),
            'margin_to_second_concept':round(best[1]-second,5),
            'top_candidates':[{'concept_id':name,'similarity':round(score,5)} for name,score in ranked[:limit]],
            'model_version':model['version_sha256'],
            'graph_edge_approved':False,'ready_for_engineering_use':False}


def evaluate_document_holdout(model: dict, cases: list[dict], dataset_root: Path,
                              *, client_id: str) -> dict:
    """Never score a patch from the same whole drawing/document group as training."""
    train_groups={s['drawing_group'] for s in model['examples']}
    if not cases or any(c.get('drawing_group') in train_groups for c in cases):
        raise ModelGateError('Holdout must be independent whole source document/drawing groups')
    outcomes=[]
    for item in cases:
        _validate_review(item)
        if item['client_id'] != client_id or item.get('dataset_split') != 'test':
            raise ModelGateError('Invalid test case or cross-client source')
        pred=predict_review_only(model,_record_image(dataset_root,item),client_id=client_id)
        outcomes.append({'record_id':item['record_id'], 'actual_concept':item['concept_id'],
                         'proposed':pred['proposed_concept_id'], 'status':pred['status']})
    total=len(outcomes)
    accepted=sum(x['proposed'] is not None for x in outcomes)
    right=sum(x['proposed']==x['actual_concept'] and x['proposed'] is not None for x in outcomes)
    return {'source':'independently-reviewed whole-document holdout',
            'test_records':total,'correct':right,'proposed':accepted,
            'precision_when_proposed':round(right/accepted,4) if accepted else None,
            'coverage':round(accepted/total,4),
            'model_state':'EVALUATED_BUT_NOT_ENGINEERING_APPROVED',
            'notice':'Check class-wise metrics and real P&ID graph quality separately; no auto deployment.'}


def feedback_to_review_queue(proposal: dict, reviewer_decision: dict,
                             review_queue_file: Path) -> dict:
    """Store corrections, but NEVER auto-fine-tune or promote a proposed label."""
    if proposal.get('status') not in ('UNVERIFIED_MODEL_PROPOSAL','UNKNOWN_REQUIRES_REVIEW'):
        raise ModelGateError('Unsupported proposal state')
    if reviewer_decision.get('decision') not in ('confirm','correct','reject'):
        raise ModelGateError('Explicit reviewer decision required')
    record={'proposal':proposal, 'decision':reviewer_decision,
            'training_state':'QUARANTINED_AWAITING_SECOND_QA_AND_RIGHTS',
            'graph_ready':False}
    review_queue_file.parent.mkdir(parents=True,exist_ok=True)
    with review_queue_file.open('a',encoding='utf-8') as f:
        f.write(json.dumps(record,ensure_ascii=False)+'\n')
    return {'queued':True,'auto_trained':False,'training_state':record['training_state']}
