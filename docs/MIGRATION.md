# 📋 Migration Guide: Upgrading Production Environment

## Overview
This guide helps you migrate from the old multi-file Docker Compose setup to the new unified deployment infrastructure.

## Pre-Migration Checklist

### 1. Backup Current Data

The following backup method works reliably whether containers are running or stopped:

```bash
# Working directory: Any location
# Create backup directory and change to it
mkdir -p ~/crawl4ai-backup-$(date +%Y%m%d)
cd ~/crawl4ai-backup-$(date +%Y%m%d)

# Export all data volumes using Docker (works in any state)
docker run --rm -v crawl4aimcp_qdrant-data:/data -v $(pwd):/backup alpine tar czf /backup/qdrant-data.tar.gz -C /data .
docker run --rm -v crawl4aimcp_valkey-data:/data -v $(pwd):/backup alpine tar czf /backup/valkey-data.tar.gz -C /data .

# If using Neo4j, also backup its volume
docker run --rm -v crawl4aimcp_neo4j-data:/data -v $(pwd):/backup alpine tar czf /backup/neo4j-data.tar.gz -C /data .

# Backup environment configuration (adjust path to your installation)
cp ~/crawl4ai-mcp/.env .env.backup  # or ~/crawl4ai-rag-mcp/.env

# Verify backups were created
ls -lh *.tar.gz
```

**Note**: These commands use Alpine Linux containers to create compressed archives of your Docker volumes. This method is 100% reliable and doesn't require containers to be running.

### 2. Document Current Setup

```bash
# From your backup directory (still in ~/crawl4ai-backup-$(date +%Y%m%d))
# Save current running services (if any)
docker compose -f ~/crawl4ai-rag-mcp/docker-compose.prod.yml ps > running-services.txt

# Save current configuration
docker compose -f ~/crawl4ai-rag-mcp/docker-compose.prod.yml config > current-config.yml

# List all volumes for reference
docker volume ls | grep crawl4ai > volumes-list.txt
```

## Migration Steps

### Step 1: Stop Current Services

Now that backups are complete, you can safely stop the old services:

```bash
# Working directory: Your installation directory (e.g., ~/crawl4ai-mcp or ~/crawl4ai-rag-mcp)
cd ~/crawl4ai-rag-mcp  # or wherever your installation is

# Stop the old production setup gracefully
docker compose -f docker-compose.prod.yml down

# IMPORTANT: Do NOT use -v flag to preserve volumes
# Wrong: docker compose -f docker-compose.prod.yml down -v  # This deletes data!
# Right: docker compose -f docker-compose.prod.yml down     # Preserves volumes
```

### Step 2: Pull Latest Changes

```bash
# Working directory: Your installation directory (same as Step 1)
# Fetch the new deployment branch
git fetch origin
git checkout feat/deployment-improvements

# Or if merging to main
git checkout main
git pull origin main
```

### Step 3: Review Configuration Changes

#### Compare Environment Variables

The new setup uses the same environment variables, but check for any new ones:

```bash
# Working directory: Your installation directory
# Compare your current .env with the new example
diff .env .env.example

# Key variables to verify:
# - OPENAI_API_KEY (required)
# - ANTHROPIC_API_KEY (optional)
# - QDRANT_API_KEY (if using in production)
# - NEO4J_PASSWORD (if using Neo4j)
```

#### Map Old Services to New Profiles

| Old File | Old Service | New Profile | Notes |
|----------|------------|-------------|-------|
| docker-compose.prod.yml | mcp-crawl4ai | `core` | Main service |
| docker-compose.prod.yml | qdrant | `core` | Vector DB |
| docker-compose.prod.yml | valkey | `core` | Cache |
| docker-compose.prod.yml | searxng | `core` | Search |
| docker-compose.prod.yml | neo4j | `full` | Only if using GraphRAG |

### Step 4: Deploy New Infrastructure

```bash
# Working directory: Your installation directory
cd ~/crawl4ai-mcp  # or your installation path

# Ensure your .env file has the correct COMPOSE_PROJECT_NAME if you want specific volume names
# Example: COMPOSE_PROJECT_NAME=crawl4ai-mcp-deimos

# Start the services (this builds the image locally and creates volumes automatically)
make start  # Or: docker compose --profile core up -d
```

