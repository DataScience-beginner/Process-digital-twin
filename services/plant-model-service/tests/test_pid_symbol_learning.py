"""Synthetic drawings only. NEVER upload actual restricted client glyphs to public GitHub."""
import copy, hashlib, json
from pathlib import Path
import pytest
cv2=pytest.importorskip('cv2')
np=pytest.importorskip('numpy')
from app.pid_symbol_learning import (
    ModelGateError, shape_features, build_model, predict_review_only,
    evaluate_document_holdout, feedback_to_review_queue,
)
SOURCE_HASH='f'*64

def glyph(path: Path,kind: str):
    a=np.ones((128,128),dtype=np.uint8)*255
    if kind=='gate':
        cv2.line(a,(16,64),(112,64),0,3)
        cv2.line(a,(42,44),(65,64),0,3);cv2.line(a,(42,84),(65,64),0,3)
        cv2.line(a,(88,44),(65,64),0,3);cv2.line(a,(88,84),(65,64),0,3)
    elif kind=='bubble':
        cv2.circle(a,(64,64),28,0,3)
        cv2.line(a,(20,64),(108,64),0,1)
    elif kind=='triangle':
        cv2.line(a,(64,35),(32,90),0,4);cv2.line(a,(32,90),(96,90),0,4);cv2.line(a,(96,90),(64,35),0,4)
    cv2.imwrite(str(path),a)

def case(dir, name,klass,grp,split='train'):
    path=dir/(name+'.png');glyph(path,klass)
    return {'record_id':name,'concept_id':klass,'client_id':'acme','drawing_group':grp,
            'source_sha256':SOURCE_HASH,'image_path':path.name,
            'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'owner_approved':True,'independent_qa_passed':True,
            'rights_confirmed_for_ml':True,'owner_reviewer':'author_1',
            'independent_reviewer':'reviewer_2', 'symbol_is_atomic':True,
            'quality_flags':[], 'dataset_split':split}

def pair(tmp):
    return [case(tmp,'train_valve','gate','legend_sheet_source'),
            case(tmp,'train_instrument','bubble','legend_sheet_source')]

def test_training_is_versioned_and_model_abstains_on_unknown(tmp_path):
    x=pair(tmp_path);dest=tmp_path/'model.json'
    s=build_model(x,tmp_path,dest,client_id='acme');assert s['examples']==2
    m=json.loads(dest.read_text());assert m['status']=='TRAINED_UNCALIBRATED_NOT_DEPLOYABLE'
    a=predict_review_only(m,tmp_path/'train_valve.png',client_id='acme')
    assert a['proposed_concept_id']=='gate' and not a['ready_for_engineering_use']
    glyph(tmp_path/'new.png','triangle')
    b=predict_review_only(m,tmp_path/'new.png',client_id='acme',min_similarity=0.99999)
    assert b['status']=='UNKNOWN_REQUIRES_REVIEW' and b['proposed_concept_id'] is None
    assert s['version']==build_model(x,tmp_path,dest,client_id='acme')['version']

@pytest.mark.parametrize('field,value', [('owner_approved',False),('independent_qa_passed',False),('rights_confirmed_for_ml',False),('symbol_is_atomic',False)])
def test_gate_rejects_untrusted_inputs(tmp_path,field,value):
    records=pair(tmp_path);records[0][field]=value
    with pytest.raises(ModelGateError):build_model(records,tmp_path,tmp_path/'m.json',client_id='acme')

def test_cross_client_no_leak_and_two_real_reviewers(tmp_path):
    items=pair(tmp_path);items[0]['independent_reviewer']='author_1'
    with pytest.raises(ModelGateError):build_model(items,tmp_path,tmp_path/'m.json',client_id='acme')
    items=pair(tmp_path);build_model(items,tmp_path,tmp_path/'m.json',client_id='acme')
    with pytest.raises(ModelGateError):predict_review_only(json.loads((tmp_path/'m.json').read_text()),tmp_path/'train_valve.png',client_id='other_company')

def test_rejects_image_mutation_and_path_escape(tmp_path):
    items=pair(tmp_path);items[0]['image_sha256']='0'*64
    with pytest.raises(ModelGateError):build_model(items,tmp_path,tmp_path/'m.json',client_id='acme')
    items=pair(tmp_path);items[0]['image_path']='../private.png'
    with pytest.raises(ModelGateError):build_model(items,tmp_path,tmp_path/'m.json',client_id='acme')

def test_holdout_requires_distinct_document(tmp_path):
    items=pair(tmp_path);dest=tmp_path/'m.json';build_model(items,tmp_path,dest,client_id='acme')
    model=json.loads(dest.read_text())
    c=case(tmp_path,'test_valve','gate','separate_PID_sheet',split='test')
    result=evaluate_document_holdout(model,[c],tmp_path,client_id='acme')
    assert result['test_records']==1 and result['model_state'].startswith('EVALUATED')
    c['drawing_group']='legend_sheet_source'
    with pytest.raises(ModelGateError):evaluate_document_holdout(model,[c],tmp_path,client_id='acme')

def test_feedback_does_not_retrain(tmp_path):
    result=feedback_to_review_queue({'status':'UNVERIFIED_MODEL_PROPOSAL','model_version':'abc'},
       {'decision':'correct','corrected_concept':'check_valve','reviewer':'user'},tmp_path/'feedback.jsonl')
    assert result['auto_trained'] is False
    r=json.loads((tmp_path/'feedback.jsonl').read_text());assert r['graph_ready'] is False
