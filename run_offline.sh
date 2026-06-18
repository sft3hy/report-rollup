#!/usr/bin/env bash
set -euo pipefail

# Default configurations
WHEELS_DIR="./wheels"
MODEL_DIR="./models"
PIR_QUERY=""
START_SERVER=false

# Help message
usage() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  -w, --wheels-dir <path>     Directory containing Python wheels (default: $WHEELS_DIR)"
  echo "  -m, --model-dir <path>      Directory containing local ML models (default: $MODEL_DIR)"
  echo "  -q, --query <string>        Run the CLI pipeline with the specified query"
  echo "  -s, --server                Start the FastAPI API web server instead of CLI"
  echo "  -h, --help                  Show this help message"
  exit 1
}

# Parse command line options
while [[ $# -gt 0 ]]; do
  case "$1" in
    -w|--wheels-dir)
      WHEELS_DIR="$2"
      shift 2
      ;;
    -m|--model-dir)
      MODEL_DIR="$2"
      shift 2
      ;;
    -q|--query)
      PIR_QUERY="$2"
      shift 2
      ;;
    -s|--server)
      START_SERVER=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

echo "=== PIPELINE OFFLINE RUNNER ==="
echo "Wheels Source: $WHEELS_DIR"
echo "Models Source: $MODEL_DIR"
echo "==============================="

# 1. Check directories
if [ ! -d "$WHEELS_DIR" ]; then
  echo "Error: Wheels directory '$WHEELS_DIR' not found."
  echo "Please run './package_offline.sh' first on an internet-connected system."
  exit 1
fi

if [ ! -d "$MODEL_DIR" ]; then
  echo "Error: Models directory '$MODEL_DIR' not found."
  echo "Please run './package_offline.sh' first on an internet-connected system."
  exit 1
fi

# 2. Re-create or sync virtual environment offline
echo "Setting up offline Python environment..."
# Initialize virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating new virtual environment (.venv)..."
  uv venv --python 3.13
fi

# Install dependencies offline using find-links
echo "Installing dependencies offline from $WHEELS_DIR..."
uv pip install \
  --no-index \
  --find-links "$WHEELS_DIR" \
  -e .

# 3. Configure offline environment variables
export HF_HUB_OFFLINE=1
export NOMIC_MODEL_PATH="$MODEL_DIR/nomic-embed-text-v1.5"
export SPACY_MODEL_PATH="en_core_web_sm"

# Unset Anthropic key to force local mock reporter if not set in current env
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "No ANTHROPIC_API_KEY detected. Running with offline Mock LLM compiler."
  export ANTHROPIC_API_KEY=""
fi

# Unset Search API keys to force local mock article search engine
export TAVILY_API_KEY=""
export NEWSAPI_API_KEY=""

# 4. Run application
if [ "$START_SERVER" = true ]; then
  echo "Starting offline FastAPI server..."
  uv run python -m pir_search.api_server
elif [ -n "$PIR_QUERY" ]; then
  echo "Executing offline CLI pipeline for query: '$PIR_QUERY'"
  uv run python -m pir_search "$PIR_QUERY"
else
  # Prompt for query if running CLI without args
  echo "Executing offline CLI pipeline..."
  uv run python -m pir_search
fi