**Important Notes**:

- **First run will take longer** as Docker builds the image from the local Dockerfile
- The image is not yet published to Docker Hub, so local building is required
- Docker Compose automatically creates volumes with names based on your COMPOSE_PROJECT_NAME
- You can pre-build the image with: `docker compose build`

### Step 5: Restore Data (If You Have Existing Data)

**⚠️ Decision Point - Do you have existing data to migrate?**

**NO - Starting Fresh**:

- Skip this step - your services are already running with empty volumes
- Proceed to Step 6 for verification

**YES - Migrating Data**:

- Stop the services temporarily to restore your backups
- Your old volumes remain untouched as a secondary backup

The new setup uses different volume names. The exact naming depends on your Docker Compose project name:

**How to identify old vs new volumes:**

- **Old volumes**: Named after the old directory/project (e.g., `crawl4aimcp_*`)
  - Usually just 3 volumes: `*_qdrant-data`, `*_valkey-data`, `*_neo4j-data`
- **New volumes**: Named after the new project name (e.g., `crawl4ai-mcp_*` or `crawl4ai-rag-mcp_*`)
  - May have additional Neo4j volumes: `*_neo4j-conf`, `*_neo4j-logs`, `*_neo4j-plugins`
  - Created when you first run the new docker-compose

```bash
# Working directory: Any location (volume operations work from anywhere)
# List existing volumes to see exact names
docker volume ls | grep -E "qdrant|valkey|neo4j"

# Typical output:
# local     crawl4aimcp_neo4j-data         <- OLD (simple name, just data)
# local     crawl4aimcp_qdrant-data        <- OLD
# local     crawl4aimcp_valkey-data         <- OLD
# local     crawl4ai-rag-mcp_neo4j-conf    <- NEW (multiple neo4j volumes)
# local     crawl4ai-rag-mcp_neo4j-data    <- NEW
# local     crawl4ai-rag-mcp_neo4j-logs    <- NEW
# local     crawl4ai-rag-mcp_neo4j-plugins <- NEW
# local     crawl4ai-rag-mcp_qdrant-data   <- NEW
# local     crawl4ai-rag-mcp_valkey-data   <- NEW

# If you haven't run the new setup yet, you'll only see old volumes
# The new volumes are created when you run docker compose with the new configuration

# Tip: Check volume creation dates to identify old vs new
docker volume inspect crawl4aimcp_qdrant-data | grep Created
docker volume inspect crawl4ai-rag-mcp_qdrant-data | grep Created

# Example: Restoring data after Docker Compose created the volumes
# This example assumes:
# - You ran docker-compose which created volumes named crawl4ai_mcp_deimos_*
# - You have backups from Step 1 in ~/crawl4ai-backup-$(date +%Y%m%d)
# - Old volumes: crawl4aimcp_* (kept as secondary backup)

# Step 1: Stop the services to restore data
cd ~/crawl4ai-mcp  # Your installation directory
make stop  # Or: docker compose down

# Step 2: Restore from backup
cd ~/crawl4ai-backup-$(date +%Y%m%d)

# Restore the backups into the volumes that Docker Compose created
docker run --rm -v crawl4ai_mcp_deimos_valkey-data:/data -v $(pwd):/backup alpine tar xzf /backup/valkey-data.tar.gz -C /data
docker run --rm -v crawl4ai_mcp_deimos_qdrant-data:/data -v $(pwd):/backup alpine tar xzf /backup/qdrant-data.tar.gz -C /data
docker run --rm -v crawl4ai_mcp_deimos_neo4j-data:/data -v $(pwd):/backup alpine tar xzf /backup/neo4j-data.tar.gz -C /data

# Step 3: Restart the services with your restored data
cd ~/crawl4ai-mcp
make start  # Or: docker compose --profile core up -d

# Your old volumes (crawl4aimcp_*) remain untouched as a secondary backup

# Alternative: Direct copy from old volumes (if backups failed)
# Only use this if your backups from Step 1 didn't work
docker compose down
docker run --rm -v crawl4aimcp_qdrant-data:/source -v crawl4ai_mcp_deimos_qdrant-data:/dest alpine cp -a /source/. /dest/
docker run --rm -v crawl4aimcp_valkey-data:/source -v crawl4ai_mcp_deimos_valkey-data:/dest alpine cp -a /source/. /dest/
docker run --rm -v crawl4aimcp_neo4j-data:/source -v crawl4ai_mcp_deimos_neo4j-data:/dest alpine cp -a /source/. /dest/
docker compose --profile core up -d
```

