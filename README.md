# PIR Intelligence Pipeline

A structured NLP and semantic search pipeline for analyzing Priority Intelligence Requirements (PIRs).

## Features
- Extractor (spaCy NER + KeyBERT)
- Parallel Search client (httpx + asyncio TaskGroup)
- Vector Filtering (BGE embeddings + FAISS)
- Hybrid Reranking (BM25Okapi + Reciprocal Rank Fusion)
- Intelligence Reporter (Claude + sources list)
- RAG Store (ChromaDB collection for follow-up QA)

## Installation & Run
```bash
uv sync --python 3.13
.venv/bin/python -m spacy download en_core_web_sm
.venv/bin/python -m pir_search "Your PIR query here"
```
