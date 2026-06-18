# Stage 1: Build virtual environment
FROM python:3.13-slim as builder

# Declare custom registry build-args
ARG UV_INDEX_URL
ARG UV_EXTRA_INDEX_URL
ARG UV_DEFAULT_INDEX
ARG UV_INDEX
ENV UV_INDEX_URL=$UV_INDEX_URL
ENV UV_EXTRA_INDEX_URL=$UV_EXTRA_INDEX_URL
ENV UV_DEFAULT_INDEX=$UV_DEFAULT_INDEX
ENV UV_INDEX=$UV_INDEX

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy package configurations
COPY pyproject.toml README.md ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# Copy package codebase
COPY pir_search/ ./pir_search/

# Build and install the project
RUN uv sync --frozen --no-dev

# Stage 2: Runtime image
FROM python:3.13-slim

WORKDIR /app

# Install libgomp1 (required for FAISS CPU execution)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and code from builder stage
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pir_search /app/pir_search

# Place virtual environment binaries in path
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Pre-download and cache the Nomic AI embedding model inside the image layers
# so the container has 100% of the model files built-in for airgapped deployments.
ARG NOMIC_MODEL_PATH=nomic-ai/nomic-embed-text-v1.5
ENV NOMIC_MODEL_PATH=$NOMIC_MODEL_PATH
RUN python -c 'import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.getenv("NOMIC_MODEL_PATH"), trust_remote_code=True)'

# Expose Port 8000 for FastAPI API server
EXPOSE 8000

# Start the FastAPI web server
CMD ["python", "-m", "pir_search.api_server"]
