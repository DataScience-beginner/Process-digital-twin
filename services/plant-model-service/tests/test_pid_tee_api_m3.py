"""HTTP engineering review test: approve a tee, rebuild and re-review graph."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

import fitz

from app.db_schema import Base
from app import pid_digitization_api as api


def _drawing():
    doc=fitz.open()
    page=doc.new_page(width=650,height=380)
    s=page.new_shape()
    s.draw_rect(fitz.Rect(55,40,140,180))
    s.draw_circle(fitz.Point(230,260),30)
    s.draw_polyline([(320,91),(345,110),(320,129),(320,91)])
    s.draw_polyline([(370,91),(345,110),(370,129),(370,91)])
    s.draw_line((140,110),(320,110))
    s.draw_line((230,110),(230,230))  # tee endpoint touching line interior
    s.finish(color=(0,0,0),width=1.3)
    s.commit()
    page.insert_text((75,75),"V-101")
    page.insert_text((208,317),"P-102")
    page.insert_text((326,70),"FCV-101")
    payload=doc.tobytes()
    doc.close()
    return payload


def test_engineer_review_tee_resets_approved_process_routes(tmp_path,monkeypatch):
    engine=create_engine("sqlite+pysqlite://",
                         connect_args={"check_same_thread":False},
                         poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(api,"_database",lambda:engine)
    monkeypatch.setenv("BDEP_PID_STORAGE",str(tmp_path))
    app=FastAPI()
    app.include_router(api.router)
    client=TestClient(app)
    imported=client.post("/api/pid-digitization/imports",
                         files={"file":("tee.pdf",_drawing(),"application/pdf")})
    assert imported.status_code==200, imported.text
    body=imported.json()
    assert body["unresolved_tees"], body["network_diagnostics"]
    import_id=body["id"]

    tags=client.post(f"/api/pid-digitization/imports/{import_id}/review",
                     json={"reviewer":"engineer-test","decisions":[
                         {"candidate_id":c["id"],"decision":"accepted"}
                         for c in body["candidates"]
                     ]})
    assert tags.status_code==200
    orig=tags.json()["connection_proposals"]
    assert any({e["tag_a"],e["tag_b"]}=={"V-101","FCV-101"} for e in orig)
    a=orig[0]
    approve=client.post(f"/api/pid-digitization/imports/{import_id}/connections/review",
                        json={"reviewer":"engineer-test","decisions":[
                            {"proposal_id":a["id"],"decision":"accepted",
                             "direction":"a_to_b"}
                        ]})
    assert approve.status_code==200,approve.text
    assert any(e["review_status"]=="accepted"
               for e in approve.json()["connection_proposals"])

    tee=body["unresolved_tees"][0]
    reviewed=client.post(f"/api/pid-digitization/imports/{import_id}/tees/review",
                         json={"reviewer":"engineer-test","decisions":[
                             {"proposal_id":tee["id"],"decision":"accepted"}
                         ]})
    assert reviewed.status_code==200,reviewed.text
    new=reviewed.json()
    assert tee["id"] in new["junction_decisions"]["approved_tee_ids_applied"]
    assert all(e["review_status"]=="unreviewed"
               for e in new["connection_proposals"])
    assert new["review_history"][-1]["previously_approved_routes_invalidated"]>=1
    assert any(e["approved_tee_ids"] for e in new["connection_proposals"]), {"tees": new["unresolved_tees"], "decisions":new["junction_decisions"], "route_proposals":new["connection_proposals"], "symbols":new["symbol_hypotheses"]}
    assert client.get(f"/api/pid-digitization/imports/{import_id}/plant-draft").json()[
        "plant_model"]["connections"]==[]
