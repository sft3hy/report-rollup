# Airgap Deployment Manifest

This document outlines the dependencies, model binaries, and configurations that must be downloaded in advance and transported via secure media (e.g., optical disc, USB) to run the **PIR Intelligence Pipeline** on an airgapped network.

---

## 📦 1. Python Wheel Packages

The destination system will not have access to PyPI. You must download all packages in wheels format beforehand.

### How to package dependencies:
On an internet-connected system with the same OS and target Python version as the airgap system:
```bash
# Create a folder for wheels
mkdir wheels

# Download all packages specified in the pyproject.toml to the folder
uv pip download -r pyproject.toml --dest ./wheels
```

### Installation on the airgap system:
```bash
# In the airgapped system, install from the local wheels folder
uv pip install --no-index --find-links ./wheels -e .
```

---

## 🤖 2. Machine Learning Model Files

The pipeline downloads two models at runtime from the Hugging Face Hub. In an airgap, Hugging Face Hub requests will fail. You must preload these models.

### A. SentenceTransformer Embeddings Model
*   **Model Name:** `nomic-ai/nomic-embed-text-v1.5` (which also relies on `nomic-ai/nomic-bert-2048`)
*   **Default Cache Directory:** `~/.cache/huggingface/hub/`
*   **How to transport:**
    1.  Verify the models exist in the Hugging Face cache folder after running the pipeline once:
        ```bash
        ls -la ~/.cache/huggingface/hub/
        # You should see models--nomic-ai--nomic-embed-text-v1.5 and models--nomic-ai--nomic-bert-2048
        ```
    2.  Compress and copy both folders:
        ```bash
        tar -czf nomic_models.tar.gz -C ~/.cache/huggingface/hub/ models--nomic-ai--nomic-embed-text-v1.5 models--nomic-ai--nomic-bert-2048
        ```
    3.  Extract them on the airgap system to the exact same path:
        ```bash
        mkdir -p ~/.cache/huggingface/hub/
        tar -xzf nomic_models.tar.gz -C ~/.cache/huggingface/hub/
        ```

### B. spaCy Language Model
*   **Model Name:** `en_core_web_sm`
*   **How to download manually:**
    1.  Download the wheel directly from spaCy's repository:
        [en_core_web_sm-3.8.0.whl](https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl)
    2.  Transport the `.whl` file to the airgap system.
    3.  Install it using `pip` within your virtual environment:
        ```bash
        .venv/bin/pip install en_core_web_sm-3.8.0-py3-none-any.whl
        ```

---

## 🔌 3. External API and Network Configurations

The current pipeline relies on external internet APIs for live search data and Anthropic's Claude API.

### A. Web Search (Tavily / NewsAPI)
*   **Airgap Availability:** **NOT AVAILABLE**
*   **Action Required:** Leave `TAVILY_API_KEY` and `NEWSAPI_API_KEY` unset or empty in the `.env` file. The pipeline will automatically fall back to using the local mock database `pir_search/resources/mock_articles.json`.
*   **Optional:** To ingest real data inside the airgap, you can manually write structured intelligence reports directly into the `pir_search/resources/mock_articles.json` file. The mock search engine will query and rank those records locally.

### B. Bedrock Claude model (`bedrock-claude-sonnet-4.5-gov`)
*   **Airgap Availability:** **RESTRICTED**
*   **Action Required:**
    1.  The Anthropic SDK (`Anthropic(api_key=...)`) queries `api.anthropic.com` by default. On a government airgapped system (e.g., AWS Secret/Top Secret regions), AWS Bedrock endpoints must be accessed via AWS PrivateLink / VPC Endpoints.
    2.  The code in `reporter.py` and `rag.py` would need to be updated to initialize via `boto3` (AWS SDK for Python) using Bedrock runtime clients, rather than the `anthropic` Python client.
    3.  If no Bedrock endpoint exists, the pipeline will fallback to the offline **Mock LLM compiler** which synthesizes reports locally.
