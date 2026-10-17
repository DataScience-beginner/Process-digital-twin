import io,sys,json,zipfile
from pathlib import Path
import fitz,pytest
from app.pid60_pipeline import process_single_page,make_zip,_stroke_endpoint_network
from fastapi.testclient import TestClient
from app.pid60_web import app

def sample_pdf():
 d=fitz.open();p=d.new_page(width=550,height=430)
 # Red closed Bezier circle and square-ish CAD strokes built independently.
 red=(1,0,0)
 p.draw_circle(fitz.Point(150,150),18,color=red,width=2)
 p.draw_rect(fitz.Rect(132,132,168,168),color=red,width=2)
 p.draw_line(fitz.Point(133,150),fitz.Point(167,150),color=red,width=1)
 p.insert_text((144,150),'PT',fontsize=7)
 p.draw_line((180,190),(260,190),color=red)
 p.draw_line((260,190),(260,250),color=red)
 p.insert_text((250,275),'45-PA-806',fontsize=10)
 out=d.tobytes();d.close();return out

def test_vector_batch_makes_actual_png_and_graph():
 o=process_single_page(sample_pdf());assert o['overlay_png'][:8]==b'\x89PNG\r\n\x1a\n'
 assert o['graph']['publish_ready'] is False
 assert o['summary']['accepted_physical_graph_edges']==0
 assert o['summary']['raw_cad_stroke_count']>=2
 assert len(make_zip(o))>1000

def test_line_cross_without_endpoints_is_not_connected():
 edges=[{'id':'a','a':[0.,10.],'b':[100.,10.]},
        {'id':'b','a':[50.,0.],'b':[50.,30.]}]
 network=_stroke_endpoint_network(edges)
 assert network['endpoint_clusters']==4

def test_owner_approval_sha_mismatch_blocked():
 with pytest.raises(ValueError,match='SHA-256'):
  process_single_page(sample_pdf(),approved_review={'source_sha256':'wrong','source_page_1based':1})

def test_upload_zip_endpoint_returns_reviewable_artifacts():
 client=TestClient(app)
 r=client.post('/digitize',data={'page':'1'},files={'file':('test.pdf',sample_pdf(),'application/pdf')})
 assert r.status_code==200,r.text
 assert 'X-Processing-Seconds' in r.headers
 with zipfile.ZipFile(io.BytesIO(r.content)) as z:
  assert {'whole_sheet_markup.png','candidate_graph.json','candidate_counts_and_benchmark.json'}.issubset(z.namelist())
  model=json.loads(z.read('candidate_graph.json'))
  assert not model['edges']['engineering_approved_physical_connections']

def test_raster_is_not_called_complete_vector_recognition():
 doc=fitz.open();doc.new_page();bad=doc.tobytes()
 with pytest.raises(ValueError,match='Raster/unsupported'):process_single_page(bad)


def test_existing_review_import_is_source_locked(monkeypatch,tmp_path):
 raw=sample_pdf()
 import hashlib
 path=tmp_path/'trusted_project_review.json'
 path.write_text(json.dumps({'source_sha256':hashlib.sha256(raw).hexdigest(),'source_page_1based':1,
    'approved_local_equipment_nodes':[{'id':'NODE-1','center':[300,300]}],
    'approved_local_ports':[], 'reviewed_visual_path_evidence':[]}))
 monkeypatch.setenv('PID_REVIEW_FILE',str(path))
 r=TestClient(app).post('/digitize',data={'page':'1'},files={'file':('test.pdf',raw,'application/pdf')})
 assert r.status_code==200,r.text
 with zipfile.ZipFile(io.BytesIO(r.content)) as z:
  g=json.loads(z.read('candidate_graph.json'))
  assert len(g['nodes']['owner_reviewed_local_equipment'])==1
  assert len(g['edges']['engineering_approved_physical_connections'])==0
 monkeypatch.setenv('PID_REVIEW_FILE',str(path))
 with fitz.open(stream=raw,filetype='pdf') as doc:
  page=doc[0];page.insert_text((20,300),'revision!');changed=doc.tobytes()
 r=TestClient(app).post('/digitize',data={'page':'1'},files={'file':('different.pdf',changed,'application/pdf')})
 assert r.status_code==422
