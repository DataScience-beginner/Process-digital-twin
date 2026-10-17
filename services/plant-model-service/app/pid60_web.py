"""Single-upload MVP. Run: uvicorn pid60_web:app --host 127.0.0.1 --port 8765

Deploy behind organization authentication and HTTPS before exposing to users.
Never log customer PDF payloads; private outputs are returned to the caller.
"""
from __future__ import annotations
import json, os, time, io
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from .pid60_pipeline import process_single_page, make_zip, MAX_BYTES

app=FastAPI(title='P&ID 60-second Preliminary Digitizer',version='0.1.0')
HTML='''<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1"><title>One-click P&ID digitizer</title><style>body{font-family:system-ui,sans-serif;max-width:700px;margin:50px auto;padding:16px;color:#1c2939}h1{font-size:1.6rem}label{display:block;margin:14px 0}button{background:#174a74;color:#fff;border:0;border-radius:8px;padding:12px 25px;font-size:16px}input{padding:8px}small{display:block;color:#666;margin-top:20px}</style><h1>Digitize one P&ID</h1><p>Upload a vector PDF (or the PDF containing your selected P&ID). One request produces a marked-up drawing, a provisional graph and measured processing time.</p><form action="/digitize" enctype="multipart/form-data" method="post"><label>PDF <input type="file" name="file" accept="application/pdf" required></label><label>PDF page number <input type="number" name="page" value="1" min="1" required></label><button type="submit">Digitize P&ID</button></form><small>Privacy: restricted sources should be processed only on an authorized local/internal deployment. Graph edges are provisional until engineering validation. Raster scans require a separate processing mode.</small>'''
@app.get('/',response_class=HTMLResponse)
async def home():return HTML
@app.post('/digitize')
async def digitize(file:UploadFile=File(...),page:int=Form(1)):
    # Size guard, including multipart uploads: do not allow unlimited in-memory files.
    raw=await file.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise HTTPException(status_code=413,detail='PDF exceeds 55MB')
    try:
        # Opt-in local/internal reviewed-evidence sidecar. Exact original PDF hash/page
        # validation occurs inside the processor. Never load client data from code.
        review_file=os.environ.get('PID_REVIEW_FILE', '').strip()
        reviewed=json.loads(Path(review_file).read_text()) if review_file else None
        payload=process_single_page(raw,page,approved_review=reviewed)
        content=make_zip(payload)
    except (ValueError,RuntimeError,IndexError) as e:
        raise HTTPException(status_code=422,detail=str(e)) from e
    return Response(content=content,media_type='application/zip',headers={
      'Content-Disposition':'attachment; filename="pid_preliminary_digital_package.zip"',
      'X-Processing-Seconds':str(payload['benchmark']['whole_drawing_seconds']),
      'X-Candidate-Instruments':str(payload['summary']['instrument_geometry_count'])})
