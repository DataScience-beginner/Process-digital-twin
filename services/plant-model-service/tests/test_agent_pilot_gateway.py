
import fitz
from fastapi.testclient import TestClient

from app.agent_pilot_gateway import create_app


def pdf(text):
    p = fitz.open(); page=p.new_page(); page.insert_text((30,30),text)
    value=p.tobytes(); p.close()
    return value


def setup(tmp_path, name='Refinery A', mode='managed_shared'):
    app = create_app(f'sqlite:///{tmp_path}/tenant.db', admin_token='admin-secret', uploads_enabled=True)
    c = TestClient(app)
    r=c.post('/api/admin/companies',json={'company_name':name,'deployment_mode':mode},
             headers={'X-Admin-Token':'admin-secret'})
    assert r.status_code==200,r.text
    tenant=r.json()
    headers={'X-Client-Token':tenant['company_access_token']}
    project=c.post('/api/projects',json={'name':'Pump system'},headers=headers).json()['project_id']
    return c, tenant, project, headers


def upload(c, project, headers, text, kind='pid'):
    payload = text if isinstance(text, bytes) else pdf(text)
    return c.post(f'/api/projects/{project}/documents?kind={kind}&page=1',headers=headers,
        files={'file':(f'{kind}.pdf',payload,'application/pdf')})


def test_missing_legend_chat_and_auto_resume(tmp_path):
    c,t,p,h=setup(tmp_path)
    r=upload(c,p,h,'P&ID TEST PUMP P-101')
    assert r.status_code==200,r.text
    assert r.json()['status']=='waiting_for_legend'
    s=c.get(f'/api/projects/{p}/status',headers=h).json()
    assert s['free_pid_used']==0
    q=[q for q in s['chat_questions'] if q['code']=='MISSING_LEGEND'][0]
    reply=c.post(f'/api/projects/{p}/chat/{q["id"]}/reply',json={'answer':'I will upload it'},headers=h)
    assert reply.status_code==200
    r=upload(c,p,h,'P&ID LEGEND GATE VALVE SYMBOL INSTRUMENT',kind='legend')
    assert r.status_code==200,r.text
    s=c.get(f'/api/projects/{p}/status',headers=h).json()
    assert s['free_pid_used']==1
    assert any(d['kind']=='pid' and d['status']=='ready_for_recognition' for d in s['documents'])
    assert any(q['code']=='MISSING_LEGEND' and q['status']=='resolved' for q in s['chat_questions'])


def test_two_free_quota_and_commercial_gate(tmp_path):
    c,t,p,h=setup(tmp_path)
    upload(c,p,h,'P&ID LEGEND GATE VALVE',kind='legend')
    states=[upload(c,p,h,f'P&ID TEST {i}').json()['status'] for i in range(3)]
    assert states==['ready_for_recognition','ready_for_recognition','contact_sales_required']
    s=c.get(f'/api/projects/{p}/status',headers=h).json()
    assert s['free_pid_used']==2
    assert any(q['code']=='CONTACT_SALES' for q in s['chat_questions'])
    assert c.post(f'/api/admin/companies/{t["company_id"]}/grant',json={
        'additional_credits':1,'commercial_reference':'signed-001'},
        headers={'X-Admin-Token':'bad'}).status_code==403
    assert c.post(f'/api/admin/companies/{t["company_id"]}/grant',json={
        'additional_credits':1,'commercial_reference':'signed-001'},
        headers={'X-Admin-Token':'admin-secret'}).status_code==200
    s=c.get(f'/api/projects/{p}/status',headers=h).json()
    assert sum(d['status']=='ready_for_recognition' for d in s['documents'])==3
    assert s['free_pid_used']==2 and s['paid_credits_remaining']==0


def test_dedupe_never_charges_twice(tmp_path):
    c,t,p,h=setup(tmp_path)
    upload(c,p,h,'P&ID LEGEND GATE VALVE',kind='legend')
    exact_bytes=pdf('P&ID DUPLICATE')
    first=upload(c,p,h,exact_bytes)
    second=upload(c,p,h,exact_bytes)
    assert first.status_code==200 and second.json()['duplicate'] is True
    assert c.get(f'/api/projects/{p}/status',headers=h).json()['free_pid_used']==1


def test_no_cross_tenant_access(tmp_path):
    c,a,pa,ha=setup(tmp_path)
    t=c.post('/api/admin/companies',json={'company_name':'Other LLC','deployment_mode':'managed_dedicated'},
             headers={'X-Admin-Token':'admin-secret'}).json()
    hb={'X-Client-Token':t['company_access_token']}
    pb=c.post('/api/projects',json={'name':'Private project'},headers=hb).json()['project_id']
    assert c.get(f'/api/projects/{pa}/status',headers=hb).status_code==404
    assert c.get(f'/api/projects/{pb}/status',headers=ha).status_code==404
    assert c.get(f'/api/projects/{pa}/status').status_code==401
    assert t['global_training_opt_in'] is False


def test_roles_and_legend_review_fail_closed(tmp_path):
    c,t,p,h=setup(tmp_path)
    upload(c,p,h,'P&ID TEST A')
    leg=upload(c,p,h,'Random schematic title',kind='legend')
    assert leg.json()['status']=='legend_needs_review'
    s=c.get(f'/api/projects/{p}/status',headers=h).json()
    assert s['free_pid_used']==0
    assert any(q['code']=='LEGEND_REVIEW' for q in s['chat_questions'])


def test_registration_admin_required_and_company_uniqueness(tmp_path):
    c,t,p,h=setup(tmp_path)
    assert c.post('/api/admin/companies',json={'company_name':'New Client'}).status_code==403
    assert c.post('/api/admin/companies',json={'company_name':'  refinery a  '},
        headers={'X-Admin-Token':'admin-secret'}).status_code==409


def test_disabled_uploads_even_for_authenticated_tenant(tmp_path):
    c,t,p,h=setup(tmp_path)
    c2=TestClient(create_app(f'sqlite:///{tmp_path}/tenant.db',admin_token='admin-secret',uploads_enabled=False))
    r=upload(c2,p,h,'P&ID DATA')
    assert r.status_code==503


def test_private_cloud_needs_separate_deployment(tmp_path):
    c,t,p,h=setup(tmp_path)
    r=c.post('/api/admin/companies',json={'company_name':'Restricted Client','deployment_mode':'private_cloud'},
             headers={'X-Admin-Token':'admin-secret'})
    assert r.status_code==409