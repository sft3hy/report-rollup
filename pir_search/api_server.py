import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pir_search.extractor import extract_search_terms
from pir_search.api_client import search_articles
from pir_search.embedder import semantic_filter
from pir_search.hybrid import hybrid_rerank
from pir_search.reporter import generate_report, format_report
from pir_search.rag import ingest_articles, query_rag

app = FastAPI(title="PIR Intelligence Pipeline API", version="0.1.0")

# Configure CORS middleware to enable Vite development server access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PIRRequest(BaseModel):
    query: str

class QARequest(BaseModel):
    question: str
    original_report: str

@app.post("/assess")
async def assess_pir(request: PIRRequest):
    """
    POST endpoint to run the full PIR assessment pipeline.
    Accepts a Priority Intelligence Requirement query, extracts terms,
    performs search, semantic filters, hybrid reranks, queries Claude,
    and returns the structured intelligence report while ingesting to RAG.
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # 1. NLP Extraction
        terms = extract_search_terms(query)
        
        # 2. Parallel Search
        candidates = await search_articles(terms)
        if not candidates:
            return {
                "report": "No relevant articles were found to generate an assessment.",
                "formatted_report": "No relevant articles were found to generate an assessment.",
                "sources": []
            }

        # 3. Semantic Vector Filtering (Nomic + FAISS)
        filtered, dense_scores = semantic_filter(query, candidates, top_k=50)

        # 4. Hybrid Reranking (BM25 + RRF)
        top_articles = hybrid_rerank(terms, filtered, dense_scores, k=60, top_n=10)

        # 5. LLM Report Generation (Claude / Mock Fallback)
        raw_report = generate_report(query, top_articles)
        formatted = format_report(raw_report, top_articles)

        # 6. RAG Ingestion into ChromaDB
        ingest_articles(top_articles)

        return {
            "report": raw_report,
            "formatted_report": formatted,
            "sources": [
                {
                    "article_id": a.article_id,
                    "title": a.title,
                    "url": a.url
                }
                for a in top_articles
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_followup(request: QARequest):
    """
    POST endpoint to query the ChromaDB RAG store for follow-up questions.
    Returns the answer grounded in the ingested sources context.
    """
    question = request.question.strip()
    original_report = request.original_report.strip()
    
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        answer = query_rag(question, original_report)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount built React static files if they exist in production
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

if __name__ == "__main__":
    # Host on 0.0.0.0 for containerized execution
    # Scan for SSL certificates to serve application over HTTPS
    ssl_cert = "/etc/certs/cosmic.crt"
    ssl_key = "/etc/certs/cosmic.key"
    ssl_ca = "/etc/certs/ca-bundle.crt"

    if not os.path.exists(ssl_cert):
        ssl_cert = os.path.expanduser("~/dev/certs/cosmic.crt")
        ssl_key = os.path.expanduser("~/dev/certs/cosmic.key")
        ssl_ca = os.path.expanduser("~/dev/certs/ca-bundle.crt")

    uvicorn_kwargs = {
        "host": "0.0.0.0",
        "port": 8000
    }

    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        print(f"SSL Certificates detected. Running in HTTPS mode.")
        uvicorn_kwargs["ssl_certfile"] = ssl_cert
        uvicorn_kwargs["ssl_keyfile"] = ssl_key
        if os.path.exists(ssl_ca):
            uvicorn_kwargs["ssl_ca_certs"] = ssl_ca

    uvicorn.run("pir_search.api_server:app", **uvicorn_kwargs)
