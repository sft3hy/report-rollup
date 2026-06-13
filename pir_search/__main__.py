import sys
import asyncio
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Import pipeline components
from pir_search.extractor import extract_search_terms
from pir_search.api_client import search_articles
from pir_search.embedder import semantic_filter
from pir_search.hybrid import hybrid_rerank
from pir_search.reporter import generate_report, format_report
from pir_search.rag import ingest_articles, query_rag

console = Console()

async def run_pipeline(pir_query: str):
    """Executes the complete end-to-end PIR intelligence pipeline."""
    console.print(
        Panel.fit(
            f"[bold green]Starting PIR Intelligence Pipeline[/bold green]\n"
            f"[bold white]Query:[/bold white] [italic cyan]{pir_query}[/italic cyan]",
            border_style="green",
            title="SYSTEM INITIALIZATION"
        )
    )

    # --- STAGE 1: NLP Extraction ---
    with console.status("[bold blue]Stage 1: Running spaCy NER & KeyBERT keyword extraction...[/bold blue]"):
        terms = extract_search_terms(pir_query)
    
    console.print(f"[green]✓[/green] [bold]Stage 1 Completed:[/bold] Extracted {len(terms)} distinct terms.")
    console.print(f"   Terms: [cyan]{', '.join(f'\"{t}\"' for t in terms)}[/cyan]\n")

    # --- STAGE 2: Parallel Search Client ---
    with console.status("[bold blue]Stage 2: Executing parallel search queries via httpx (async TaskGroup)...[/bold blue]"):
        candidates = await search_articles(terms)
    
    console.print(f"[green]✓[/green] [bold]Stage 2 Completed:[/bold] Fetched and deduplicated [cyan]{len(candidates)}[/cyan] candidate articles.\n")
    if not candidates:
        console.print("[red]Error: No articles matching the extracted terms were found. Exiting.[/red]")
        return

    # --- STAGE 3: Semantic Filtering (BGE + FAISS) ---
    with console.status("[bold blue]Stage 3: Embedding summaries & indexing in FAISS flat IP vector database...[/bold blue]"):
        filtered_articles, dense_scores = semantic_filter(pir_query, candidates, top_k=50)
    
    console.print(f"[green]✓[/green] [bold]Stage 3 Completed:[/bold] Filtered candidates down to [cyan]{len(filtered_articles)}[/cyan] articles using cosine similarity.\n")

    # --- STAGE 4: Hybrid Reranking (BM25 + RRF) ---
    with console.status("[bold blue]Stage 4: Tokenizing & running BM25Okapi + Reciprocal Rank Fusion (k=60)...[/bold blue]"):
        top_articles = hybrid_rerank(terms, filtered_articles, dense_scores, k=60, top_n=10)
    
    console.print(f"[green]✓[/green] [bold]Stage 4 Completed:[/bold] Selected top [cyan]{len(top_articles)}[/cyan] articles using hybrid fusion.\n")

    # --- STAGE 5: LLM Report Generation (Claude / Mock) ---
    with console.status("[bold blue]Stage 5: Constructing prompt & generating intelligence assessment...[/bold blue]"):
        raw_report = generate_report(pir_query, top_articles)
        formatted_report = format_report(raw_report, top_articles)

    # Display the final generated report
    console.print("\n" + "═" * 80)
    console.print(Markdown(formatted_report))
    console.print("═" * 80 + "\n")

    # --- STRETCH GOAL: Ingest into RAG store ---
    with console.status("[bold blue]Stage 6 (Stretch): Ingesting article full texts into local ChromaDB RAG store...[/bold blue]"):
        ingest_articles(top_articles)
    
    # --- STRETCH GOAL: Interactive Q&A loop ---
    console.print("\n[bold yellow]═══ Interactive Follow-up Q&A Session ═══[/bold yellow]")
    console.print("Ask follow-up questions grounded in the weekly article database.")
    console.print("Type [bold red]'exit'[/bold red] or [bold red]'quit'[/bold red] to terminate the session.\n")
    
    while True:
        try:
            question = console.input("[bold yellow]QA Question > [/bold yellow]").strip()
            if not question:
                continue
            if question.lower() in ["exit", "quit"]:
                console.print("[green]Exiting interactive QA session. Goodbye![/green]")
                break
            
            with console.status("[bold blue]Searching ChromaDB chunks and compiling answer...[/bold blue]"):
                answer = query_rag(question, raw_report)
                
            console.print()
            console.print(Panel(Markdown(answer), title=f"[cyan]Answer: {question}[/cyan]", border_style="yellow"))
            console.print()
        except KeyboardInterrupt:
            console.print("\n[green]Exiting interactive QA session. Goodbye![/green]")
            break
        except Exception as e:
            console.print(f"[red]Error in QA loop: {e}[/red]")

async def main_async():
    parser = argparse.ArgumentParser(description="PIR Intelligence Pipeline")
    parser.add_argument(
        "query", 
        nargs="?", 
        type=str, 
        help="Priority Intelligence Requirement (PIR) query string"
    )
    args = parser.parse_args()

    if args.query:
        query = args.query.strip()
    else:
        # Prompt if run without arguments
        console.print("[bold yellow]No query passed as command-line argument.[/bold yellow]")
        query = console.input("[bold green]Enter Priority Intelligence Requirement (PIR) query: [/bold green]").strip()
        if not query:
            console.print("[red]Query cannot be empty. Exiting.[/red]")
            sys.exit(1)

    await run_pipeline(query)

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        console.print("\n[red]Pipeline execution interrupted by user.[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
