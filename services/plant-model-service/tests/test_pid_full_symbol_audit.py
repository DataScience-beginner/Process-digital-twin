import fitz
from pid_full_symbol_audit import scan_native_motifs


def _page():
    d=fitz.open();p=d.new_page(width=400,height=320);return d,p


def test_plain_circle_matches_complete_location_legend():
    d,p=_page();p.draw_circle((90,70),18,color=(1,0,0))
    r=scan_native_motifs(p);a=r['candidates']
    assert any(x['subtype_geometry']=='FIELD_CIRCLE' and x['suggested_legend_id_not_verified']=='DB_P40_031' for x in a)
    d.close()


def test_circle_and_square_match_full_composite_not_just_circle():
    d,p=_page();p.draw_circle((90,70),18,color=(1,0,0));p.draw_rect((72,52,108,88),color=(1,0,0))
    r=scan_native_motifs(p)
    assert any(x['subtype_geometry'].startswith('CIRCLE_SQUARE') for x in r['candidates'])
    d.close()


def test_rotated_quad_is_diamond_not_square():
    d,p=_page();p.draw_quad(fitz.Quad(fitz.Point(90,52),fitz.Point(108,70),fitz.Point(72,70),fitz.Point(90,88)),color=(1,0,0))
    r=scan_native_motifs(p)
    assert any(x['subtype_geometry']=='ROTATED_DIAMOND_INTERLOCK_OR_ALARM' for x in r['candidates'])
    d.close()


def test_bowtie_geometry_found_without_fill():
    d,p=_page()
    p.draw_polyline([(100,100),(115,109),(100,109),(115,100)],color=(1,0,0))
    r=scan_native_motifs(p)
    assert any(x['family']=='INLINE_VALVE_FAMILY' for x in r['candidates'])
    d.close()


def test_unsupported_class_not_passed_as_physical_edges():
    d,p=_page();p.draw_line((60,190),(250,190),color=(1,0,0))
    r=scan_native_motifs(p)
    assert r['engineering_graph_edges_accepted']==0
    assert not r['symbol_detection_recall_measured']
    d.close()
