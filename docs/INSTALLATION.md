# 📦 Installation Guide

Comprehensive installation instructions for Crawl4AI MCP Server.

## Table of Contents

- [Requirements](#requirements)
- [Installation Methods](#installation-methods)
  - [One-Click Install](#one-click-install)
  - [Docker Install](#docker-install)
  - [Manual Install](#manual-install)
  - [Development Install](#development-install)
- [Configuration](#configuration)
- [Verification](#verification)
- [Upgrading](#upgrading)
- [Uninstallation](#uninstallation)

## Requirements

### System Requirements

- **OS**: Linux, macOS, Windows (with WSL2)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB free space
- **CPU**: 2+ cores recommended

### Software Requirements

- **Docker**: 20.10+ ([Installation guide](https://docs.docker.com/get-docker/))
- **Docker Compose**: 2.0+ (usually included with Docker Desktop)
- **Git**: (optional, for cloning repository)

### Network Requirements

- Ports available: 8051, 6333, 6379, 8080
- Internet connection for pulling images

## Installation Methods

### One-Click Install

The fastest way to get started:

```bash
curl -sSL https://raw.githubusercontent.com/krashnicov/crawl4ai-mcp/main/scripts/install.sh | bash
```

This script will:
- Check dependencies
- Clone the repository
- Set up directories
- Configure environment
- Pull Docker images
- Start services

### Docker Install

Using Docker directly:

```bash
# Pull the image
docker pull krashnicov/crawl4ai-mcp:latest

# Run with minimal setup
docker run -d \
  --name crawl4ai-mcp \
  -p 8051:8051 \
  -v $(pwd)/data:/app/data \
  -e OPENAI_API_KEY=your_key_here \
  krashnicov/crawl4ai-mcp:latest
```

### Manual Install

Step-by-step manual installation:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/krashnicov/crawl4ai-mcp.git
   cd crawl4ai-mcp
   ```

2. **Create directories:**
   ```bash
   mkdir -p data/{qdrant,neo4j,valkey}
   mkdir -p logs
   mkdir -p analysis_scripts/{user_scripts,validation_results}
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   nano .env
   ```

4. **Start services:**
   ```bash
   docker compose --profile core up -d
   ```

### Development Install

For contributors and developers:

1. **Clone with submodules:**
   ```bash
   git clone --recursive https://github.com/krashnicov/crawl4ai-mcp.git
   cd crawl4ai-mcp
   ```

2. **Install Python dependencies:**
   ```bash
   # Install UV package manager
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install dependencies
   uv sync
   ```

3. **Start development environment:**
   ```bash
   make dev  # Or: docker compose --profile dev up --watch
   ```

## Configuration

### Environment Variables

Create and edit `.env` file:

```env
# Required
OPENAI_API_KEY=sk-...

# Optional API Keys
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
COHERE_API_KEY=...

# Service Configuration
PORT=8051
TRANSPORT=http

# Database Selection
VECTOR_DATABASE=qdrant  # or supabase

# Qdrant Configuration
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=  # Optional, for production

# Neo4j Configuration (for advanced features)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# RAG Configuration
USE_RERANKING=true
ENHANCED_CONTEXT=true
ENABLE_AGENTIC_RAG=true
ENABLE_HYBRID_SEARCH=false

# Search Configuration
SEARXNG_URL=http://searxng:8080
```

### Docker Compose Profiles

Choose the appropriate profile:

```bash
# Minimal setup (MCP, Qdrant, Valkey, SearXNG)
docker compose --profile core up -d

# Full features (core + Neo4j)
docker compose --profile full up -d

# Development (full + Mailhog, Jupyter)
docker compose --profile dev up -d
```

### Resource Limits

Adjust in `docker-compose.yml` if needed:

```yaml
services:
  mcp-crawl4ai:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Verification

### Check Installation

1. **Verify services are running:**
   ```bash
   make status
   # Or: docker compose ps
   ```

2. **Check health endpoints:**
   ```bash
   curl http://localhost:8051/health
   curl http://localhost:6333/readyz
   ```

3. **View logs:**
   ```bash
   make logs
   # Or: docker compose logs -f
   ```

### Test Functionality

```python
# Test search
curl -X POST http://localhost:8051/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test search"}'

# Test crawling
curl -X POST http://localhost:8051/scrape_urls \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Upgrading

### Using Make

```bash
cd ~/crawl4ai-mcp
git pull
make restart
```

### Using Docker

```bash
# Pull latest image
docker pull krashnicov/crawl4ai-mcp:latest

# Restart services
docker compose down
docker compose --profile core up -d
```

### Database Migration

When upgrading major versions:

```bash
# Backup data
docker compose exec qdrant qdrant-backup create /backup

# Upgrade
git pull
docker compose pull
docker compose up -d

# Verify data
make health
```

## Uninstallation

### Complete Removal

```bash
# Stop and remove containers
cd ~/crawl4ai-mcp
make clean-all

# Remove directory
cd ~
rm -rf crawl4ai-mcp

# Remove shell aliases
# Edit ~/.bashrc or ~/.zshrc and remove crawl4ai lines
```

### Preserve Data

```bash
# Stop services but keep data
make stop

# Backup data before removal
tar czf crawl4ai-backup.tar.gz data/
```

## Troubleshooting

### Common Issues

**Port conflicts:**
```bash
# Find process using port
lsof -i :8051
# Kill process or change port in .env
```

**Permission denied:**
```bash
# Fix ownership
sudo chown -R $USER:$USER .
```

**Out of memory:**
```bash
# Increase Docker memory
# Docker Desktop → Settings → Resources → Memory
```

**Slow performance:**
```bash
# Check resource usage
docker stats

# Restart services
make restart
```

### Getting Help

- Check logs: `make logs`
- Documentation: [README](../README.md)
- Issues: [GitHub Issues](https://github.com/krashnicov/crawl4ai-mcp/issues)
- Discord: [Join Community](https://discord.gg/crawl4ai)

---

For configuration options, see [CONFIGURATION.md](CONFIGURATION.md).