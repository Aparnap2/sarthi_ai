# Sarthi Python AI Worker
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv
RUN UV_LINK_MODE=copy uv pip install --system \
    temporalio \
    langgraph \
    langchain \
    langchain-core \
    openai \
    qdrant-client \
    pydantic \
    httpx \
    structlog \
    pyyaml \
    psycopg2-binary \
    dspy-ai \
    langfuse

# Copy source
COPY src/ src/

# Default command
CMD ["python", "-m", "src.worker"]
