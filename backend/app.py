import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import laya_engine

app = FastAPI(title="Before You Send")


@app.on_event("startup")
def _warm():
    laya_engine.warmup()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AnalyzeRequest(BaseModel):
    text: str = ""


@app.get("/health")
def health():
    return {"status": "ok", "mode": laya_engine.mode()}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    return laya_engine.analyze(req.text or "")


_FRONTEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(_FRONTEND):
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")
