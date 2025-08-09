# Development with stdio Mode

This guide explains how to set up and use the hybrid development environment with stdio transport mode for easier testing and debugging of the MCP server.

## Overview

The hybrid development setup allows you to:
- Run the MCP server locally with **stdio transport** for direct process communication
- Keep database services (Qdrant, Neo4j, SearXNG, Valkey) running in Docker containers
- Simplify testing and debugging without network overhead
- Maintain consistency with production HTTP mode

## Why stdio Mode?

stdio (Standard Input/Output) mode offers several advantages for development:

1. **Direct Process Communication**: The MCP client spawns the server process directly and communicates via stdin/stdout pipes
2. **Easier Debugging**: Direct process attachment for debugging tools
3. **No Network Configuration**: No ports, hosts, or network issues to troubleshoot
4. **Faster Development Cycle**: Instant server restarts without Docker rebuild

## Setup Instructions

### Prerequisites

- Docker and Docker Compose installed
- UV package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Python 3.11+ installed locally
- MCP client that supports stdio mode (e.g., Claude Desktop, mcp-cli)

### Initial Setup

1. **Create the development environment file** (already created):
   ```bash
   # The .env.dev file has been created with stdio configuration
   # It sets TRANSPORT=stdio and configures localhost URLs for services
   ```

2. **Install Python dependencies locally**:
   ```bash
   uv sync
   ```

## Usage

### Quick Start

The easiest way to start development:

```bash
# Start all services and run MCP server in stdio mode
make dev-hybrid
```

### Step-by-Step Usage

1. **Start database services only**:
   ```bash
   make dev-services
   ```
   
   This starts:
   - Qdrant (vector database) on http://localhost:6333
   - Neo4j (graph database) on http://localhost:7474
   - SearXNG (search engine) on http://localhost:8080
   - Valkey (cache) on localhost:6379

2. **Run the MCP server in stdio mode**:
   ```bash
   make dev-stdio
   ```
   
   Or directly:
   ```bash
   export $(cat .env.dev | grep -v '^#' | xargs) && uv run python src/main.py
   ```

3. **Configure your MCP client** to use stdio mode with the command:
   ```json
   {
     "command": "uv",
     "args": ["run", "python", "src/main.py"],
     "env": {
       "DOTENV_PATH": ".env.dev"
     }
   }
   ```

### Additional Commands

- **View service logs**:
  ```bash
  make dev-services-logs
  ```

- **Stop services**:
  ```bash
  make dev-services-down
  ```

- **Restart just the MCP server** (when services are running):
  Simply stop the server with Ctrl+C and run `make dev-stdio` again

## Environment Configuration

The `.env.dev` file configures:

- `TRANSPORT=stdio` - Enables stdio mode
- Service URLs pointing to localhost (for Docker services exposed to host)
- Development-friendly settings (debug mode, verbose logging)
- Disabled production features for faster startup

### Key Configuration Differences

| Setting | Production (.env) | Development (.env.dev) |
|---------|------------------|----------------------|
| TRANSPORT | http | stdio |
| SEARXNG_URL | http://searxng:8080 | http://localhost:8080 |
| QDRANT_URL | http://qdrant:6333 | http://localhost:6333 |
| NEO4J_URI | bolt://neo4j:7687 | bolt://localhost:7687 |
| DEBUG | false | true |

## Testing with MCP Clients

### Claude Desktop Configuration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "crawl4ai": {
      "command": "uv",
      "args": ["run", "python", "src/main.py"],
      "cwd": "/path/to/crawl4aimcp",
      "env": {
        "DOTENV_PATH": ".env.dev"
      }
    }
  }
}
```

### mcp-cli Testing

```bash
# Install mcp-cli if not already installed
npm install -g @modelcontextprotocol/cli

# Test the server
mcp-cli --stdio "uv run python src/main.py"
```

## Troubleshooting

### Services Not Accessible

If services are not accessible on localhost:

1. Check services are running:
   ```bash
   docker compose ps
   ```

2. Verify port bindings:
   ```bash
   docker compose port qdrant 6333
   docker compose port neo4j 7687
   docker compose port searxng 8080
   ```

3. Check service health:
   ```bash
   docker compose ps --format "table {{.Service}}\t{{.Status}}"
   ```

### MCP Server Won't Start

1. Ensure `.env.dev` exists:
   ```bash
   ls -la .env.dev
   ```

2. Verify environment variables are loaded:
   ```bash
   export $(cat .env.dev | grep -v '^#' | xargs) && echo $TRANSPORT
   # Should output: stdio
   ```

3. Check Python dependencies:
   ```bash
   uv sync
   ```

### Connection Errors to Services

If the MCP server can't connect to services:

1. Ensure services are healthy:
   ```bash
   make dev-services-logs
   ```

2. Test service connectivity:
   ```bash
   # Test Qdrant
   curl http://localhost:6333/dashboard
   
   # Test Neo4j
   curl http://localhost:7474
   
   # Test SearXNG
   curl http://localhost:8080/healthz
   ```

## Switching Between Modes

### From stdio to HTTP Mode

To switch back to full Docker HTTP mode:

```bash
# Stop stdio development
# (Ctrl+C in the terminal running the MCP server)

# Stop services
make dev-services-down

# Start full Docker environment
make dev-bg
```

### From HTTP to stdio Mode

To switch from Docker HTTP to stdio mode:

```bash
# Stop Docker environment
make dev-down

# Start hybrid environment
make dev-hybrid
```

## Best Practices

1. **Use stdio mode for**:
   - Rapid development and testing
   - Debugging MCP tool implementations
   - Testing with MCP clients
   - Local development without Docker overhead

2. **Use HTTP mode for**:
   - Production-like testing
   - Multi-service integration testing
   - Deployment preparation
   - Team collaboration with consistent environment

3. **Keep services running**: Start services once with `make dev-services` and leave them running throughout your development session

4. **Hot reload**: The MCP server will use your local source files, so changes are reflected immediately upon restart

5. **Environment isolation**: The `.env.dev` file ensures development settings don't affect production

## Architecture Diagram

```
┌──────────────────┐
│   MCP Client     │
│ (Claude Desktop) │
└────────┬─────────┘
         │ stdio (stdin/stdout)
         │
┌────────▼─────────┐
│   MCP Server     │
│  (Local Python)  │
│   TRANSPORT=stdio│
└────────┬─────────┘
         │ HTTP/Network
         │
┌────────▼─────────────────────────┐
│        Docker Services            │
│                                   │
│  ┌─────────┐  ┌─────────┐       │
│  │ Qdrant  │  │  Neo4j  │       │
│  │  :6333  │  │  :7687  │       │
│  └─────────┘  └─────────┘       │
│                                   │
│  ┌─────────┐  ┌─────────┐       │
│  │ SearXNG │  │ Valkey  │       │
│  │  :8080  │  │  :6379  │       │
│  └─────────┘  └─────────┘       │
└───────────────────────────────────┘
```

## Summary

The hybrid stdio development setup provides the best of both worlds:
- **Fast iteration** with local Python execution
- **No database hassle** with Docker-managed services  
- **Easy debugging** with direct process communication
- **Production parity** with the same service configuration

Use `make dev-hybrid` to get started quickly, or follow the step-by-step instructions for more control over the development environment.