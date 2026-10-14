"""End-to-end client workflow: 2 uploaded PDFs, engineer legend+P&ID review,
single-page extraction and source-document provenance without baseline write.
"""
from __future__ import annotations

import io
import zipfile
import fitz
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.db_schema import Base
from app import pid_digitization_api as pid
from app import pid_client_intake_api as intake


def fixture_pdf(role: str):
    doc=fitz.open()
    page=doc.new_page(width=850,height=550)
    if role=="legend":
        page.insert_text((660,425),"P&ID LEGENDS AND SYMBOLS")
        page.insert_text((90,140),"CHECK VALVE")
        page.insert_text((90,180),"PUMP, CENTRIFUGAL")
    else:
        page.insert_text((685,430),"PUMP STATION P&ID")
        page.insert_text((695,480),"P-101")
        page.insert_text((100,150),"P-101")
        page.insert_text((335,155),"V-101")
        shape=page.new_shape()
        shape.draw_circle(fitz.Point(115,190),30)
        shape.draw_rect(fitz.Rect(310,115,410,225))
        shape.draw_line((145,190),(310,190))
        shape.finish(color=(0,0,0),width=1.5)
        shape.commit()
    b=doc.tobytes()
    doc.close()
    return b


def test_client_package_workflow_requires_approved_legend_before_extraction(monkeypatch,tmp_path):
    engine=create_engine("sqlite+pysqlite://",
                         connect_args={"check_same_thread":False},
                         poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(intake,"_database",lambda:engine)
    monkeypatch.setattr(pid,"_database",lambda:engine)
    monkeypatch.setenv("BDEP_PID_STORAGE",str(tmp_path))
    app=FastAPI()
    app.include_router(intake.router)
    app.include_router(pid.router)
    client=TestClient(app)
    r=client.post("/api/pid-digitization/client-batches",
                  data={"client_label":"Test Client","package_label":"PIDs+Legends"},
                  files=[
                      ("files",("legend.pdf",fixture_pdf("legend"),"application/pdf")),
                      ("files",("pid.pdf",fixture_pdf("pid"),"application/pdf")),
                  ])
    assert r.status_code==200,r.text
    data=r.json()
    docs=data["documents"]
    assert len(docs)==2
    roles=[d["preflight"]["pages"][0]["role"] for d in docs]
    assert roles==["legend","pid"],roles
    batch_id=data["id"]
    report=client.get(f"/api/pid-digitization/client-batches/{batch_id}/readiness")
    assert report.json()["readiness"]!="ready_for_pagewise_evidence_extraction"
    pdfdoc=docs[1]["id"]
    blocked=client.post(f"/api/pid-digitization/client-batches/{batch_id}/documents/{pdfdoc}/pages/1/analyze")
    assert blocked.status_code==409
    decisions=[
        {"document_id":doc["id"],"page":1,"role":role}
        for doc,role in zip(docs,["legend","pid"])
    ]
    approve=client.post(f"/api/pid-digitization/client-batches/{batch_id}/roles/review",
                        json={"reviewer":"Eng-Test","decisions":decisions})
    assert approve.status_code==200,approve.text
    assert approve.json()["readiness"]["readiness"]=="ready_for_pagewise_evidence_extraction"
    legend_doc=docs[0]
    sample=legend_doc["preflight"]["legend_terms"][0]
    crop=client.get(
        f"/api/pid-digitization/client-batches/{batch_id}/documents/{legend_doc['id']}/legends/{sample['id']}.png"
    )
    assert crop.status_code==200
    assert crop.content.startswith(b"\x89PNG")
    legend_review=client.post(
        f"/api/pid-digitization/client-batches/{batch_id}/legends/review",
        json={"reviewer":"Eng-Test",
              "decisions":[{"document_id":legend_doc["id"],
                            "legend_term_id":sample["id"],
                            "decision":"accepted"}]}
    )
    assert legend_review.status_code==200,legend_review.text
    assert legend_review.json()["accepted_legend_examples"]==1
    image=client.get(
        f"/api/pid-digitization/client-batches/{batch_id}/documents/{pdfdoc}/pages/1.png"
    )
    assert image.status_code==200 and image.content[:8]==b"\x89PNG\r\n\x1a\n"
    extracted=client.post(
        f"/api/pid-digitization/client-batches/{batch_id}/documents/{pdfdoc}/pages/1/analyze"
    )
    assert extracted.status_code==200,extracted.text
    result=extracted.json()
    assert result["publish_ready"] is False
    assert result["project_legend_candidates"]>=2
    assert result["review_url"].endswith(result["import_id"])
    doc_result=client.get(
        f'/api/pid-digitization/imports/{result["import_id"]}'
    )
    assert doc_result.status_code==200
    source=doc_result.json()["client_source"]
    assert source["source_document_id"]==pdfdoc
    assert source["source_original_sha256"]==docs[1]["preflight"]["source_sha256"]
    assert source["source_original_page"]==1
    assert doc_result.json()["candidates"]
    assert all(e["review_status"]=="unreviewed"
               for e in doc_result.json()["connection_proposals"])


def test_unknown_sheet_and_disguised_non_pdf_are_rejected(monkeypatch,tmp_path):
    engine=create_engine("sqlite+pysqlite://",connect_args={"check_same_thread":False},
                         poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(intake,"_database",lambda:engine)
    monkeypatch.setenv("BDEP_PID_STORAGE",str(tmp_path))
    app=FastAPI()
    app.include_router(intake.router)
    client=TestClient(app)
    bad=client.post("/api/pid-digitization/client-batches",
                    data={"client_label":"Test client","package_label":"drawing set"},
                    files=[("files",("bad.pdf",b"this is not a drawing","application/pdf"))])
    assert bad.status_code==422


def test_zip_package_ingestion_is_path_safe_and_preserves_multiple_pdf_members(
    monkeypatch, tmp_path
):
    engine=create_engine("sqlite+pysqlite://",
                         connect_args={"check_same_thread":False},
                         poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(intake,"_database",lambda:engine)
    monkeypatch.setenv("BDEP_PID_STORAGE",str(tmp_path))
    app=FastAPI()
    app.include_router(intake.router)
    client=TestClient(app)
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("project/01_Legend.pdf",fixture_pdf("legend"))
        z.writestr("project/02_PandID.pdf",fixture_pdf("pid"))
        z.writestr("project/README.txt","Testing a README to ensure it is ignored")
    response=client.post(
        "/api/pid-digitization/client-batches/zip",
        data={"client_label":"Test zip client","package_label":"Rev A packaged drawings"},
        files={"archive":("set.zip",archive.getvalue(),"application/zip")},
    )
    assert response.status_code==200,response.text
    docs=response.json()["documents"]
    assert len(docs)==2
    assert {d["filename"] for d in docs}=={"01_Legend.pdf","02_PandID.pdf"}
    assert all(d["preflight"]["source_sha256"] for d in docs)


def test_disguised_zip_member_rejected(monkeypatch,tmp_path):
    engine=create_engine("sqlite+pysqlite://",
                         connect_args={"check_same_thread":False},
                         poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(intake,"_database",lambda:engine)
    monkeypatch.setenv("BDEP_PID_STORAGE",str(tmp_path))
    app=FastAPI()
    app.include_router(intake.router)
    client=TestClient(app)
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,"w") as z:
        z.writestr("../evil.pdf",b"not a PDF")
    response=client.post(
        "/api/pid-digitization/client-batches/zip",
        data={"client_label":"Test zip client","package_label":"Rev A drawings"},
        files={"archive":("bad.zip",archive.getvalue(),"application/zip")},
    )
    assert response.status_code==422
