import os
import hashlib
from typing import List, Dict, Any
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack import Document
import google.generativeai as genai
from .generator import generate_answer

# ================== CONFIG ==================
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION = os.environ.get("QDRANT_COLLECTION", "kb_collection")

GEMINI_EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
GEMINI_EMBED_DIM = int(os.environ.get("GEMINI_EMBED_DIM", "768"))  # 768 = best balance (supports 128–3072)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY environment variable is required")
genai.configure(api_key=GEMINI_API_KEY)

doc_store = QdrantDocumentStore(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    prefer_grpc=False,
    index=COLLECTION,
    embedding_dim=GEMINI_EMBED_DIM,
    similarity="cosine"
)

# ================== GEMINI EMBEDDERS ==================
class GeminiTextEmbedder:
    def __init__(self, model: str = GEMINI_EMBED_MODEL, dim: int = GEMINI_EMBED_DIM):
        self.model = model
        self.dim = dim

    def run(self, text: str) -> Dict[str, Any]:
        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type="RETRIEVAL_QUERY",          # ← Uppercase required now
            output_dimensionality=self.dim
        )
        # print("Embed response:", result)

        emb = result.get("embedding")
        if not emb:
            raise ValueError(f"Gemini embed_content returned no embedding: {result}")
        return {"embedding": emb}
        # return {"embedding": result['embedding']}

    def warm_up(self):
        self.run("warmup query")

class GeminiDocumentEmbedder:
    def __init__(self, model: str = GEMINI_EMBED_MODEL, dim: int = GEMINI_EMBED_DIM):
        self.model = model
        self.dim = dim

    def run(self, documents: List[Document]) -> Dict[str, List[Document]]:
        texts = [doc.content for doc in documents]
        result = genai.embed_content(
            model=self.model,
            content=texts,                         # Batch supported natively
            task_type="RETRIEVAL_DOCUMENT",        # ← Uppercase required now
            output_dimensionality=self.dim
        )
        embeddings = result['embedding']

        for doc, emb in zip(documents, embeddings):
            doc.embedding = emb

        return {"documents": documents}

    def warm_up(self):
        self.run([Document(content="warmup document")])

# ================== RAG SERVICE ==================
class RAGService:
    def __init__(self, retriever, doc_store, text_embedder, doc_embedder):
        self.retriever = retriever
        self.doc_store = doc_store
        self.text_embedder = text_embedder
        self.doc_embedder = doc_embedder

    def ingest(self, docs: List[Dict[str, Any]]):
        hay_docs = []
        for d in docs:
            meta = d.get("meta", {})
            id_str = f"{meta.get('title', '')}_{meta.get('chunk', '')}"
            custom_id = hashlib.sha256(id_str.encode()).hexdigest()
            hay_docs.append(Document(content=d["content"], meta=meta, id=custom_id))

        embedded_docs = self.doc_embedder.run(documents=hay_docs)["documents"]
        self.doc_store.write_documents(embedded_docs, policy=DuplicatePolicy.OVERWRITE)

    def delete(self, meta_filter: Dict[str, Any]):
        conditions = [{"field": f"meta.{k}", "operator": "==", "value": v} for k, v in meta_filter.items()]
        filters = {"operator": "AND", "conditions": conditions} if conditions else None
        matching_docs = self.doc_store.filter_documents(filters=filters)
        if matching_docs:
            doc_ids = [doc.id for doc in matching_docs]
            self.doc_store.delete_documents(document_ids=doc_ids)
            return {"deleted": len(doc_ids)}
        return {"deleted": 0}

    def query(self, query_text: str, top_k: int = 10):
        query_emb = self.text_embedder.run(text=query_text)["embedding"]
        hits = self.retriever.run(query_embedding=query_emb, top_k=top_k)["documents"]
        # print("Retriever hits:", hits)
        context = "\n\n".join([h.content for h in hits])

        # if not context.strip():
        #     return {"answer": "No relevant information found in the knowledge base."}

        prompt = f"""Use ONLY the following context to answer the question.
You MUST detect the language of the question below and respond ONLY in that language.
If the context does not contain relevant information to answer the question, respond with 'No relevant information found in the knowledge base.'
If the question asks for a table, return it as clean markdown (no code fences).
If it asks for a single number/year, return only that value.

Context:
{context}

Question: {query_text}

Answer:"""

#         prompt = f"""Use ONLY the following context to answer the question.
# Do not add any information that is not present in the context.
# If the context does not contain relevant information to answer the question, respond with 'No relevant information found in the knowledge base.'
# If the question asks for a table, return it as clean markdown (no code fences).
# If it asks for a single number/year, return only that value.
#
# Context:
# {context}
#
# Question: {query_text}
#
# Answer:"""

        try:
            answer = generate_answer(prompt)
        except Exception as e:
            return {"answer": f"Generation failed: {str(e)}"}
        return {"answer": answer}

# Initialize
text_embedder = GeminiTextEmbedder()
doc_embedder = GeminiDocumentEmbedder()
retriever = QdrantEmbeddingRetriever(document_store=doc_store)
rag_service = RAGService(retriever=retriever, doc_store=doc_store, text_embedder=text_embedder, doc_embedder=doc_embedder)

print("Warming up Gemini embedders...")
text_embedder.warm_up()
doc_embedder.warm_up()
print(f"Using {GEMINI_EMBED_MODEL} @ {GEMINI_EMBED_DIM}-dim")