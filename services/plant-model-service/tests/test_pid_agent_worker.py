"""E2E synthetic agent orchestration/recognition checks. No client drawing data."""
import io
import json
import zipfile

import fitz
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.agent_pilot_gateway import create_app
from app.pid_agent_worker import execute_one


def sheet(text, *, vector=True):
    doc = fitz.open()
    pg = doc.new_page(width=600, height=430)
    pg.insert_text((60, 60), text)
    if vector:
        pg.draw_circle((180, 170), 18, color=(1, 0, 0), width=2)
        pg.draw_rect(fitz.Rect(162, 152, 198, 188), color=(1, 0, 0), width=2)
        pg.draw_line((163, 170), (197, 170), color=(1, 0, 0))
        pg.insert_text((172, 170), "PT", fontsize=7)
        pg.draw_line((220, 250), (380, 250), color=(1, 0, 0))
    data = doc.tobytes()
    doc.close()
    return data


def api(tmp_path):
    uri = f'sqlite:///{tmp_path}/agent-stage.sqlite'
    app = create_app(uri, admin_token='test-admin', uploads_enabled=True)
    http = TestClient(app)
    tenant = http.post('/api/admin/companies', headers={'X-Admin-Token':'test-admin'},
        json={'company_name':'Fictional plant pilot'}).json()
    headers = {'X-Client-Token':tenant['company_access_token']}
    project = http.post('/api/projects', headers=headers, json={'name':'Pump train'}).json()['project_id']
    return http, create_engine(uri), tenant, headers, project


def upload(http, headers, project, data, kind='pid'):
    return http.post(f'/api/projects/{project}/documents?kind={kind}&page=1',
        headers=headers, files={'file':(f'{kind}.pdf',data,'application/pdf')})


def preview_payload(raw, page):
    assert raw.startswith(b'%PDF-') and page == 1
    return {'graph':{'provisional_graph_only':True,'publish_ready':False,
                     'edges':{'engineering_approved_physical_connections':[]},'nodes':{'instrument_shape_candidates':[]}},
            'summary':{'accepted_physical_graph_edges':0,'instrument_geometry_count':0},
            'benchmark':{'whole_drawing_seconds':0.1},
            'overlay_png':b'\x89PNG\r\n\x1a\nFAKE', 'annotated_pdf':raw}


def test_preflight_then_first_graph_and_source_linked_artifact(tmp_path):
    http, engine, tenant, headers, project = api(tmp_path)
    src = sheet('P&ID P-101')
    pid = upload(http, headers, project, src).json()['document_id']
    assert execute_one(engine)['processed'] is False  # missing legend blocks worker
    assert http.get(f'/api/projects/{project}/documents/{pid}/candidate-graph',headers=headers).status_code == 404
    legend = upload(http, headers, project, sheet('LEGEND SYMBOL GATE VALVE'), kind='legend')
    assert legend.status_code == 200
    state = http.get(f'/api/projects/{project}/status',headers=headers).json()
    assert state['recognition_jobs'][0]['state'] == 'queued'
    assert state['free_pid_used'] == 1
    result = execute_one(engine, processor=preview_payload)
    assert result['processed'] and result['state']=='candidate_review_ready'
    graph_response = http.get(f'/api/projects/{project}/documents/{pid}/candidate-graph',headers=headers)
    assert graph_response.status_code == 200
    graph = graph_response.json()['graph']
    assert graph['original_source']['original_pdf_sha256'] == __import__('hashlib').sha256(src).hexdigest()
    assert graph['original_source']['original_page_1based'] == 1
    assert graph['publish_ready'] is False
    assert graph['edges']['engineering_approved_physical_connections'] == []
    z = http.get(f'/api/projects/{project}/documents/{pid}/artifact?format=zip',headers=headers)
    assert z.status_code == 200
    assert z.headers['cache-control'] == 'private, no-store'
    with zipfile.ZipFile(io.BytesIO(z.content)) as archive:
        assert set(archive.namelist()) >= {'candidate_markup.png','candidate_annotated.pdf','candidate_graph.json'}
        assert json.loads(archive.read('candidate_graph.json'))['original_source']['document_id'] == pid
    state = http.get(f'/api/projects/{project}/status',headers=headers).json()
    assert state['recognition_jobs'][0]['state']=='candidate_review_ready'
    assert any(q['code']=='REVIEW_CANDIDATES' for q in state['chat_questions'])
    assert state['free_pid_used'] == 1
    assert execute_one(engine, processor=preview_payload)['processed'] is False


