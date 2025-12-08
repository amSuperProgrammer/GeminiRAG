import os
import hashlib  # For custom ID hashing
from typing import List, Dict, Any
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack.document_stores.types import DuplicatePolicy  # Updated import
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder
from haystack import Document
from .generator import generate_answer

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
COLLECTION = os.environ.get("QDRANT_COLLECTION", "kb_collection")

doc_store = QdrantDocumentStore(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    prefer_grpc=False,
    index=COLLECTION,
    embedding_dim=1024,
    similarity="cosine"
)

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
            # Generate custom ID: hash of title + chunk for upsert behavior
            id_str = f"{meta.get('title', '')}_{meta.get('chunk', '')}"
            custom_id = hashlib.sha256(id_str.encode()).hexdigest()
            hay_docs.append(Document(content=d["content"], meta=meta, id=custom_id))

        # Embed in batches if needed; SentenceTransformers handles it internally
        embedded_docs = self.doc_embedder.run(documents=hay_docs)["documents"]
        self.doc_store.write_documents(embedded_docs, policy=DuplicatePolicy.OVERWRITE)  # Overwrite if ID matches

    def delete(self, meta_filter: Dict[str, Any]):
        # Build Haystack filter: e.g., {"operator": "AND", "conditions": [{"field": "meta.title", "operator": "==", "value": "test_data.txt"}]}
        conditions = [{"field": f"meta.{k}", "operator": "==", "value": v} for k, v in meta_filter.items()]
        filters = {"operator": "AND", "conditions": conditions} if conditions else None

        # First, find matching documents
        matching_docs = self.doc_store.filter_documents(filters=filters)

        # Extract IDs and delete
        if matching_docs:
            doc_ids = [doc.id for doc in matching_docs]
            self.doc_store.delete_documents(document_ids=doc_ids)
            return {"deleted": len(doc_ids)}
        return {"deleted": 0}

    # def query(self, query_text: str, top_k: int = 5):
    def query(self, query_text: str, top_k: int = 10):
        query_emb = self.text_embedder.run(text=query_text)["embedding"]
        hits = self.retriever.run(query_embedding=query_emb, top_k=top_k)["documents"]
        context = "\n\n".join([h.content for h in hits])
        # prompt = f"Context:\n{context}\n\nQuestion: {query_text}\n\nAnswer:"
        # prompt = f"Context:\n{context}\n\nQuestion: {query_text}\n\nExtract and display the full table from the context, including all years (historical and forecasted), rows, columns, and any additional summary notes or statistics. Format it exactly as a markdown table. Do not omit or abbreviate any part. If forecasts or notes are present, include them below the table.\nAnswer:"
        # prompt = f"Context:\n{context}\n\nQuestion: {query_text}\n\nAnswer the question accurately based only on the provided context. Extract and include ONLY the relevant information requested in the question. If the question asks for specific data (e.g., a single year), provide just that—do not include extra rows or full tables unless asked. Format any tabular data as a markdown table using pipe | syntax, without code fences like ```. Place any notes as bullet points below if relevant to the query. Do not add unrequested information.\nAnswer:" # Deepseek prompt.
        prompt = f"Context:\n{context}\n\nQuestion: {query_text}\n\nAnswer the question accurately based only on the provided context. Extract and include ONLY the relevant information requested in the question. If the question asks for specific data (e.g., a single year), provide just that—do not include extra rows, full tables, notes, summaries, or explanations unless asked. Do NOT add any notes, bullets, or additional text like 'Примечания' or comments. Format any tabular data as a markdown table using pipe | syntax, without code fences like ```. Do not omit or abbreviate any part, but keep the response minimal and exact to the query.\nAnswer:" # Deepseek prompt.
        answer = generate_answer(prompt)
        # sources = [{"title": h.meta.get("title", "doc"), "score": float(h.score or 0.0)} for h in hits]
        # return {"answer": answer, "sources": sources}
        return {"answer": answer}

text_embedder = SentenceTransformersTextEmbedder(model="BAAI/bge-m3")
doc_embedder = SentenceTransformersDocumentEmbedder(model="BAAI/bge-m3")
retriever = QdrantEmbeddingRetriever(document_store=doc_store)
rag_service = RAGService(retriever=retriever, doc_store=doc_store, text_embedder=text_embedder, doc_embedder=doc_embedder)

print("Warming up text embedder...")
text_embedder.warm_up()   # this triggers the actual load/download

print("Warming up document embedder...")
doc_embedder.warm_up()