### Step 6: Verify Migration

```bash
# Working directory: Your installation directory
# Check service health
make health
# or
docker compose ps

# Check logs for any errors
make logs
# or
docker compose logs --tail=50

# Test MCP endpoint
curl http://localhost:8051/health

# Check Qdrant
curl http://localhost:6333/readyz
```

### Step 7: Smoke Tests

```python
# Working directory: Any location
# Quick test script
import requests

# Test MCP Server
response = requests.get("http://localhost:8051/health")
print(f"MCP Server: {response.status_code}")

# Test search functionality
search_data = {"query": "test search"}
response = requests.post("http://localhost:8051/search", json=search_data)
print(f"Search API: {response.status_code}")
```

## Rollback Plan

If issues occur, rollback to previous setup:

```bash
# Working directory: Your installation directory
cd ~/crawl4ai-mcp  # or your installation path

# Stop new services
docker compose down

# Checkout previous version
git checkout main  # or your previous branch

# Restore old docker-compose files from archives
cp archives/docker-compose/docker-compose.prod.yml .

# Restore data from backup (if reverting to old volume names)
# Working directory: Change to backup directory
cd ~/crawl4ai-backup-$(date +%Y%m%d)
docker run --rm -v crawl4aimcp_qdrant-data:/data -v $(pwd):/backup alpine tar xzf /backup/qdrant-data.tar.gz -C /data
docker run --rm -v crawl4aimcp_valkey-data:/data -v $(pwd):/backup alpine tar xzf /backup/valkey-data.tar.gz -C /data
docker run --rm -v crawl4aimcp_neo4j-data:/data -v $(pwd):/backup alpine tar xzf /backup/neo4j-data.tar.gz -C /data

# Start old services
docker compose -f docker-compose.prod.yml up -d
```

## Key Differences to Note

### 1. **Single Docker Compose File**

- Old: `docker-compose.prod.yml`, `docker-compose.dev.yml`, `docker-compose.test.yml`
- New: Single `docker-compose.yml` with profiles

### 2. **Simplified Commands**

- Old: `docker compose -f docker-compose.prod.yml up -d`
- New: `make start` or `docker compose --profile core up -d`

### 3. **Security Improvements**

- All services now run as non-root users
- Added `no-new-privileges` security option
- Proper capability drops

### 4. **Logging**

- All services now have log rotation configured
- Max 10MB per file, 3 files total

### 5. **Health Checks**

- Improved health check configurations
- Better startup dependencies

## Monitoring After Migration

### Check Resource Usage

```bash
# Monitor container stats
docker stats

# Check disk usage
docker system df
```

### Monitor Logs

```bash
# Follow logs for issues
make logs
# or
docker compose logs -f --tail=100
```

### Performance Metrics

```bash
# Check response times
time curl http://localhost:8051/health

# Monitor Qdrant performance
curl http://localhost:6333/metrics
```

## Common Issues & Solutions

### Issue 1: Playwright Browser Missing

If you see an error about Playwright browsers not being installed:

```text
Error: BrowserType.launch: Executable doesn't exist at /home/appuser/.cache/ms-playwright/chromium-1181/chrome-linux/chrome
```

**Solution**: Rebuild the Docker image with the updated Dockerfile:

```bash
# Force rebuild to include Playwright browsers
docker compose build --no-cache mcp-crawl4ai

# Then restart services
docker compose --profile core up -d
```

### Issue 2: Port Conflicts