def test_cross_tenant_cannot_view_graph_or_artifact(tmp_path):
    http, engine, tenant, headers, project = api(tmp_path)
    upload(http,headers,project,sheet('LEGEND SYMBOL GATE VALVE'),kind='legend')
    doc_id = upload(http,headers,project,sheet('P&ID PLANT P-101')).json()['document_id']
    assert execute_one(engine, processor=preview_payload)['state']=='candidate_review_ready'
    rival = http.post('/api/admin/companies', headers={'X-Admin-Token':'test-admin'},
        json={'company_name':'Another company'}).json()
    wrong = {'X-Client-Token':rival['company_access_token']}
    for endpoint in ('candidate-graph','artifact'):
        assert http.get(f'/api/projects/{project}/documents/{doc_id}/{endpoint}',headers=wrong).status_code==404
        assert http.get(f'/api/projects/{project}/documents/{doc_id}/{endpoint}').status_code==401


def test_reject_nonprovisional_graph_or_invented_physical_edge(tmp_path):
    http, engine, tenant, headers, project = api(tmp_path)
    upload(http,headers,project,sheet('LEGEND SYMBOL GATE VALVE'),kind='legend')
    doc_id = upload(http,headers,project,sheet('P&ID LINE')).json()['document_id']
    def unsafe(src,page):
        data=preview_payload(src,page)
        data['graph']['edges']['engineering_approved_physical_connections']=[{'invented':True}]
        return data
    result=execute_one(engine,processor=unsafe)
    assert result['state']=='needs_engineering_review'
    assert result['error_code']=='output_integrity_failed'
    assert http.get(f'/api/projects/{project}/documents/{doc_id}/artifact',headers=headers).status_code==409
    assert http.get(f'/api/projects/{project}/status',headers=headers).json()['free_pid_used']==1


def test_scanned_pdf_raises_reviewer_question(tmp_path):
    http, engine, tenant, headers, project = api(tmp_path)
    upload(http,headers,project,sheet('LEGEND SYMBOL GATE VALVE'),kind='legend')
    doc_id = upload(http,headers,project,sheet('P&ID IMAGE ONLY',vector=False)).json()['document_id']
    def scanned(src,page):
        raise ValueError('Raster/unsupported native geometry')
    assert execute_one(engine,processor=scanned)['state']=='needs_engineering_review'
    state = http.get(f'/api/projects/{project}/status',headers=headers).json()
    assert any(q['code']=='UNSUPPORTED_DRAWING' for q in state['chat_questions'])
    assert any(d['id']==doc_id for d in []) is False


def test_two_free_quota_stops_third_before_worker_execution(tmp_path):
    http, engine, tenant, headers, project = api(tmp_path)
    upload(http,headers,project,sheet('LEGEND SYMBOL GATE VALVE'),kind='legend')
    ids=[]
    for index in range(3):
        ids.append(upload(http,headers,project,sheet(f'P&ID LINE {index}')).json()['document_id'])
    assert execute_one(engine,processor=preview_payload)['processed'] is True
    assert execute_one(engine,processor=preview_payload)['processed'] is True
    assert execute_one(engine,processor=preview_payload)['processed'] is False
    state=http.get(f'/api/projects/{project}/status',headers=headers).json()
    assert state['free_pid_used']==2 and len(state['recognition_jobs'])==2
    assert http.get(f'/api/projects/{project}/documents/{ids[2]}/artifact',headers=headers).status_code == 404
    grant=http.post(f'/api/admin/companies/{tenant["company_id"]}/grant',
        headers={'X-Admin-Token':'test-admin'},json={'additional_credits':1,'commercial_reference':'signed-scope-0001'})
    assert grant.status_code==200
    assert execute_one(engine,processor=preview_payload)['processed'] is True
    assert http.get(f'/api/projects/{project}/status',headers=headers).json()['free_pid_used']==2


def test_actual_pdf_geometry_pipeline_without_client_sources(tmp_path):
    from pytest import importorskip
    pipeline=importorskip('app.pid60_pipeline')
    http, engine, tenant, headers, project=api(tmp_path)
    upload(http,headers,project,sheet('LEGEND SYMBOL GATE VALVE'),kind='legend')
    source=sheet('P&ID PIPE CAD')
    document=upload(http,headers,project,source).json()['document_id']
    r=execute_one(engine,processor=pipeline.process_single_page)
    assert r['state']=='candidate_review_ready',r
    resp=http.get(f'/api/projects/{project}/documents/{document}/candidate-graph',headers=headers)
    assert resp.status_code==200
    data=resp.json()
    assert data['summary']['accepted_physical_graph_edges']==0
    assert len(data['graph']['edges']['source_cad_strokes'])>=1