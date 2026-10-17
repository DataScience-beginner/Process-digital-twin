"""Purely synthetic regression tests: never bundle restricted customer drawing."""
import pytest,fitz
from pid_geometry_relations import build_candidate_relationships

def _line(x0,y0,x1,y1):
    return {'color':(1,0,0),'items':[('l',fitz.Point(x0,y0),fitz.Point(x1,y1))]}

def _s(name,box):return {'id':name,'bbox_pdf_pt':box,'family':'synthetic'}

def test_two_symbols_shared_stroke_no_auto_edge():
    ret=build_candidate_relationships([_line(10,20,50,20)],[],[_s('A',[2,15,10,25]),_s('B',[50,15,58,25])])
    assert ret['statistics']['shared_run_relations']==1
    assert ret['shared_run_symbol_relationships'][0]['engineering_accepted'] is False
    assert ret['safety']['physical_graph_edges_approved']==0

def test_disjoint_source_lines_never_connected():
    ret=build_candidate_relationships([_line(10,20,30,20),_line(40,20,60,20)],[],[_s('A',[2,15,10,25]),_s('B',[60,15,68,25])])
    assert ret['statistics']['run_count']==2
    assert ret['statistics']['shared_run_relations']==0

def test_t_endpoint_to_interior_not_joined():
    res=build_candidate_relationships([_line(10,20,90,20),_line(50,20,50,70)],[],[])
    assert len(res['tee_candidates'])==1
    assert res['tee_candidates'][0]['connected'] is None
    assert len(res['cad_runs'])==2

def test_crossing_is_ambiguous():
    res=build_candidate_relationships([_line(10,20,90,20),_line(50,10,50,70)],[],[])
    assert len(res['unresolved_interior_crossings'])==1
    assert res['statistics']['run_count']==2

def test_native_line_tags_no_assignment():
    res=build_candidate_relationships([],[ (0.,0.,20.,10., '8"-P-45-0402-A1A') ],[])
    assert len(res['native_line_tags_unassigned'])==1
    assert res['native_line_tags_unassigned'][0]['pipe_association']=='UNVERIFIED'

def test_skips_black_and_short():
    dark=_line(10,20,90,20);dark['color']=(0,0,0)
    res=build_candidate_relationships([dark,_line(20,10,24,10)],[],[])
    assert res['statistics']['stroke_count']==0

def test_bbox_filter():
    res=build_candidate_relationships([_line(10,20,90,20)],[],[],drawing_bbox=(20,0,100,100))
    assert res['statistics']['stroke_count']==0
