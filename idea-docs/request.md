## Embedding model recommendation

Based on the current MTEB leaderboard landscape, use **`BAAI/bge-base-en-v1.5`** for v1. It sits at the sweet spot for this use case:

for limited infrastructure where GPU memory isn't guaranteed, MiniLM is cost-efficient, but for accuracy-critical retrieval systems, BGE is worth the modest extra investment. It runs locally, needs no API key, fits in CPU RAM at 438MB, and uses instruction prefixes for task specialization — `search_query:` for the PIR and `search_document:` for article summaries — enabling flexible retrieval without swapping models. If you have a GPU later, swap to `BAAI/bge-large-en-v1.5` or `Qwen3-Embedding-0.6B` with zero code changes.

---

## Project structure

```
pir_search/
├── pir_search/
│   ├── __init__.py
│   ├── extractor.py        # Stage 1 — NLP entity/keyword extraction
│   ├── api_client.py       # Stage 1 — mock + real search API
│   ├── embedder.py         # Stage 2 — embedding + FAISS semantic filter
│   ├── hybrid.py           # Stage 3 — BM25 + RRF reranker
│   ├── reporter.py         # Stage 4 — LLM report generation
│   ├── rag.py              # Stretch — ChromaDB weekly store
│   └── models.py           # Pydantic data models
├── tests/
│   └── test_pipeline.py
├── pyproject.toml
└── .env
```

---

## Stage-by-stage plan

### Stage 1 — PIR parsing and search (extractor + api_client)

**Goal:** turn a one-liner PIR into 100 deduplicated candidate articles.

`extractor.py` uses **spaCy** (`en_core_web_sm`) to run NER over the PIR text, pulling `GPE`, `ORG`, `PERSON`, `NORP`, and `EVENT` entity types as hard keywords. Then **KeyBERT** (also uses sentence-transformers under the hood) extracts the top 5–8 noun-phrase keywords. Stop-words, articles, and filler are stripped with a small regex filter. You end up with 8–15 distinct search terms to pass to the API.

`api_client.py` runs those terms in parallel `asyncio` tasks (use `httpx.AsyncClient`). Each query returns up to 15 results. Responses are merged, duplicate `article_id` values dropped, and capped at 100. The mock API generates fake articles from a template JSON so you can develop offline.

Data model (Pydantic):
```python
class Article(BaseModel):
    article_id: str
    title: str
    summary: str
    full_text: str
    url: str
    published_at: datetime
```

Python 3.13 specifics: use `asyncio.TaskGroup` (stable in 3.11+, idiomatic in 3.13) instead of `asyncio.gather` for structured concurrency. Type all functions with `str | None` union syntax, not `Optional[str]`.

---

### Stage 2 — Semantic filtering with BGE (embedder.py)

**Goal:** 100 articles → top 50 by cosine similarity to PIR.

```python
from sentence_transformers import SentenceTransformer
import faiss, numpy as np

model = SentenceTransformer("BAAI/bge-base-en-v1.5")

def embed_query(pir: str) -> np.ndarray:
    return model.encode(f"Represent this query for retrieving relevant documents: {pir}",
                        normalize_embeddings=True)

def embed_docs(summaries: list[str]) -> np.ndarray:
    prefixed = [f"Represent this document for retrieval: {s}" for s in summaries]
    return model.encode(prefixed, batch_size=32, normalize_embeddings=True)
```

Generate embeddings for all documents and index them in FAISS. For a query, retrieve top-k results from both BM25 and vector search, then normalize scores before combining. For Stage 2, use `faiss.IndexFlatIP` (inner product on normalized vectors = cosine similarity). Retrieve the top 50 by score. No HNSW needed at this scale — flat index is exact and fast for 100 docs.

BGE instruction prefix tip: the model was trained with query/document asymmetry. Prefixing the PIR with the query instruction and the summaries with the document instruction gives a measurable retrieval quality boost over bare text.

---

### Stage 3 — Hybrid reranking with RRF (hybrid.py)

**Goal:** 50 articles → top 10 using combined BM25 + dense scores.

RRF fusion requires no tuning — use k=60 and it just works across score scales. Hybrid search improves recall 15–30% over single methods with minimal added complexity.

