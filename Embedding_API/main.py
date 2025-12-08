from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from google.genai import types
from  dotenv import load_dotenv
import os
import re
from fastapi import HTTPException
from typing import List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Инициализация FastAPI
app = FastAPI(title="Text Chunking & Embedding API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить любые источники (в т.ч. Origin: null)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройка Gemini API
GEMINI_APIKEY = os.getenv("GEMINI_APIKEY")
if not GEMINI_APIKEY:
    raise ValueError("GEMINI_APIKEY не установлен")

client = genai.Client(api_key=GEMINI_APIKEY)

# Модели данных
class DocumentRequest(BaseModel):
    text: str
    chunk_size: Optional[int] = 1200  # токенов
    overlap: Optional[int] = 250      # токенов перекрытия
    title: Optional[str] = None

class ChunkInfo(BaseModel):
    chunk_id: int
    text: str
    embedding: List[float]

class DocumentEmbeddingResponse(BaseModel):
    chunks: List[ChunkInfo]
    total_chunks: int
    dimension: int
    original_length: int

#region Функция разбиения текста на чанки (depicated)
# def split_into_chunks(text: str, chunk_size: int = 1200, overlap: int = 250) -> List[dict]:
#     """
#     Разбивает текст на логические чанки с перекрытием
#     """
#     # Примерно 1 токен = 4 символа для русского текста
#     chars_per_chunk = chunk_size * 4
#     overlap_chars = overlap * 4
    
#     chunks = []
    
#     # Сначала пробуем разбить по абзацам
#     paragraphs = text.split('\n\n')
    
#     current_chunk = ""
#     start_pos = 0
    
#     for para in paragraphs:
#         para = para.strip()
#         if not para:
#             continue
        
#         # Если текущий чанк + параграф не превышает лимит
#         if len(current_chunk) + len(para) < chars_per_chunk:
#             current_chunk += para + "\n\n"
#         else:
#             # Сохраняем текущий чанк
#             if current_chunk:
#                 chunk_text = current_chunk.strip()
#                 chunks.append({
#                     "text": chunk_text,
#                     "start_pos": start_pos,
#                     "end_pos": start_pos + len(chunk_text)
#                 })
                
#                 # Начинаем новый чанк с перекрытием
#                 overlap_text = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else current_chunk
#                 start_pos = start_pos + len(current_chunk) - len(overlap_text)
#                 current_chunk = overlap_text + para + "\n\n"
#             else:
#                 # Если параграф сам слишком большой, разбиваем по предложениям
#                 if len(para) > chars_per_chunk:
#                     sentences = re.split(r'(?<=[.!?])\s+', para)
#                     for sentence in sentences:
#                         if len(current_chunk) + len(sentence) < chars_per_chunk:
#                             current_chunk += sentence + " "
#                         else:
#                             if current_chunk:
#                                 chunk_text = current_chunk.strip()
#                                 chunks.append({
#                                     "text": chunk_text,
#                                     "start_pos": start_pos,
#                                     "end_pos": start_pos + len(chunk_text)
#                                 })
#                                 overlap_text = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else current_chunk
#                                 start_pos = start_pos + len(current_chunk) - len(overlap_text)
#                                 current_chunk = overlap_text + sentence + " "
#                             else:
#                                 current_chunk = sentence + " "
#                 else:
#                     current_chunk = para + "\n\n"
    
#     # Добавляем последний чанк
#     if current_chunk.strip():
#         chunk_text = current_chunk.strip()
#         chunks.append({
#             "text": chunk_text,
#             "start_pos": start_pos,
#             "end_pos": start_pos + len(chunk_text)
#         })
    
#     return chunks
#endregion

@app.post("/chunks_get")
async def chunks_get(request: DocumentRequest):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=request.chunk_size * 4,
        chunk_overlap=request.overlap * 4,
        separators=["\n\n", "\n", " ", ""],
        keep_separator=False,
    )

    chunks = splitter.split_text(request.text)

    docs = [
        {
            "content": chunk,
            "meta": {
                "title": request.title,
                "chunk": i
            }
        }
        for i, chunk in enumerate(chunks)
    ]

    return docs

# Основной эндпоинт
@app.post("/process", response_model=DocumentEmbeddingResponse)
async def process_document(request: DocumentRequest):
    """
    Принимает большой текст, разбивает на чанки и создает эмбеддинги
    
    Параметры:
    - text: исходный текст
    - chunk_size: размер чанка в токенах (по умолчанию 1200)
    - overlap: размер перекрытия в токенах (по умолчанию 250)
    - title: опциональный заголовок документа
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=request.chunk_size*4,
        chunk_overlap=request.overlap*4,
        separators=["\n\n", "\n", " ", ""],
        keep_separator=False,
    )
    try:
        # Разбиваем текст на чанки
        chunks = text_splitter.split_text(request.text)
        
        # Создаем эмбеддинги для каждого чанка
        chunk_infos = []
        
        for i, chunk in enumerate(chunks):
            # Получаем эмбеддинг
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=chunk,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            
            chunk_infos.append(ChunkInfo(
                chunk_id=i,
                text=chunk,
                embedding=result.embeddings[0].values,
            ))
        
        return DocumentEmbeddingResponse(
            chunks=chunk_infos,
            total_chunks=len(chunk_infos),
            dimension=len(chunk_infos[0].embedding) if chunk_infos else 0,
            original_length=len(request.text)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")

# Эндпоинт только для разбиения (без эмбеддингов)
@app.post("/chunks-only")
async def get_chunks_only(request: DocumentRequest):
    """
    Только разбивает текст на чанки без создания эмбеддингов
    Полезно для тестирования разбиения
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=request.chunk_size*4,
        chunk_overlap=request.overlap*4,
        separators=["\n\n", "\n", " ", ""],
        keep_separator=False,
    )
    try:
        print(type(request.text))
        chunks = text_splitter.split_text(request.text)
        
        return {
            "chunks": [
                {
                    "chunk_id": i,
                    "text": chunk,
                    "length": len(chunk)
                }
                for i, chunk in enumerate(chunks)
            ],
            "total_chunks": len(chunks),
            "original_length": len(request.text)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

# Проверка здоровья API
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "model": "text-embedding-001",
        "features": ["chunking", "embedding"]
    }

@app.get("/")
async def root():
    return {
        "message": "Text Chunking & Embedding API",
        "endpoints": {
            "/process": "POST - разбить текст на чанки и создать эмбеддинги",
            "/chunks-only": "POST - только разбить текст (для тестирования)",
            "/health": "GET - проверка статуса",
            "/docs": "GET - документация"
        }
    }

# Запуск напрямую из скрипта
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",  # или просто app, если запускаешь из этого же файла
        host="0.0.0.0",
        port=8005,
        reload=True  # автоперезагрузка при изменениях
    )