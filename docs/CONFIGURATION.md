# ⚙️ Configuration Guide

Complete configuration reference for Crawl4AI MCP Server.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Service Configuration](#service-configuration)
- [RAG Configuration](#rag-configuration)
- [Database Configuration](#database-configuration)
- [Search Configuration](#search-configuration)
- [Performance Tuning](#performance-tuning)
- [Security Settings](#security-settings)
- [Advanced Configuration](#advanced-configuration)

## Environment Variables

### API Keys

```env
# OpenAI (Required for embeddings)
OPENAI_API_KEY=sk-...

# Anthropic (Optional, for Claude models)
ANTHROPIC_API_KEY=sk-ant-...

# Groq (Optional, for Groq models)
GROQ_API_KEY=gsk_...

# Cohere (Optional, for reranking)
COHERE_API_KEY=...

# Google (Optional, for Gemini models)
GOOGLE_API_KEY=...
```

### Server Configuration

```env
# MCP Server Settings
HOST=0.0.0.0
PORT=8051
TRANSPORT=http

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json  # json or text
LOG_FILE=/app/logs/mcp.log

# Request Limits
MAX_REQUEST_SIZE=32MB
REQUEST_TIMEOUT=300  # seconds
RATE_LIMIT=100  # requests per minute
```

## Service Configuration

### Docker Compose Profiles

```yaml
# Minimal setup (production)
profiles: ["core"]
# Includes: MCP Server, Qdrant, Valkey, SearXNG

# Full features
profiles: ["full"]
# Includes: core + Neo4j

# Development
profiles: ["dev"]
# Includes: full + Mailhog, Jupyter
```

Usage:
```bash
# Start specific profile
docker compose --profile core up -d
docker compose --profile full up -d
docker compose --profile dev up -d
```

### Service Ports

Default port mappings:

| Service | Internal | External | Environment Variable |
|---------|----------|----------|---------------------|
| MCP Server | 8051 | 8051 | `PORT` |
| Qdrant | 6333 | 6333 | `QDRANT_PORT` |
| Qdrant gRPC | 6334 | 6334 | `QDRANT_GRPC_PORT` |
| Valkey | 6379 | 6379 | `VALKEY_PORT` |
| SearXNG | 8080 | 8080 | `SEARXNG_PORT` |
| Neo4j HTTP | 7474 | 7474 | `NEO4J_HTTP_PORT` |
| Neo4j Bolt | 7687 | 7687 | `NEO4J_BOLT_PORT` |

## RAG Configuration

### Embedding Settings

```env
# Embedding Model
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
EMBEDDING_BATCH_SIZE=100

# Chunking Strategy
CHUNK_SIZE=2000
CHUNK_OVERLAP=200
MIN_CHUNK_SIZE=100
MAX_CHUNK_SIZE=5000
```

### RAG Strategy

```env
# RAG Features
USE_RERANKING=true
ENHANCED_CONTEXT=true
ENABLE_AGENTIC_RAG=true
ENABLE_HYBRID_SEARCH=false

# Reranking
RERANKER_MODEL=cohere
RERANK_TOP_K=5
MIN_RELEVANCE_SCORE=0.7

# Context Window
MAX_CONTEXT_LENGTH=8000
CONTEXT_WINDOW_SIZE=4000
```

### Search Settings

```env
# Vector Search
VECTOR_SEARCH_TOP_K=10
SIMILARITY_THRESHOLD=0.75
USE_MMR=true  # Maximal Marginal Relevance
MMR_LAMBDA=0.5

# Hybrid Search (if enabled)
HYBRID_ALPHA=0.7  # 0=keyword only, 1=vector only
BM25_K1=1.2
BM25_B=0.75
```

## Database Configuration

### Qdrant Settings

```env
# Connection
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=  # Optional, for production
QDRANT_GRPC_PORT=6334

# Collection Settings
QDRANT_COLLECTION=crawled_pages
QDRANT_COLLECTION_CODE=code_examples
QDRANT_DISTANCE_METRIC=Cosine  # Cosine, Euclid, Dot

# Performance
QDRANT_BATCH_SIZE=100
QDRANT_TIMEOUT=30
QDRANT_MAX_RETRIES=3
```

### Supabase Settings (Alternative)

```env
# Use Supabase instead of Qdrant
VECTOR_DATABASE=supabase

# Supabase Connection
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_TABLE=documents
SUPABASE_EMBEDDING_COLUMN=embedding

# pgvector Settings
PGVECTOR_DISTANCE_METRIC=cosine  # cosine, l2, inner
PGVECTOR_INDEX_TYPE=ivfflat  # ivfflat, hnsw
```

### Neo4j Settings

```env
# Connection
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Database
NEO4J_DATABASE=neo4j
NEO4J_MAX_CONNECTION_LIFETIME=3600
NEO4J_MAX_CONNECTION_POOL_SIZE=50

# Memory Settings
NEO4J_server_memory_heap_initial__size=512M
NEO4J_server_memory_heap_max__size=1G
NEO4J_server_memory_pagecache_size=512M
```

### Cache Settings (Valkey/Redis)

```env
# Connection
VALKEY_URL=redis://valkey:6379
VALKEY_PASSWORD=  # Optional

# Cache Settings
CACHE_TTL=3600  # seconds
CACHE_MAX_SIZE=256MB
CACHE_EVICTION_POLICY=allkeys-lru

# Persistence
VALKEY_SAVE_INTERVALS="60 1 300 10 900 100"
```

## Search Configuration

### SearXNG Settings

```env
# Base Configuration
SEARXNG_URL=http://searxng:8080
SEARXNG_BASE_URL=http://localhost:8080/
SEARXNG_SECRET_KEY=ultrasecretkey

# Search Settings
SEARXNG_DEFAULT_ENGINES=google,bing,duckduckgo
SEARXNG_LANGUAGE=en
SEARXNG_REGION=us
SEARXNG_SAFE_SEARCH=0  # 0=off, 1=moderate, 2=strict
SEARXNG_TIME_RANGE=  # day, week, month, year
```

### Search Behavior

```env
# Result Limits
SEARCH_MAX_RESULTS=10
SEARCH_TIMEOUT=10
SEARCH_RETRY_COUNT=3

# Crawling Behavior
CRAWL_MAX_DEPTH=3
CRAWL_MAX_PAGES=100
CRAWL_TIMEOUT=30
CRAWL_USER_AGENT="Mozilla/5.0 (compatible; Crawl4AI)"
```

## Performance Tuning

### Resource Limits

Docker Compose resource configuration:

```yaml
services:
  mcp-crawl4ai:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G

  qdrant:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Concurrency Settings

```env
# Crawling Concurrency
MAX_CONCURRENT_CRAWLS=10
MAX_CONCURRENT_BROWSERS=5
BROWSER_POOL_SIZE=3

# Processing Concurrency
MAX_WORKERS=4
THREAD_POOL_SIZE=10
ASYNC_BATCH_SIZE=20
```

### Optimization Flags

```env
# Performance Optimizations
ENABLE_CACHING=true
ENABLE_COMPRESSION=true
USE_CONNECTION_POOLING=true
LAZY_LOADING=true

# Debug/Development
DEBUG_MODE=false
PROFILE_REQUESTS=false
ENABLE_METRICS=true
```

## Security Settings

### Authentication

```env
# API Authentication
ENABLE_AUTH=false
API_KEY=  # If auth enabled
JWT_SECRET=  # For JWT tokens
TOKEN_EXPIRY=3600

# OAuth2 (optional)
OAUTH2_PROVIDER=
OAUTH2_CLIENT_ID=
OAUTH2_CLIENT_SECRET=
```

### Network Security

```env
# CORS Settings
CORS_ENABLED=true
CORS_ORIGINS=["http://localhost:3000"]
CORS_METHODS=["GET", "POST"]
CORS_HEADERS=["Content-Type", "Authorization"]

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60  # seconds

# IP Filtering
IP_WHITELIST=  # Comma-separated IPs
IP_BLACKLIST=
```

### SSL/TLS Configuration

```env
# HTTPS Settings
ENABLE_HTTPS=false
SSL_CERT_FILE=/certs/cert.pem
SSL_KEY_FILE=/certs/key.pem
SSL_VERIFY_MODE=CERT_REQUIRED
```

## Advanced Configuration

### Crawler Settings

```env
# Browser Configuration
BROWSER_HEADLESS=true
BROWSER_SANDBOX=true
BROWSER_DEVTOOLS=false
BROWSER_VIEWPORT_WIDTH=1920
BROWSER_VIEWPORT_HEIGHT=1080

# JavaScript Execution
ENABLE_JAVASCRIPT=true
JS_EXECUTION_TIMEOUT=10000
WAIT_FOR_SELECTOR=
WAIT_FOR_NAVIGATION=load  # load, domcontentloaded, networkidle

# Content Extraction
EXTRACT_IMAGES=false
EXTRACT_LINKS=true
EXTRACT_METADATA=true
CLEAN_HTML=true
REMOVE_SCRIPTS=true
REMOVE_STYLES=true
```

### Hallucination Detection

```env
# Neo4j Knowledge Graph
ENABLE_HALLUCINATION_DETECTION=true
KNOWLEDGE_GRAPH_UPDATE_INTERVAL=3600
MIN_CONFIDENCE_SCORE=0.8

# Validation Settings
VALIDATE_IMPORTS=true
VALIDATE_METHODS=true
VALIDATE_PARAMETERS=true
CHECK_DEPRECATED_APIS=true
```

### Monitoring & Observability

```env
# Metrics
ENABLE_PROMETHEUS=false
PROMETHEUS_PORT=9090
METRICS_INTERVAL=60

# Tracing
ENABLE_TRACING=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=crawl4ai-mcp
OTEL_TRACES_SAMPLER=always_on
OTEL_TRACES_SAMPLER_ARG=1.0

# Health Checks
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=5
HEALTH_CHECK_RETRIES=3
```

### Backup & Recovery

```env
# Backup Settings
ENABLE_AUTO_BACKUP=false
BACKUP_INTERVAL=86400  # Daily
BACKUP_RETENTION_DAYS=7
BACKUP_PATH=/backups

# Recovery
AUTO_RECOVERY=true
RECOVERY_MAX_ATTEMPTS=3
RECOVERY_DELAY=60
```

## Configuration Files

### Custom Configuration Locations

```bash
# Override default config
docker run -v ./custom-config.yaml:/app/config.yaml ...

# Multiple config files
CONFIG_PATH=/app/config
CONFIG_FILES=base.yaml,production.yaml,secrets.yaml
```

### Configuration Hierarchy

1. Default values (built-in)
2. Configuration files
3. Environment variables
4. Command-line arguments

### Validating Configuration

```bash
# Check configuration
make config-check

# Test configuration
docker compose config

# Validate environment
docker run --rm krashnicov/crawl4ai-mcp:latest validate-config
```

## Examples

### Production Configuration

```env
# .env.production
OPENAI_API_KEY=sk-prod-...
LOG_LEVEL=WARNING
ENABLE_AUTH=true
API_KEY=secure-api-key-here
RATE_LIMIT_REQUESTS=50
ENABLE_METRICS=true
ENABLE_AUTO_BACKUP=true
```

### Development Configuration

```env
# .env.development
OPENAI_API_KEY=sk-dev-...
LOG_LEVEL=DEBUG
DEBUG_MODE=true
BROWSER_HEADLESS=false
PROFILE_REQUESTS=true
ENABLE_METRICS=true
```

### Minimal Configuration

```env
# .env.minimal
OPENAI_API_KEY=sk-...
# Everything else uses defaults
```

---

For installation instructions, see [INSTALLATION.md](INSTALLATION.md).
For troubleshooting, see the main [README.md](../README.md#troubleshooting).