```python
from rank_bm25 import BM25Okapi

def rrf_score(bm25_rank: int, dense_rank: int, k: int = 60) -> float:
    return 1/(k + bm25_rank) + 1/(k + dense_rank)
```

Steps inside `hybrid.py`:
1. Build a `BM25Okapi` index over the 50 article summaries (tokenize with `.split()` for speed, or spaCy tokens for quality).
2. Score the PIR keywords against BM25 → rank list.
3. Use the already-computed FAISS scores from Stage 2 → dense rank list.
4. Compute RRF for each article → sort → take top 10.

This stage takes milliseconds on 50 docs — no batching concerns.

---

### Stage 4 — LLM report generation (reporter.py)

**Goal:** 10 articles → structured intelligence summary with citations.

Use the Anthropic SDK with a structured prompt. Keep the full text of all 10 articles in context (modern models handle this fine). The prompt template:

```python
SYSTEM = """You are an intelligence analyst. Given a Priority Intelligence Requirement (PIR)
and a set of reporting articles, produce a structured assessment that:
1. Directly answers the PIR based on the evidence
2. Highlights key entities, locations, and events
3. Notes confidence level and information gaps
4. Cites articles by their ID using [ID] notation"""

def build_user_prompt(pir: str, articles: list[Article]) -> str:
    docs = "\n\n".join(
        f"[{a.article_id}] {a.title}\n{a.full_text}"
        for a in articles
    )
    return f"PIR: {pir}\n\n---\n{docs}"
```

Print the LLM response followed by a reference list:
```
== INTELLIGENCE ASSESSMENT ==
[response text with inline citations]

== SOURCES ==
[ID001] Title — https://...
[ID002] Title — https://...
```

---

### Stretch goal — RAG follow-up (rag.py)

**Goal:** "Tell me more about X" answers grounded in the full weekly article corpus.

Use **ChromaDB** (local, no server needed) to persist embeddings across sessions. A nightly ingest job chunks `full_text` into ~512-token windows (split on sentence boundaries with spaCy), embeds with the same BGE model, and upserts into a ChromaDB collection keyed by `article_id + chunk_index`.

Hybrid search retrieves results from both keyword search and semantic search, ranks the output, and sends the most relevant documents to the LLM — improving accuracy and reducing hallucinations by keeping the model grounded in real data.

At query time: embed the follow-up question, retrieve top-8 chunks, stuff into a Claude prompt with the original report as context.

```python
import chromadb
from chromadb.utils import embedding_functions

ef = embedding_functions.SentenceTransformerEmbeddingFunction("BAAI/bge-base-en-v1.5")
client = chromadb.PersistentClient(path="./chroma_store")
collection = client.get_or_create_collection("weekly_articles", embedding_function=ef)
```

---

## Dependency stack

```toml
[project]
name = "pir-search"
requires-python = ">=3.13"
dependencies = [
    "anthropic>=0.40",
    "sentence-transformers>=3.3",
    "faiss-cpu>=1.8",
    "rank-bm25>=0.2",
    "spacy>=3.8",
    "keybert>=0.8",
    "httpx>=0.28",
    "pydantic>=2.9",
    "chromadb>=0.6",      # stretch goal
    "rich>=13",           # pretty terminal output
    "python-dotenv>=1.0",
]
```

After install: `python -m spacy download en_core_web_sm`

---

## Build order for v1

1. `models.py` + mock API → get real JSON flowing through the system end-to-end in one afternoon.
2. `extractor.py` → verify keyword extraction on a handful of real PIR examples before touching embeddings.
3. `embedder.py` → wire Stage 2, confirm top-50 results make intuitive sense.
4. `hybrid.py` → add BM25 + RRF, verify the top-10 cut looks cleaner than semantic alone.
5. `reporter.py` → write the prompt, test with Claude, tune the output format.
6. CLI entry point (`__main__.py`) → `python -m pir_search "What is adversary X doing in region Y?"`.
7. `rag.py` → stretch goal, add after v1 is stable.

Each step is independently testable with a small `pytest` fixture that feeds mock articles — you never need the live API to develop any individual component.