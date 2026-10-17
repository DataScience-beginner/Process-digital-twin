"""Synthetic-only tests; no proprietary refinery names, glyphs or drawings."""
import copy
import pytest
from app.pid_visual_adjacency import apply_visual_route_review, AdjacencyReviewError

SHA='b'*64

def fixtures():
 graph={'source_sha256':SHA,'page':9,
  'nodes':[{'id':'pump1','status':'SOURCE_REVIEWED'}],
  'ports':[{'id':'port1','node_id':'pump1','status':'SOURCE_REVIEWED','source_attachment_pdf_pt':[10,20]}],
  'approved_edges':[]}
 route={'id':'r1','source_pdf_sha256':SHA,'source_pdf_page_1based':9,
  'begin_owner_approved_port_id':'port1', 'path_pdf_point_waypoints':[[10.1,20],[12,20],[14,40]],
  'next_component_id':'UNKNOWN_NOT_MATCHED'}
 event={'source_pdf_sha256':SHA,'source_pdf_page_1based':9,'reviewer_id':'personA',
  'reviewed_at':'2026-10-17','statement_verbatim':'I confirmed the traced route',
  'decisions':[{'route_id':'r1','decision':'CONFIRM_VISUAL_PATH'}]}
 return graph,[route],event

def test_accepts_visual_route_not_physical_graph():
 graph,routes,event=fixtures()
 out=apply_visual_route_review(graph,routes,event)
 assert out['owner_accepted_visual_path_count']==1
 assert out['engineer_accepted_physical_edges']==[]
 assert out['physical_graph_publish_ready'] is False
 assert out['reviewed_visual_path_evidence'][0]['terminal_semantic_class'].startswith('UNKNOWN')
 assert graph['approved_edges']==[]

def test_rejects_cross_document_review():
 a,b,c=fixtures();c['source_pdf_sha256']='c'*64
 with pytest.raises(AdjacencyReviewError,match='source'):apply_visual_route_review(a,b,c)

def test_rejects_unreviewed_port():
 a,b,c=fixtures();a['ports'][0]['status']='UNREVIEWED'
 with pytest.raises(AdjacencyReviewError,match='approved pump port'):apply_visual_route_review(a,b,c)

def test_rejects_spurious_path_start():
 a,b,c=fixtures();b[0]['path_pdf_point_waypoints'][0]=[90,90]
 with pytest.raises(AdjacencyReviewError,match='begin'):apply_visual_route_review(a,b,c)

def test_rejects_ambiguous_duplicate_decisions():
 a,b,c=fixtures();c['decisions']=[c['decisions'][0],c['decisions'][0]]
 with pytest.raises(AdjacencyReviewError):apply_visual_route_review(a,b,c)

def test_rejected_visual_route_does_not_create_edge():
 a,b,c=fixtures();c['decisions'][0]['decision']='REJECT_VISUAL_PATH'
 out=apply_visual_route_review(a,b,c)
 assert out['owner_accepted_visual_path_count']==0
 assert out['engineer_accepted_physical_edges']==[]

def test_rejects_malformed_geometry():
 a,b,c=fixtures();b[0]['path_pdf_point_waypoints'][1]=[float('nan'),20]
 with pytest.raises(AdjacencyReviewError,match='finite'):apply_visual_route_review(a,b,c)

def test_not_silently_promote_valve_classification():
 a,b,c=fixtures();b[0]['valve_type']='gate_valve'
 out=apply_visual_route_review(a,b,c)
 assert out['reviewed_visual_path_evidence'][0]['terminal_semantic_class']=='UNKNOWN_REQUIRES_SEPARATE_REVIEW'
 assert out['reviewed_visual_path_evidence'][0]['line_number']=='UNVERIFIED'
