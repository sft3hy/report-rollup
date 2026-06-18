import os
import httpx
from rich.console import Console

console = Console()

def call_llm(system_prompt: str, user_prompt: str, model: str = "bedrock-claude-sonnet-4.5-gov", max_tokens: int = 2500, temperature: float = 0.2) -> str:
    """
    Unified entrypoint to call the LLM. 
    Queries the NRO Sanctuary API gateway (https://sanctuary.clairvoyant.proj.nro.ic.gov/api/v1)
    if SANCTUARY_KEY is set. Falls back to direct Anthropic API if ANTHROPIC_API_KEY is set.
    """
    sanctuary_key = os.getenv("SANCTUARY_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not sanctuary_key or not sanctuary_key.strip():
        if anthropic_key and anthropic_key.strip():
            console.print("[blue]SANCTUARY_KEY not set. Falling back to direct Anthropic API client...[/blue]")
            from anthropic import Anthropic
            client = Anthropic(api_key=anthropic_key)
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return message.content[0].text
        raise ValueError("Neither SANCTUARY_KEY nor ANTHROPIC_API_KEY is set in the environment.")

    # 1. Attempt OpenAI-style chat completions on NRO Sanctuary Gateway
    url = "https://sanctuary.clairvoyant.proj.nro.ic.gov/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {sanctuary_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    # Locate NRO ca-bundle.crt if available
    cert_dir = "/etc/certs"
    if not os.path.exists(cert_dir):
        cert_dir = os.path.expanduser("~/dev/certs")
    
    ca_bundle = os.path.join(cert_dir, "ca-bundle.crt")
    ssl_verify = ca_bundle if os.path.exists(ca_bundle) else False

    console.print(f"[blue]Dispatching request to Sanctuary NRO API Gateway ({url})...[/blue]")
    if ssl_verify:
        console.print(f"[green]SSL validation enabled using: {ssl_verify}[/green]")
    else:
        console.print("[yellow]SSL validation disabled (ca-bundle.crt not found)[/yellow]")
    
    with httpx.Client(verify=ssl_verify) as client:
        try:
            response = client.post(url, headers=headers, json=payload, timeout=60.0)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            
            # 2. If 404 or Method Not Allowed, NRO Sanctuary might expose Anthropic compatibility endpoint
            if response.status_code in (404, 405):
                console.print("[yellow]OpenAI endpoint returned 404/405. Attempting Anthropic Messages API compatible gateway...[/yellow]")
                anthropic_url = "https://sanctuary.clairvoyant.proj.nro.ic.gov/api/v1/messages"
                anthropic_headers = {
                    "x-api-key": sanctuary_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                }
                anthropic_payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": user_prompt}],
                    "system": system_prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                alt_resp = client.post(anthropic_url, headers=anthropic_headers, json=anthropic_payload, timeout=60.0)
                if alt_resp.status_code == 200:
                    alt_data = alt_resp.json()
                    return alt_data["content"][0]["text"]
                raise RuntimeError(f"Sanctuary Anthropic endpoint failed (status {alt_resp.status_code}): {alt_resp.text}")
            
            raise RuntimeError(f"Sanctuary OpenAI endpoint failed (status {response.status_code}): {response.text}")
            
        except Exception as e:
            # 3. Third fallback: try using Anthropic python SDK with custom base_url
            console.print(f"[yellow]HTTPX gateway request failed: {e}. Trying Anthropic SDK base_url override...[/yellow]")
            try:
                from anthropic import Anthropic
                sdk_client = Anthropic(api_key=sanctuary_key, base_url="https://sanctuary.clairvoyant.proj.nro.ic.gov/api/v1")
                message = sdk_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                return message.content[0].text
            except Exception as sdk_err:
                raise RuntimeError(f"Sanctuary gateway connection failed. Gateway Error: {e}. SDK Error: {sdk_err}")
