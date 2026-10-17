"""Only synthetic PDF examples; no client material in this test suite."""
from __future__ import annotations
import hashlib
from pathlib import Path
import fitz
import pytest
from scripts.pid_legend_review_atlas import build_atlas, validate_registry

def sample():
    pdf=fitz.open();p=pdf.new_page(width=250,height=160)
    p.draw_line((15,50),(48,50),width=2)
    p.insert_text((80,55),'TEST SYMBOL ONLY')
    raw=pdf.tobytes();pdf.close()
    return raw,{'source_sha256':hashlib.sha256(raw).hexdigest(),'pages':[1],
                'registry':[{'id':'ICON_1','pdf_page':1,'label_candidate':'TEST SYMBOL ONLY',
                             'image_bbox_pdf_pt':[12,42,55,62],'label_bbox_pdf_pt':[78,40,175,68],
                             'owner_mapping_approved':False,'kind':'glyph_label_pair'}]}

def test_registry_full_page_coverage_synthetic():
    raw,r=sample();assert len(validate_registry(raw,r))==1

def test_wrong_source_rejected():
    raw,r=sample();r['source_sha256']='other'
    with pytest.raises(ValueError,match='fingerprint'):validate_registry(raw,r)

def test_rejects_bad_bounds():
    raw,r=sample();r['registry'][0]['image_bbox_pdf_pt']=[15,50,900,80]
    with pytest.raises(ValueError,match='outside'):validate_registry(raw,r)

def test_rejects_duplicate_item():
    raw,r=sample();r['registry'].append(dict(r['registry'][0]))
    with pytest.raises(ValueError,match='Duplicate'):validate_registry(raw,r)

def test_export_never_grants_approval(tmp_path):
    raw,r=sample();s=build_atlas(raw,r,tmp_path)
    assert s['source_pages']==1 and s['source_candidates']==1
    assert s['automatically_approved']==0 and not s['overall_library_ready']
    assert 'data:image/png;base64,' in (tmp_path/'Offline_Legend_Review.html').read_text()
