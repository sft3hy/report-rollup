import pytest
from datetime import datetime, timezone
from pir_search.models import Article
from pir_search.extractor import clean_term, extract_search_terms
from pir_search.api_client import search_mock_db, load_mock_corpus, search_articles
from pir_search.embedder import semantic_filter, embed_query, embed_docs
from pir_search.hybrid import get_ranks, rrf_score, hybrid_rerank
from pir_search.reporter import generate_mock_report, format_report
from pir_search.rag import chunk_article_text, ingest_articles, get_chroma_collection

@pytest.fixture
def mock_articles():
    return [
        Article(
            article_id="ART001",
            title="APT29 targets European infrastructure",
            summary="A report on APT29 cyber espionage attacks against European organizations.",
            full_text="Russian state actors Cozy Bear or APT29 have been observed targetting diplomat computers across Europe using custom backdoors.",
            url="https://example.com/art001",
            published_at=datetime.now(timezone.utc)
        ),
        Article(
            article_id="ART002",
            title="Naval movements in the South China Sea",
            summary="Chinese warships conduct drills near disputed reefs in the South China Sea.",
            full_text="Destroyers and frigates were observed patrolling the maritime corridors near the Paracel Islands, issuing warnings to commercial cargo carriers.",
            url="https://example.com/art002",
            published_at=datetime.now(timezone.utc)
        ),
        Article(
            article_id="ART003",
            title="Critical grid software vulnerability discovered",
            summary="A CVSS 9.8 vulnerability in Siemens SIMATIC WinCC grid control systems has been identified.",
            full_text="Siemens released patches for a remote code execution vulnerability in software managing electrical grid distribution.",
            url="https://example.com/art003",
            published_at=datetime.now(timezone.utc)
        )
    ]

def test_clean_term():
    """Test that terms are properly stripped of punctuation, whitespace, and fillers."""
    assert clean_term("What is APT29 doing?") == "apt29"
    assert clean_term("the current status of energy pipeline") == "energy pipeline"

def test_extractor():
    """Test that extractor extracts a list of search terms from a PIR."""
    pir = "What is Cozy Bear (APT29) doing to target European energy pipelines and SCADA networks?"
    terms = extract_search_terms(pir)
    assert isinstance(terms, list)
    assert len(terms) >= 1
    # Check that at least some key terms are present
    assert any("apt29" in t or "cozy bear" in t or "bear" in t for t in terms)

def test_mock_search(mock_articles):
    """Test that mock database query performs token-based matching and ranking."""
    corpus = [a.model_dump() for a in mock_articles]
    # Update date to string for raw mock dicts
    for c in corpus:
        c["published_at"] = c["published_at"].isoformat()

    results = search_mock_db("APT29 cyber espionage", corpus)
    assert len(results) >= 1
    assert results[0].article_id == "ART001"

    results2 = search_mock_db("South China Sea warships", corpus)
    assert len(results2) >= 1
    assert results2[0].article_id == "ART002"

def test_search_articles_offline(monkeypatch):
    """Test the parallel search API in offline mock mode."""
    # Ensure keys are not active to force offline mock db search
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("NEWSAPI_API_KEY", "")
    terms = ["APT29", "South China Sea"]
    import asyncio
    results = asyncio.run(search_articles(terms))
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(a, Article) for a in results)

def test_embedder_shapes(mock_articles):
    """Test that embedding outputs match FAISS expectations (numpy shapes)."""
    q_emb = embed_query("APT29 operations")
    assert q_emb.ndim == 2
    assert q_emb.shape[0] == 1
    
    doc_embs = embed_docs([a.summary for a in mock_articles])
    assert doc_embs.ndim == 2
    assert doc_embs.shape[0] == len(mock_articles)
    assert q_emb.shape[1] == doc_embs.shape[1]

def test_semantic_filter(mock_articles):
    """Test Stage 2 semantic filter logic via FAISS flat index."""
    filtered_articles, scores = semantic_filter("APT29 European target", mock_articles, top_k=2)
    assert len(filtered_articles) <= 2
    assert len(scores) == len(filtered_articles)
    # The first article should be about APT29 due to semantic match
    assert filtered_articles[0].article_id == "ART001"

def test_ranks_calculation():
    """Test the score to rank mapping helper."""
    scores = [10.0, 50.0, 30.0]
    ranks = get_ranks(scores)
    # 50.0 is index 1, should be rank 0
    # 30.0 is index 2, should be rank 1
    # 10.0 is index 0, should be rank 2
    assert ranks == [2, 0, 1]

def test_rrf_score():
    """Test RRF math."""
    # k = 60
    # rank 0, rank 0: 1/(60+0) + 1/(60+0) = 2/60 = 0.0333
    assert rrf_score(0, 0, k=60) == pytest.approx(1/30)

def test_hybrid_rerank(mock_articles):
    """Test Stage 3 hybrid reranking (BM25 + RRF)."""
    # Force mock scores where ART001 matches semantic query but we search for "SCADA grid" in BM25
    dense_scores = [0.9, 0.4, 0.7] # ART001: 0.9, ART002: 0.4, ART003: 0.7
    # Keywords match ART003 ("critical grid software WinCC SCADA")
    keywords = ["grid", "software", "WinCC", "SCADA"]
    
    top_docs = hybrid_rerank(keywords, mock_articles, dense_scores, k=60, top_n=2)
    assert len(top_docs) == 2
    # ART003 has highest combined ranking (semantic 0.7 = rank 1, keyword = rank 0)
    # ART001 (semantic 0.9 = rank 0, keyword = rank 2)
    # Let's verify that both are in top_docs
    ids = [d.article_id for d in top_docs]
    assert "ART003" in ids
    assert "ART001" in ids

def test_reporter(mock_articles):
    """Test report formatting and mock compiler outputs."""
    report = generate_mock_report("PIR status", mock_articles)
    assert "PIR status" in report
    assert "ART001" in report
    
    formatted = format_report(report, mock_articles)
    assert "== INTELLIGENCE ASSESSMENT ==" in formatted
    assert "== SOURCES ==" in formatted
    assert "[ART001] APT29 targets European infrastructure" in formatted

def test_rag_chunker(mock_articles):
    """Test sentence-bounded chunking."""
    long_text = (
        "This is the first sentence. "
        "This is the second sentence. "
        "And here is the third sentence that is slightly longer to evaluate token limits."
    )
    chunks = chunk_article_text(long_text, target_chunk_tokens=15)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    # Verify sentences are glued back together or split
    assert any("first sentence" in c for c in chunks)

def test_call_llm_fallback(monkeypatch):
    """Test that call_llm falls back gracefully when keys are missing."""
    import pytest
    from pir_search.llm import call_llm
    
    monkeypatch.setenv("SANCTUARY_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    with pytest.raises(ValueError, match="Neither SANCTUARY_KEY nor ANTHROPIC_API_KEY"):
        call_llm("sys", "user")
