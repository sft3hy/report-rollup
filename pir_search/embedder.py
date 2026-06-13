import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from rich.console import Console

from pir_search.models import Article

console = Console()

_model = None

def get_nomic_model() -> SentenceTransformer:
    """Lazy-loads and caches the nomic-ai/nomic-embed-text-v1.5 model."""
    global _model
    if _model is None:
        console.print("[blue]Loading Nomic embedding model (nomic-ai/nomic-embed-text-v1.5)...[/blue]")
        # Pass trust_remote_code=True for Nomic model loading
        _model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
        console.print("[green]Nomic model loaded successfully.[/green]")
    return _model

def embed_query(pir: str) -> np.ndarray:
    """Generates a normalized embedding for the query with the Nomic query instruction prefix."""
    model = get_nomic_model()
    # Nomic v1.5 query prefix
    text = f"search_query: {pir}"
    embedding = model.encode(text, normalize_embeddings=True)
    # Ensure it's a 2D numpy array of shape (1, dim)
    return np.ascontiguousarray(np.expand_dims(embedding, axis=0).astype("float32"))

def embed_docs(summaries: list[str]) -> np.ndarray:
    """Generates normalized embeddings for a list of document summaries with the Nomic document prefix."""
    model = get_nomic_model()
    # Nomic v1.5 document prefix
    prefixed = [f"search_document: {s}" for s in summaries]
    embeddings = model.encode(prefixed, batch_size=32, normalize_embeddings=True)
    return np.ascontiguousarray(embeddings.astype("float32"))

def semantic_filter(pir: str, articles: list[Article], top_k: int = 50) -> tuple[list[Article], list[float]]:
    """
    Stage 2: Semantic filtering of articles.
    Returns the top_k articles (up to 50) and their cosine similarity scores.
    """
    if not articles:
        return [], []

    # 1. Embed query and document summaries
    q_emb = embed_query(pir)
    summaries = [art.summary for art in articles]
    doc_embs = embed_docs(summaries)

    # 2. Index in FAISS
    dimension = doc_embs.shape[1]
    # Flat IP (Inner Product) on L2-normalized vectors represents Cosine Similarity
    index = faiss.IndexFlatIP(dimension)
    index.add(doc_embs)

    # 3. Retrieve scores and indices
    k = min(top_k, len(articles))
    scores, indices = index.search(q_emb, k)

    # Extract results
    filtered_articles = []
    filtered_scores = []
    
    # scores and indices are arrays of shape (1, k)
    for idx, score in zip(indices[0], scores[0]):
        if idx == -1:  # FAISS padding if fewer than k items found
            continue
        filtered_articles.append(articles[idx])
        # Force float conversion
        filtered_scores.append(float(score))

    return filtered_articles, filtered_scores