```bash
# Check if ports are in use
lsof -i :8051
lsof -i :6333

# Solution: Change ports in .env file
PORT=8052  # Different port for MCP
```

### Issue 2: Volume Permissions

```bash
# Fix volume permissions if needed
docker compose down
sudo chown -R 1000:1000 data/
docker compose --profile core up -d
```

### Issue 3: Memory Issues

```bash
# Check Docker resources
docker info | grep -i memory

# Increase Docker Desktop memory if needed
# Settings -> Resources -> Memory
```

## Migration Validation Checklist

After completing the migration, verify:

- [ ] All services are running (`docker compose ps`)
- [ ] No error logs in first 5 minutes (`make logs`)
- [ ] MCP Server responds (`curl http://localhost:8051/health`)
- [ ] Qdrant is accessible (`curl http://localhost:6333/readyz`)
- [ ] Search functionality works (test with sample query)
- [ ] Previous data is accessible (vector search returns results)
- [ ] Performance is comparable or better
- [ ] Disk usage is reasonable (`docker system df`)
- [ ] Memory usage is stable (`docker stats`)
- [ ] Backup is safely stored

## Quick Reference: Command Mapping

| Old Command | New Command | Purpose |
|-------------|-------------|---------|
| `docker compose -f docker-compose.prod.yml up -d` | `make start` | Start production |
| `docker compose -f docker-compose.prod.yml down` | `make stop` | Stop services |
| `docker compose -f docker-compose.prod.yml logs` | `make logs` | View logs |
| `docker compose -f docker-compose.prod.yml ps` | `make status` | Check status |
| `docker compose -f docker-compose.prod.yml restart` | `make restart` | Restart services |
| `docker compose -f docker-compose.dev.yml up` | `make dev` | Development mode |

## Environment-Specific Notes

### AWS/Cloud Deployment

If deploying to AWS or other cloud providers:

1. Ensure security groups allow required ports
2. Consider using managed services (RDS for PostgreSQL, ElastiCache for Redis)
3. Use secrets manager for API keys instead of .env files
4. Configure proper backup policies for volumes

### Kubernetes Migration

If moving to Kubernetes:

1. Use the new Docker image: `krashnicov/crawl4ai-mcp:latest`
2. Convert docker-compose.yml to K8s manifests using Kompose
3. Create ConfigMaps for configuration
4. Use Secrets for sensitive data
5. Set up PersistentVolumeClaims for data persistence

## Support & Verification

After migration, verify everything is working:

1. **API Endpoints**: Test all critical endpoints
2. **Data Integrity**: Verify vector searches return expected results
3. **Performance**: Compare response times with baseline
4. **Logs**: No critical errors in first 30 minutes

## Contact for Issues

If you encounter problems:

1. Check logs: `make logs`
2. Review troubleshooting in `docs/INSTALLATION.md`
3. Create issue with migration details on GitHub
4. Include output of `docker compose ps` and relevant error logs

## Appendix: Complete Environment Variables

### Required Variables

```env
# API Keys
OPENAI_API_KEY=sk-...  # Required for embeddings

# Server Configuration
PORT=8051
HOST=0.0.0.0
TRANSPORT=http
```

### Optional Variables

```env
# Additional AI Providers
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
COHERE_API_KEY=...

# Database Configuration
VECTOR_DATABASE=qdrant  # or supabase
QDRANT_API_KEY=  # For production security
NEO4J_PASSWORD=password  # Change in production

# Feature Flags
USE_RERANKING=true
ENHANCED_CONTEXT=true
ENABLE_AGENTIC_RAG=true
ENABLE_HYBRID_SEARCH=false

# Performance Tuning
MAX_CONCURRENT_CRAWLS=10
CHUNK_SIZE=2000
EMBEDDING_BATCH_SIZE=100
```

---

**Note**: This migration maintains all your data and settings. The main changes are structural improvements for better maintainability and security. Your application functionality remains the same.

**Document Version**: 1.0.0  
**Last Updated**: 2025-08-09  
**Applies to**: Migration from v0.0.x to v0.1.0
