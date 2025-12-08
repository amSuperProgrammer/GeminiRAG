from fastapi import FastAPI, UploadFile, File, HTTPException
from text_utils import extract_text_from_pdf, extract_text_from_docx, clean_text, chunk_text
import tempfile
import google.generativeai as genai
import os
from fastapi.middleware.cors import CORSMiddleware

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
emb_model = "models/text-embedding-004"

app = FastAPI(title="Ingest & Extract API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить любые источники (в т.ч. Origin: null)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- helper: сохранить файл и вернуть очищенный текст ---
async def load_and_extract(file: UploadFile) -> str:
    suffix = os.path.splitext(file.filename)[1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        if suffix == ".pdf":
            raw = extract_text_from_pdf(tmp_path)
        elif suffix == ".docx":
            raw = extract_text_from_docx(tmp_path)
        elif suffix == ".txt":
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        return clean_text(raw)

    finally:
        try:
            os.remove(tmp_path)
        except:
            pass


# === /extract endpoint ===
@app.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    text = await load_and_extract(file)

    return {
        "filename": file.filename,
        "characters": len(text),
        "text": text
    }


# === /ingest endpoint ===
@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    text = await load_and_extract(file)

    chunks = chunk_text(text)

    vectors = []
    for ch in chunks:
        resp = genai.embed_content(
            model=emb_model,
            content=ch,
            task_type="retrieval_document"
        )
        vectors.append({
            "text": ch,
            "embedding": resp["embedding"]
        })

    return {
        "filename": file.filename,
        "chunks_count": len(vectors),
        "vector_dim": len(vectors[0]["embedding"]) if vectors else 0,
        "preview": vectors[:2]
    }
    
# === server run ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "extract_api:app",
        host="0.0.0.0",
        port=8004,
        reload=True
    )