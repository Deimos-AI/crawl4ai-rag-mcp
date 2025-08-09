# syntax=docker/dockerfile:1.5
# Enable BuildKit features for better caching and performance

# ============================================
# Build Stage: Compile dependencies
# ============================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python package manager
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip uv

# Copy dependency files first for better caching
COPY pyproject.toml .
COPY README.md .

# Create minimal src structure for installation
RUN mkdir src
COPY src/__init__.py src/
COPY src/main.py src/

# Install dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

# Copy the rest of the source code
COPY src/ ./src/

# Run crawl4ai-setup if available
RUN crawl4ai-setup || echo "crawl4ai-setup not required"

# ============================================
# Security Scanning Stage (optional in dev)
# ============================================
FROM aquasec/trivy:latest AS scanner
COPY --from=builder /build /scan
RUN trivy fs --exit-code 0 --severity HIGH,CRITICAL --no-progress /scan || true

# ============================================
# Production Stage: Minimal runtime
# ============================================
FROM python:3.12-slim AS production

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 -s /bin/bash appuser

# Copy Python packages from builder
COPY --from=builder --chown=appuser:appuser /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder --chown=appuser:appuser /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder --chown=appuser:appuser /build/src ./src

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/analysis_scripts \
    && chown -R appuser:appuser /app

# Add metadata labels
LABEL org.opencontainers.image.source="https://github.com/krashnicov/crawl4ai-mcp"
LABEL org.opencontainers.image.description="Web Crawling, Search and RAG MCP Server"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.version="0.1.0"

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8051

# Switch to non-root user
USER appuser

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import socket; s = socket.socket(); s.settimeout(1); s.connect(('localhost', ${PORT})); s.close()"

# Expose the port
EXPOSE ${PORT}

# Set the entrypoint
ENTRYPOINT ["python", "src/main.py"]