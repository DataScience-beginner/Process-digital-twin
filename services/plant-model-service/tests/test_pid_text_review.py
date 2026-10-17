import fitz
from app.pid_text_review import extract_tags,extract_line_strokes,build_draft_graph,source_sha256

def page():
 p=fitz.open();q=p.new_page(width=500,height=300)
 q.insert_text((80,95),'45-PA-806 A')
 q.insert_text((100,148),'PT')
 q.insert_text((100,161),'0401')
 q.draw_line((50,120),(240,120),color=(1,0,0),width=1)
 q.draw_line((175,80),(175,150),color=(1,0,0),width=1)
 return p,q

def test_equipment_text_does_not_become_accepted_graph_node():
 p,q=page();c=extract_tags(q)
 assert any('45-PA-806' in x['tag_text'] for x in c)
 g=build_draft_graph(c,source_sha256(p.tobytes()),1)
 assert not g['approved_nodes'] and not g['approved_edges']
 p.close()

def test_instrument_text_never_claims_visual_symbol():
 p,q=page();c=extract_tags(q)
 assert any(x['type']=='instrument_text' for x in c)
 assert all(x['review_status']=='unreviewed' for x in c)
 p.close()

def test_crossing_strokes_not_joined():
 p,q=page();seg=extract_line_strokes(q,min_len=15)
 assert len(seg)==2
 assert all(not e['connection_claim'] for e in seg)
 p.close()
