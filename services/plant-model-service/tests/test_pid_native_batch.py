"""Synthetic-only tests: no proprietary drawings, texts or images."""
import fitz, pytest
from pid_native_batch import extract_native_candidates


def fixture():
    d=fitz.open();p=d.new_page(width=420,height=320)
    p.draw_circle((110,110),17.94,color=(1,0,0),width=1)
    p.insert_text((102,110),'PT',fontsize=8,color=(1,0,0))
    p.insert_text((95,119),'0401',fontsize=6,color=(1,0,0))
    p.draw_line((160,190),(340,190),color=(1,0,0),width=1)
    p.draw_line((210,190),(210,240),color=(1,0,0),width=1)
    raw=d.tobytes();d.close();return raw


def test_bubble_and_cad_strokes_are_batch_observed():
    data=extract_native_candidates(fixture(),1)
    assert len(data['instrument_bubble_candidates'])==1
    assert 'PT' in data['instrument_bubble_candidates'][0]['source_text']
    assert len(data['source_cad_stroke_candidates'])>=2


def test_proposals_never_publish_physical_edges():
    data=extract_native_candidates(fixture(),1)
    assert data['approved_physical_graph_edges']==[]
    assert data['engineering_publish_ready'] is False
    assert all(not x['process_piping_confirmed'] for x in data['source_cad_stroke_candidates'])


def test_wrong_page_fails():
    with pytest.raises(ValueError):extract_native_candidates(fixture(),2)


def test_nonred_content_ignored():
    d=fitz.open();p=d.new_page(width=420,height=320)
    p.draw_circle((100,100),17.94,color=(0,0,0))
    p.insert_text((91,100),'PI',fontsize=8)
    raw=d.tobytes();d.close()
    assert not extract_native_candidates(raw,1)['instrument_bubble_candidates']
