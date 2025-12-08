import requests
from pathlib import Path

API_URL = "http://127.0.0.1:8000/ingest"
DELETE_URL = "http://127.0.0.1:8000/delete"  # Assume you've added this endpoint to your backend

def chunk_text(text: str, max_chars: int = 1000) -> list[str]:
    """Simple chunking by ~1000 chars with overlap"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - 200  # 200 char overlap
    return chunks

def delete_documents(meta_filter: dict):
    """Delete existing documents matching the meta filter"""
    body = {"meta_filter": meta_filter}  # Wrap in expected structure
    resp = requests.delete(DELETE_URL, json=body)
    print(f"Delete response: {resp.json()}")

def ingest_folder(folder_path: str, replace_existing: bool = False):
    folder = Path(folder_path)
    docs = []

    for txt_file in folder.rglob("*.txt"):  # supports subfolders
        print(f"Processing {txt_file}")

        if replace_existing:
            # Delete existing chunks for this file
            meta_filter = {"title": txt_file.name}  # Adjust based on how your backend queries/deletes
            delete_documents(meta_filter)

        text = txt_file.read_text(encoding="utf-8")
        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):
            docs.append({
                "content": chunk,
                "meta": {
                    "title": txt_file.name,
                    "chunk": i + 1,
                    "source": str(txt_file)
                }
            })

    # Send in batches of 50 to avoid timeout
    batch_size = 50
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        resp = requests.post(API_URL, json=batch)
        print(f"Ingested batch {i//batch_size + 1}: {resp.json()}")

if __name__ == "__main__":
    # Change this to your folder with TXT files
    ingest_folder(r"data", replace_existing=True)  # Set to True to replace previous sources

    print("✅ All TXT files ingested! Now use /query")