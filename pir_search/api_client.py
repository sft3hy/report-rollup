import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import httpx
from dotenv import load_dotenv
from rich.console import Console

from pir_search.models import Article

# Ensure env variables are loaded
load_dotenv()

console = Console()

MOCK_DB_PATH = Path(__file__).parent / "resources" / "mock_articles.json"

def load_mock_corpus() -> list[dict]:
    """Loads the static mock database from JSON file."""
    if not MOCK_DB_PATH.exists():
        return []
    try:
        with open(MOCK_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading mock articles DB: {e}[/red]")
        return []

def search_mock_db(term: str, corpus: list[dict]) -> list[Article]:
    """
    Locally queries the mock corpus. Matches search term tokens
    against titles, summaries, and full texts, and returns sorted results.
    """
    # Split term into words of length > 2
    tokens = [t.lower() for t in term.split() if len(t) > 2]
    if not tokens:
        tokens = [term.lower()]

    scored_articles = []
    for art in corpus:
        score = 0
        title_lower = art["title"].lower()
        summary_lower = art["summary"].lower()
        full_text_lower = art["full_text"].lower()

        for token in tokens:
            if token in title_lower:
                score += 5
            if token in summary_lower:
                score += 3
            if token in full_text_lower:
                score += 1

        if score > 0:
            scored_articles.append((score, art))

    # Sort by score descending
    scored_articles.sort(key=lambda x: x[0], reverse=True)
    
    # Map raw dicts to Article objects
    results = []
    for _, art in scored_articles[:15]:
        try:
            # Parse datetime string
            pub_date = datetime.fromisoformat(art["published_at"].replace("Z", "+00:00"))
            results.append(Article(
                article_id=art["article_id"],
                title=art["title"],
                summary=art["summary"],
                full_text=art["full_text"],
                url=art["url"],
                published_at=pub_date
            ))
        except Exception as e:
            # Fallback if parsing date fails
            results.append(Article(
                article_id=art["article_id"],
                title=art["title"],
                summary=art["summary"],
                full_text=art["full_text"],
                url=art["url"],
                published_at=datetime.now(timezone.utc)
            ))
    return results

async def search_tavily(client: httpx.AsyncClient, term: str, api_key: str) -> list[Article]:
    """Queries Tavily API for the given search term."""
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": term,
        "search_depth": "basic",
        "max_results": 15
    }
    try:
        response = await client.post(url, json=payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        
        articles = []
        for res in results:
            # Generate a consistent ID based on title
            art_id = f"TAV_{hash(res['title']) & 0xffffffff:08x}"
            published_at = datetime.now(timezone.utc)
            pub_date_str = res.get("published_date") or res.get("raw_date")
            if pub_date_str:
                try:
                    # Clean up some common variations in datetime formats
                    clean_date = pub_date_str.split(".")[0].replace("Z", "+00:00")
                    published_at = datetime.fromisoformat(clean_date)
                except Exception:
                    pass

            articles.append(Article(
                article_id=art_id,
                title=res["title"],
                summary=res.get("content", "")[:300],
                full_text=res.get("content", ""),
                url=res["url"],
                published_at=published_at
            ))
        return articles
    except Exception as e:
        console.print(f"[yellow]Tavily search failed for '{term}': {e}. Falling back to mock.[/yellow]")
        return []

async def search_newsapi(client: httpx.AsyncClient, term: str, api_key: str) -> list[Article]:
    """Queries NewsAPI for the given search term."""
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": term,
        "pageSize": 15,
        "apiKey": api_key
    }
    try:
        response = await client.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        results = data.get("articles", [])
        
        articles = []
        for res in results:
            if not res.get("title") or not res.get("url"):
                continue
            art_id = f"NWS_{hash(res['title']) & 0xffffffff:08x}"
            published_at = datetime.now(timezone.utc)
            pub_str = res.get("publishedAt")
            if pub_str:
                try:
                    published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            articles.append(Article(
                article_id=art_id,
                title=res["title"],
                summary=res.get("description") or "",
                full_text=res.get("content") or res.get("description") or "",
                url=res["url"],
                published_at=published_at
            ))
        return articles
    except Exception as e:
        console.print(f"[yellow]NewsAPI search failed for '{term}': {e}. Falling back to mock.[/yellow]")
        return []

async def search_articles(terms: list[str]) -> list[Article]:
    """
    Performs searches in parallel across all terms using asyncio.TaskGroup.
    Deduplicates final results by article_id and caps them at 100.
    """
    tavily_key = os.getenv("TAVILY_API_KEY")
    newsapi_key = os.getenv("NEWSAPI_API_KEY")
    
    # Decide which backend to use. Prioritize Tavily, then NewsAPI, otherwise Mock.
    # Note: If key is present but empty, treat it as unset.
    use_tavily = bool(tavily_key and tavily_key.strip())
    use_newsapi = bool(newsapi_key and newsapi_key.strip())
    
    all_results = []
    
    if not use_tavily and not use_newsapi:
        # Offline mode - use mock DB
        corpus = load_mock_corpus()
        for term in terms:
            all_results.extend(search_mock_db(term, corpus))
    else:
        # Online mode - perform concurrent requests using httpx
        async with httpx.AsyncClient() as client:
            async with asyncio.TaskGroup() as tg:
                tasks = []
                for term in terms:
                    if use_tavily:
                        tasks.append(tg.create_task(search_tavily(client, term, tavily_key)))
                    elif use_newsapi:
                        tasks.append(tg.create_task(search_newsapi(client, term, newsapi_key)))
            
            # Collect results after the TaskGroup has successfully exited and completed all tasks
            for task in tasks:
                all_results.extend(task.result())

    # Deduplicate by article_id
    seen_ids = set()
    deduped_articles = []
    for art in all_results:
        if art.article_id not in seen_ids:
            seen_ids.add(art.article_id)
            deduped_articles.append(art)
            
    # Cap at 100 articles
    return deduped_articles[:100]
