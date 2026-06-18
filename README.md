# PIR Intelligence Pipeline & Tactical Ops Dashboard

A structured NLP and semantic search pipeline for analyzing Priority Intelligence Requirements (PIRs), integrated with a React-based futuristic web interface and designed for fully offline (airgapped) deployment.

## 🚀 Features
- **Futuristic Ops Web UI**: A cybernetic React dashboard featuring real-time scrolling pipeline logs, interactive RAG follow-up terminal, and responsive dual-pane display.
- **NLP Extractor**: spaCy Named Entity Recognition (NER) and KeyBERT keyword extraction.
- **Parallel Search Client**: Multi-query asyncio TaskGroup engine executing search client requests via `httpx`.
- **Semantic Vector Filtering**: High-performance local sentence embedding mapping using BGE/Nomic models indexed in a FAISS Flat IP vector database.
- **Hybrid Reranking**: Reciprocal Rank Fusion (RRF) combining dense semantic search scores and BM25Okapi token matching.
- **Intelligence Reporter**: Custom prompt builder utilizing Claude (`bedrock-claude-sonnet-4.5-gov`) with inline bibliography citation indexing.
- **RAG Knowledge Store**: Persistent ChromaDB vector collection storing chunked full texts for interactive follow-up Q&A grounded in source data.
- **Airgap Capabilities**: Single-command packaging for Python wheels and ML weights to run without any internet access.

---

## 🛠️ Installation & Setup

Ensure you have Python 3.13 and Node.js installed on your development machine.

### 1. Initialize Python Environment
```bash
# Sync python virtual environment and download packages
uv sync --python 3.13

# Download the spaCy model
.venv/bin/python -m spacy download en_core_web_sm
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
ANTHROPIC_API_KEY=your-api-key-here
```
*If `ANTHROPIC_API_KEY` is not provided, the pipeline will fall back to using the local mock compiler.*

---

## 🖥️ Running the Application

### Option A: Futuristic Web Dashboard (Recommended)

To run the full stack (API Backend + React Frontend):

1. **Build the Frontend Assets**:
   ```bash
   npm run build --prefix frontend
   ```
2. **Start the FastAPI Server**:
   ```bash
   uv run python -m pir_search.api_server
   ```
3. Open **`http://localhost:8000/`** in your browser.

*For frontend development with hot-reloading:*
Run `npm run dev --prefix frontend` (port `5173`) alongside the FastAPI server.

### Option B: Command Line Interface (CLI)
Run the pipeline directly from your shell:
```bash
uv run python -m pir_search "Your PIR query here"
```

---

## 📦 Offline & Airgapped Deployments

This repository contains dedicated automation scripts to bundle all dependencies and run entirely offline.

1. **Package Everything (Online Machine)**:
   ```bash
   ./package_offline.sh
   ```
   *This downloads all Python wheels (to `./wheels`) and Hugging Face model checkpoints (to `./models`).*

2. **Run Everything Offline (Airgapped Machine)**:
   ```bash
   ./run_offline.sh -q "Your PIR query here"
   # Or start the server:
   ./run_offline.sh --server
   ```

For detailed options, custom PyPI mirror configuration, and container yard deployment instructions, see the **[Offline Deployment Guide](file:///Users/samueltownsend/dev/cosmic/report-rollup/offline_setup.md)**.

