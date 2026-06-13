import re
import numpy as np
from rank_bm25 import BM25Okapi

from pir_search.models import Article

def tokenize(text: str) -> list[str]:
    """Helper to lowercase and tokenize text by words."""
    # Convert to lowercase and find all word tokens
    return re.findall(r"\w+", text.lower())

def get_ranks(scores: list[float]) -> list[int]:
    """
    Given a list of scores, returns a list of ranks (0-indexed).
    The highest score receives rank 0, the next highest rank 1, etc.
    """
    sorted_indices = np.argsort(scores)[::-1]
    ranks = np.zeros(len(scores), dtype=int)
    for rank, idx in enumerate(sorted_indices):
        ranks[idx] = rank
    return list(ranks)

def rrf_score(bm25_rank: int, dense_rank: int, k: int = 60) -> float:
    """Computes the Reciprocal Rank Fusion (RRF) score for a document."""
    return 1 / (k + bm25_rank) + 1 / (k + dense_rank)

def hybrid_rerank(
    pir_keywords: list[str],
    articles: list[Article],
    dense_scores: list[float],
    k: int = 60,
    top_n: int = 10
) -> list[Article]:
    """
    Stage 3: Hybrid reranking using BM25 and dense scores.
    Combines ranks using Reciprocal Rank Fusion (RRF) and returns the top_n articles.
    """
    if not articles:
        return []

    # 1. Build BM25 index over the filtered article summaries
    tokenized_corpus = [tokenize(art.summary) for art in articles]
    bm25 = BM25Okapi(tokenized_corpus)

    # 2. Tokenize the PIR keywords as the BM25 query
    combined_query_str = " ".join(pir_keywords)
    tokenized_query = tokenize(combined_query_str)

    # 3. Score articles using BM25
    bm25_scores = list(bm25.get_scores(tokenized_query))

    # 4. Compute ranks for both BM25 and dense scores
    bm25_ranks = get_ranks(bm25_scores)
    dense_ranks = get_ranks(dense_scores)

    # 5. Compute RRF scores for all articles
    fused_results = []
    for i, article in enumerate(articles):
        score = rrf_score(bm25_ranks[i], dense_ranks[i], k=k)
        fused_results.append((score, article))

    # 6. Sort by RRF score descending and return top_n
    fused_results.sort(key=lambda x: x[0], reverse=True)
    return [art for _, art in fused_results[:top_n]]
