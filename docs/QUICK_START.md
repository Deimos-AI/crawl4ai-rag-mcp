# 🚀 Quick Start Guide

Get Crawl4AI MCP Server running in under 3 minutes!

## 📋 Prerequisites

- Docker Desktop installed ([Download here](https://docs.docker.com/get-docker/))
- 4GB RAM minimum
- 10GB free disk space

## 🎯 3-Step Installation

### Step 1: Install

```bash
curl -sSL https://raw.githubusercontent.com/krashnicov/crawl4ai-mcp/main/scripts/install.sh | bash
```

### Step 2: Configure API Keys

Edit the `.env` file in `~/crawl4ai-mcp/`:

```bash
cd ~/crawl4ai-mcp
nano .env  # or use your favorite editor
```

Add your API keys:
```env
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here  # Optional
```

### Step 3: Start Services

```bash
make start
```

That's it! 🎉

## 🌐 Access Points

- **MCP Server**: http://localhost:8051
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **API Documentation**: http://localhost:8051/docs

## 🛠️ Basic Commands

```bash
make logs    # View logs
make status  # Check service health
make stop    # Stop services
make restart # Restart services
```

## 🔧 MCP Client Configuration

### Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "crawl4ai": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "--network", "host", "krashnicov/crawl4ai-mcp:latest"]
    }
  }
}
```

### Generic MCP Client

```bash
# Connect to the server
mcp connect http://localhost:8051
```

## 📝 Example Usage

### Search and Crawl

```python
# Search for content
results = search(query="AI web crawling tools")

# Crawl a specific URL
content = scrape_urls(url="https://example.com")

# Smart crawl with RAG
data = smart_crawl_url(
    url="https://docs.example.com",
    query="installation guide"
)
```

### RAG Queries

```python
# Perform RAG query on stored content
answer = perform_rag_query(
    query="How to install Docker?",
    source="docs.docker.com"
)
```

## 🚨 Troubleshooting

### Services won't start
```bash
# Check Docker is running
docker --version

# Check ports are free
lsof -i :8051
lsof -i :6333

# View detailed logs
make logs
```

### Memory issues
```bash
# Increase Docker memory allocation
# Docker Desktop → Settings → Resources → Memory: 6GB+
```

### Permission errors
```bash
# Fix directory permissions
sudo chown -R $USER:$USER ~/crawl4ai-mcp
```

## 📚 Next Steps

- Read the full [Installation Guide](INSTALLATION.md)
- Configure advanced settings in [Configuration Guide](CONFIGURATION.md)
- Explore the [API Documentation](http://localhost:8051/docs)
- Join our [Discord Community](https://discord.gg/crawl4ai)

## 💡 Pro Tips

1. **Use profiles for different environments:**
   ```bash
   make start           # Minimal setup (core profile)
   docker compose --profile full up -d   # Full features
   docker compose --profile dev up -d    # Development mode
   ```

2. **Monitor resource usage:**
   ```bash
   docker stats
   ```

3. **Quick aliases (after restart):**
   ```bash
   crawl4ai-start   # Start services
   crawl4ai-stop    # Stop services
   crawl4ai-logs    # View logs
   crawl4ai-status  # Check status
   ```

---

Need help? Check our [Troubleshooting Guide](../README.md#troubleshooting) or [open an issue](https://github.com/krashnicov/crawl4ai-mcp/issues).