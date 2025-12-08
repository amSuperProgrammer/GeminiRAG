from typing import List
import os
import time
import requests

BGE_EMBED_URL = os.environ.get("BGE_EMBED_URL", "https://api.example.com/bge/embed")
BGE_API_KEY = os.environ.get("BGE_API_KEY", "")
BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "16"))
TIMEOUT = int(os.environ.get("EMBED_TIMEOUT", "30"))
RETRIES = int(os.environ.get("EMBED_RETRIES", "3"))
RETRY_BACKOFF = float(os.environ.get("EMBED_RETRY_BACKOFF", "0.8"))

headers = {"Authorization": f"Bearer {BGE_API_KEY}", "Content-Type": "application/json"}

def _call_embed_api(texts: List[str]) -> List[List[float]]:
    payload = {"inputs": texts}
    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.post(BGE_EMBED_URL, json=payload, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            # adapt to your provider response shape; assume data["embeddings"] is list[list[float]]
            return data["embeddings"]
        except Exception as e:
            if attempt == RETRIES:
                raise
            time.sleep(RETRY_BACKOFF * attempt)
    raise RuntimeError("Unreachable")

def bge_m3_embed(texts: List[str]) -> List[List[float]]:
    all_embs = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        embs = _call_embed_api(batch)
        all_embs.extend(embs)
    return all_embs