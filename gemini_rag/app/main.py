from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from .rag_service import rag_service

app = FastAPI()

class IngestDoc(BaseModel):
    content: str
    meta: Dict[str, Any] = {}

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

class DeleteRequest(BaseModel):
    meta_filter: Dict[str, Any]  # e.g., {"title": "test_data.txt"}

@app.post("/ingest")
def ingest(docs: List[IngestDoc]):
    try:
        payload = [{"content": d.content, "meta": d.meta} for d in docs]
        rag_service.ingest(payload)
        return {"status": "ok", "ingested": len(payload)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete")
def delete_docs(req: DeleteRequest):
    try:
        result = rag_service.delete(req.meta_filter)
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
def query(req: QueryRequest):
    try:
        return rag_service.query(req.query, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
