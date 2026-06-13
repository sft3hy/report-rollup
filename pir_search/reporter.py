import os
from dotenv import load_dotenv
from anthropic import Anthropic
from rich.console import Console

from pir_search.models import Article

# Ensure env is loaded
load_dotenv()

console = Console()

SYSTEM_PROMPT = """You are an intelligence analyst. Given a Priority Intelligence Requirement (PIR)
and a set of reporting articles, produce a structured assessment that:
1. Directly answers the PIR based on the evidence
2. Highlights key entities, locations, and events
3. Notes confidence level and information gaps
4. Cites articles by their ID using [ID] notation (e.g. [ART001])"""

def build_user_prompt(pir: str, articles: list[Article]) -> str:
    """Formats the PIR and the selected articles into a prompt for the model."""
    docs = "\n\n".join(
        f"[{a.article_id}] {a.title}\n{a.full_text}"
        for a in articles
    )
    return f"PIR: {pir}\n\n---\n{docs}"

def generate_mock_report(pir: str, articles: list[Article]) -> str:
    """Generates a high-quality, structured simulated intelligence assessment from the articles."""
    findings = []
    entities = set()
    for art in articles:
        findings.append(f"- From {art.title} [{art.article_id}]: {art.summary}")
        # Extract plausible-looking capitalized words as entities
        for word in art.title.split():
            clean = word.strip(".,()-\"")
            if clean and clean[0].isupper() and len(clean) > 2:
                if clean.lower() not in {"the", "and", "for", "with", "after", "near", "from", "into", "over", "rise", "open", "hits", "boosts"}:
                    entities.add(clean)

    ent_list = ", ".join(sorted(list(entities))[:12])
    findings_str = "\n".join(findings)

    return f"""### 1. Executive Summary
This assessment answers the Priority Intelligence Requirement: "{pir}". 
The analysis is based on {len(articles)} retrieved sources relating to regional security, maritime channels, and critical infrastructure networks.

### 2. Key Findings & Synthesis
A synthesis of current intelligence reports indicates several developments:
{findings_str}

### 3. Key Entities and Locations
- **Critical Entities:** {ent_list if ent_list else "None identified."}

### 4. Confidence Level & Information Gaps
- **Confidence Assessment:** **MEDIUM** (Simulated fallback). The reporting is consistent across the mock database but lacks multi-source real-time intelligence feeds.
- **Information Gaps:** Direct forensics logs, signal intelligence (SIGINT), and immediate command-and-control communications have not been analyzed.

*Note: This report was compiled using the offline Mock LLM Reranker compiler due to a missing Anthropic API Key.*"""

def generate_report(pir: str, articles: list[Article]) -> str:
    """
    Stage 4: LLM report generation.
    Sends the top 10 articles to Anthropic Claude 3.5 Sonnet to generate an intelligence report.
    Falls back to a structured local compiler if ANTHROPIC_API_KEY is not set.
    """
    if not articles:
        return "No relevant reporting articles were found to generate an assessment."

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[yellow]WARNING: ANTHROPIC_API_KEY is not set in the environment. Using Mock LLM reporter.[/yellow]")
        return generate_mock_report(pir, articles)

    try:
        console.print("[blue]Sending assessment request to Anthropic Claude...[/blue]")
        client = Anthropic(api_key=api_key)
        user_prompt = build_user_prompt(pir, articles)
        
        # Using bedrock-claude-sonnet-4.5-gov as specified by the configuration
        message = client.messages.create(
            model="bedrock-claude-sonnet-4.5-gov",
            max_tokens=2500,
            temperature=0.2,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        console.print(f"[red]Error calling Anthropic API: {e}. Falling back to Mock LLM reporter.[/red]")
        return generate_mock_report(pir, articles)

def format_report(report_text: str, articles: list[Article]) -> str:
    """Formats the intelligence assessment with inline sources and a sources bibliography."""
    output = []
    output.append("== INTELLIGENCE ASSESSMENT ==")
    output.append(report_text.strip())
    output.append("")
    output.append("== SOURCES ==")
    for art in articles:
        output.append(f"[{art.article_id}] {art.title} — {art.url}")
    return "\n".join(output)
