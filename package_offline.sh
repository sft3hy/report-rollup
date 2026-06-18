#!/usr/bin/env bash
set -euo pipefail

# Default configurations
WHEELS_DIR="./wheels"
MODEL_DIR="./models"
PYPI_INDEX_URL=""

# Help message
usage() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  -w, --wheels-dir <path>     Directory to download Python wheels to (default: $WHEELS_DIR)"
  echo "  -m, --model-dir <path>      Directory to download ML models to (default: $MODEL_DIR)"
  echo "  -i, --index-url <url>       Custom PyPI mirror registry URL"
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
    -i|--index-url)
      PYPI_INDEX_URL="$2"
      shift 2
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

echo "=== PIPELINE OFFLINE PACKAGER ==="
echo "Wheels Destination: $WHEELS_DIR"
echo "Models Destination: $MODEL_DIR"
if [ -n "$PYPI_INDEX_URL" ]; then
  echo "PyPI Index Mirror:  $PYPI_INDEX_URL"
else
  echo "PyPI Index Mirror:  Default (PyPI)"
fi
echo "================================="

# Create directories
mkdir -p "$WHEELS_DIR"
mkdir -p "$MODEL_DIR"

# Generate requirements.txt if not present
if [ ! -f "requirements.txt" ]; then
  echo "Compiling requirements.txt from pyproject.toml..."
  uv pip compile pyproject.toml -o requirements.txt
fi

# Download wheels
echo "Downloading Python wheels..."
INDEX_ARG=""
if [ -n "$PYPI_INDEX_URL" ]; then
  INDEX_ARG="--index-url $PYPI_INDEX_URL"
fi

# Run pip download
.venv/bin/python -m pip download -r requirements.txt \
  --dest "$WHEELS_DIR" \
  $INDEX_ARG \
  --no-cache-dir

# Download build backend for offline installation of editable project
.venv/bin/python -m pip download hatchling editables \
  --dest "$WHEELS_DIR" \
  $INDEX_ARG \
  --no-cache-dir

# Download Hugging Face Models
echo "Downloading Hugging Face models..."
export MODEL_DIR
.venv/bin/python -c "
import os
from huggingface_hub import snapshot_download

model_dir = os.environ['MODEL_DIR']

print('Downloading nomic-embed-text-v1.5 to:', os.path.join(model_dir, 'nomic-embed-text-v1.5'))
snapshot_download(
    repo_id='nomic-ai/nomic-embed-text-v1.5',
    local_dir=os.path.join(model_dir, 'nomic-embed-text-v1.5'),
    local_dir_use_symlinks=False,
    ignore_patterns=['*.bin', '*.h5', '*.ot', '*.msgpack'] # Download only safetensors / required configs
)

print('Downloading nomic-bert-2048 to:', os.path.join(model_dir, 'nomic-bert-2048'))
snapshot_download(
    repo_id='nomic-ai/nomic-bert-2048',
    local_dir=os.path.join(model_dir, 'nomic-bert-2048'),
    local_dir_use_symlinks=False,
    ignore_patterns=['*.bin', '*.h5', '*.ot', '*.msgpack']
)
"

# Copy spaCy model wheel for standalone access if needed (already downloaded to wheels)
echo "Looking for spaCy model wheel..."
SPACY_WHEEL=$(find "$WHEELS_DIR" -name "en_core_web_sm*.whl" | head -n 1)
if [ -n "$SPACY_WHEEL" ]; then
  echo "Found spaCy model wheel: $SPACY_WHEEL"
  cp "$SPACY_WHEEL" "$MODEL_DIR/"
  echo "Copied spaCy model wheel to $MODEL_DIR"
fi

echo ""
echo "Offline packaging complete!"
echo "You can now transfer the following directories to the airgapped system:"
echo "1. $WHEELS_DIR/ (All pip dependency wheels)"
echo "2. $MODEL_DIR/ (Local ML model files)"
