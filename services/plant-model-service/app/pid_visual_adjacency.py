"""Human-reviewed *visual* P&ID route layer; never publish physical graph edges.

This generic component contains no customer drawings, valve classifications,
line numbers, image crops, or private coordinates. Human confirmation of a
source-visible path is NOT a complete engineering port-to-port topology review.
"""
from __future__ import annotations

from copy import deepcopy
from math import hypot, isfinite

class AdjacencyReviewError(ValueError):
    pass


def _xy(p):
    if not isinstance(p, (list, tuple)) or len(p) != 2:
        raise AdjacencyReviewError('Expected a 2-D PDF-point coordinate')
    if not all(isinstance(c,(int,float)) and not isinstance(c,bool) and isfinite(c) for c in p):
        raise AdjacencyReviewError('Coordinates must be finite numbers')
    return p


def apply_visual_route_review(approved_source_graph: dict, candidates: list[dict], event: dict, *, tolerance_pt: float = 8.0) -> dict:
    """Accept visual line-path evidence while keeping engineering-edge gate closed.

    Candidate fields: id, source_pdf_sha256, source_pdf_page_1based,
    begin_owner_approved_port_id, path_pdf_point_waypoints,
    next_component_id.  Decisions are explicit per-route CONFIRM/REJECT.

    Approval attests only that a path follows the displayed image toward a
    feature at the end. It does not establish correct line type, valve class,
    line tag, tee/crossing, endpoints, pressure boundary or process direction.
    """
    if not (0 < tolerance_pt <= 30):
        raise AdjacencyReviewError('Invalid coordinate tolerance')
    src=approved_source_graph.get('source_sha256')
    page=approved_source_graph.get('page')
    if not isinstance(src,str) or len(src) != 64 or not isinstance(page,int) or page < 1:
        raise AdjacencyReviewError('Need a source-hashed approved local graph')
    if event.get('source_pdf_sha256') != src or event.get('source_pdf_page_1based') != page:
        raise AdjacencyReviewError('Review event does not match exact source PDF page')
    if not event.get('reviewer_id') or not event.get('reviewed_at') or not event.get('statement_verbatim'):
        raise AdjacencyReviewError('Explicit dated reviewer statement required')
    ports={p['id']:p for p in approved_source_graph.get('ports',[]) if p.get('status')=='SOURCE_REVIEWED'}
    nodes={p['id']:p for p in approved_source_graph.get('nodes',[]) if p.get('status')=='SOURCE_REVIEWED'}
    decisions=event.get('decisions')
    if not isinstance(decisions,list) or len(decisions) != len(candidates):
        raise AdjacencyReviewError('One explicit decision per route required')
    by_dec={}
    for d in decisions:
        if not isinstance(d,dict) or not d.get('route_id') or d['route_id'] in by_dec:
            raise AdjacencyReviewError('Duplicate or invalid route review decision')
        if d.get('decision') not in ('CONFIRM_VISUAL_PATH','REJECT_VISUAL_PATH'):
            raise AdjacencyReviewError('Unsupported visual route decision')
        by_dec[d['route_id']]=d['decision']
    seen=set();results=[]
    for candidate in candidates:
        cid=candidate.get('id')
        if not isinstance(cid,str) or not cid or cid in seen or cid not in by_dec:
            raise AdjacencyReviewError('Missing or duplicate candidate/decision ID')
        seen.add(cid)
        if (candidate.get('source_pdf_sha256') != src or candidate.get('source_pdf_page_1based') != page):
            raise AdjacencyReviewError('Route source mismatch')
        port=ports.get(candidate.get('begin_owner_approved_port_id'))
        if not port or port.get('node_id') not in nodes:
            raise AdjacencyReviewError('Route not anchored to owner-approved pump port')
        start=port.get('source_attachment_pdf_pt')
        waypoints=candidate.get('path_pdf_point_waypoints')
        if not isinstance(waypoints,list) or len(waypoints)<2 or len(waypoints)>100:
            raise AdjacencyReviewError('Route requires bounded ordered path')
        for p in waypoints:
            _xy(p)
        _xy(start)
        if hypot(waypoints[0][0]-start[0],waypoints[0][1]-start[1])>tolerance_pt:
            raise AdjacencyReviewError('Route does not begin at accepted source port')
        result={
          'id':cid, 'source_pdf_sha256':src,'source_pdf_page_1based':page,
          'from_reviewed_equipment_node_id':port['node_id'],
          'from_reviewed_port_id':port['id'],
          'path_pdf_point_waypoints':deepcopy(waypoints),
          'terminal_position_pdf_pt':deepcopy(waypoints[-1]),
          'terminal_semantic_class':'UNKNOWN_REQUIRES_SEPARATE_REVIEW',
          'line_number':'UNVERIFIED','line_type':'UNVERIFIED','process_direction':'UNVERIFIED',
          'source_stroke_chain':'UNVERIFIED','tee_crossing_classification':'UNVERIFIED',
          'visual_route_review': 'OWNER_CONFIRMED' if by_dec[cid]=='CONFIRM_VISUAL_PATH' else 'REJECTED',
          'reviewer_id':event['reviewer_id'],'reviewed_at':event['reviewed_at'],
          'engineering_physical_graph_edge_approved':False,
        }
        results.append(result)
    if set(by_dec) != seen:
        raise AdjacencyReviewError('Orphaned decisions')
    approved=[r for r in results if r['visual_route_review']=='OWNER_CONFIRMED']
    return {
      'schema':'pid-owner-reviewed-visual-adjacency-v1',
      'source_sha256':src,'source_page_1based':page,
      'approved_local_equipment_nodes':[deepcopy(n) for n in nodes.values()],
      'approved_local_ports':[deepcopy(p) for p in ports.values()],
      'reviewed_visual_path_evidence':results,
      'owner_accepted_visual_path_count':len(approved),
      'engineer_accepted_physical_edges':[],
      'physical_graph_publish_ready':False,
      'requires_next':['source_stroke_chain','terminal_component_semantics','line_id_check','junctions','independent_engineering_qa'],
      'notice':'Accepted visual routes are not mechanically verified pipe edges. Downstream calculation/publishing prohibited.'
    }
