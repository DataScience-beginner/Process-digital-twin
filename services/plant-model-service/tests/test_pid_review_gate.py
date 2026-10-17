"""All tests are synthetic; no restricted engineering drawings or glyphs."""
import pytest
from app.pid_review_gate import check_sheet_index,propose_local_pump_review,record_markup_decisions,accept_verified_route

HASH='e'*64

def example():
    return propose_local_pump_review(HASH,1,[{'id':'P-A','tag_proposal':'TEST-A','center':[10,10]}, {'id':'P-B','tag_proposal':'TEST-B','center':[50,10]}])

def test_index_does_not_confuse_typical_details_with_atomic_symbols():
    r=[{'pdf_page':1,'role':'INDEX','source_pdf_sha256':HASH},{'pdf_page':2,'role':'DETAIL_STANDARD','source_pdf_sha256':HASH},{'pdf_page':3,'role':'SYMBOL_LEGEND','source_pdf_sha256':HASH}]
    s=check_sheet_index(r,{1,2,3});assert s['role_counts']['SYMBOL_LEGEND']==1 and s['glyph_library_ready'] is False
    with pytest.raises(ValueError):check_sheet_index(r,{1,2,3,4})

def test_review_starts_with_zero_nodes_and_edges():
    d=example();assert len(d['nodes'])==2 and len(d['ports'])==4
    assert len(d['approved_edges'])==0 and len(d['approved_nodes'])==0

def test_markup_can_confirm_node_but_not_implicitly_connect_pipes():
    d=example();dec={'schema':'pid-review-decisions-v1','source':{'source_sha256':HASH},'reviewer':'eng1','reviewed_at':'2026-10-17','decisions':[{'id':'P-A','decision':'CONFIRM'},{'id':'P-A-left','decision':'CONFIRM'}]}
    ans=record_markup_decisions(d,dec)
    assert ans['approved_nodes']==['P-A'] and ans['approved_edges']==[]
    dec['source']['source_sha256']='f'*64
    with pytest.raises(ValueError): record_markup_decisions(d,dec)

def test_accept_route_fail_closed_without_junction_and_second_reviewer():
    d=example();dec={'schema':'pid-review-decisions-v1','source':{'source_sha256':HASH},'reviewer':'eng1','reviewed_at':'2026-10-17','decisions':[{'id':'P-A','decision':'CONFIRM'},{'id':'P-B','decision':'CONFIRM'}]}
    r=record_markup_decisions(d,dec)
    pipe={'id':'E1','source_sha256':HASH,'pdf_page':1,'source_node':'P-A','target_node':'P-B','from_port_id':'P-A-right','to_port_id':'P-B-left','source_stroke_ids':['test-line1'],'process_line_confirmed':True,'tee_crossing_review_completed':True,'route_reviewer':'eng1','independent_reviewer':'eng2','route_reviewed_at':'2026-10-17'}
    assert accept_verified_route(r,pipe)['approved_edges'][0]['status']=='ENGINEERING_ACCEPTED'
    pipe['independent_reviewer']='eng1'
    with pytest.raises(ValueError):accept_verified_route(r,pipe)
    pipe['independent_reviewer']='eng2';pipe['tee_crossing_review_completed']=False
    with pytest.raises(ValueError):accept_verified_route(r,pipe)
