# import os
# import requests
# import time
#
# BGE_GEN_URL = os.environ.get("BGE_GEN_URL", "https://api.example.com/bge/generate")
# BGE_API_KEY = os.environ.get("BGE_API_KEY", "")
# TIMEOUT = int(os.environ.get("GEN_TIMEOUT", "60"))
# RETRIES = int(os.environ.get("GEN_RETRIES", "3"))
# RETRY_BACKOFF = float(os.environ.get("GEN_RETRY_BACKOFF", "1.0"))
#
# headers = {"Authorization": f"Bearer {BGE_API_KEY}", "Content-Type": "application/json"}
#
# def generate_answer(prompt: str, max_tokens: int = 256, temperature: float = 0.0) -> str:
#     payload = {"prompt": prompt, "max_tokens": max_tokens, "temperature": temperature}
#     for attempt in range(1, RETRIES + 1):
#         try:
#             resp = requests.post(BGE_GEN_URL, json=payload, headers=headers, timeout=TIMEOUT)
#             resp.raise_for_status()
#             data = resp.json()
#             # adapt to provider response; assume data["text"] or data["choices"][0]["text"]
#             if "text" in data:
#                 return data["text"]
#             if "choices" in data and len(data["choices"]) > 0:
#                 return data["choices"][0].get("text", "")
#             return str(data)
#         except Exception as e:
#             if attempt == RETRIES:
#                 raise
#             time.sleep(RETRY_BACKOFF * attempt)
#     raise RuntimeError("Generation failed")

import ollama

# def generate_answer(prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
def generate_answer(prompt: str, max_tokens: int = 1024, temperature: float = 0.1) -> str:
    response = ollama.generate(
        model="deepseek-r1:8b",
        # model="qwen3:8b",
        prompt=prompt,
        options={
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    )
    return response["response"]