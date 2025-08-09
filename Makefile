# Crawl4AI MCP Server - Makefile with 2025 Best Practices
SHELL := /bin/bash
.DELETE_ON_ERROR:  # Clean up on failure  
.ONESHELL:         # Run recipes in single shell

# ============================================
# Variables
# ============================================
APP_NAME := crawl4ai-mcp
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "0.1.0")
REGISTRY := docker.io/krashnicov
IMAGE := $(REGISTRY)/$(APP_NAME)
PLATFORMS := linux/amd64,linux/arm64

# Docker compose command
DOCKER_COMPOSE := docker compose
PYTHON := uv run python
PYTEST := uv run pytest
RUFF := uv run ruff

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color
COLOR_GREEN := $(GREEN)
COLOR_YELLOW := $(YELLOW)
COLOR_RED := $(RED)
COLOR_RESET := $(NC)

# ============================================
# PHONY Targets (Best Practice)
# ============================================
.PHONY: help install start stop clean test build push release
.PHONY: dev prod logs health security-scan
.PHONY: docker-build docker-push docker-scan build-local
.PHONY: dirs env-setup quickstart
.PHONY: restart status shell python lint format
.PHONY: dev-bg dev-logs dev-down dev-restart dev-rebuild
.PHONY: test-unit test-integration test-all test-coverage
.PHONY: clean-all env-check deps ps
.PHONY: prod-down prod-logs prod-ps prod-restart
.PHONY: start-full start-dev volumes backup restore

# ============================================
# Default Target
# ============================================
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)╔════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║   Crawl4AI MCP Server - Make Commands     ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  $(YELLOW)make install$(NC)        # First-time setup"
	@echo "  $(YELLOW)make start$(NC)          # Start services"
	@echo "  $(YELLOW)make logs$(NC)           # View logs"
	@echo "  $(YELLOW)make stop$(NC)           # Stop services"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BLUE)For detailed help on legacy commands, run: make help-legacy$(NC)"

help-legacy: ## Show legacy command help
	@echo "$(COLOR_GREEN)Legacy Development Commands$(COLOR_RESET)"
	@echo "============================================"
	@echo ""
	@echo "$(COLOR_YELLOW)Development Environment:$(COLOR_RESET)"
	@echo "  make dev             - Start development with watch mode"
	@echo "  make dev-bg          - Start development in background"
	@echo "  make dev-logs        - View development logs"
	@echo "  make dev-down        - Stop development environment"
	@echo "  make dev-restart     - Restart development services"
	@echo "  make dev-rebuild     - Rebuild development environment"
	@echo ""
	@echo "$(COLOR_YELLOW)Testing:$(COLOR_RESET)"
	@echo "  make test-unit       - Run unit tests"
	@echo "  make test-integration- Run integration tests"
	@echo "  make test-all        - Run all tests"
	@echo "  make test-coverage   - Run tests with coverage"

# ============================================
# Installation & Setup (NEW)
# ============================================
dirs: ## Create required directories
	@echo "$(GREEN)Creating directory structure...$(NC)"
	@mkdir -p data
	@mkdir -p logs
	@mkdir -p analysis_scripts/{user_scripts,validation_results}
	@mkdir -p docker/neo4j/import
	@mkdir -p notebooks
	@echo "$(GREEN)✓ Directories created$(NC)"

env-setup: ## Setup environment file
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creating .env from template...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN)✓ Environment file created$(NC)"; \
		echo "$(YELLOW)⚠ Please edit .env with your API keys$(NC)"; \
	else \
		echo "$(GREEN)✓ Environment file exists$(NC)"; \
	fi

env-check: ## Validate environment variables
	@echo "$(COLOR_GREEN)Checking environment configuration...$(COLOR_RESET)"
	@if [ ! -f .env ]; then \
		echo "$(COLOR_RED)Error: .env file not found$(COLOR_RESET)"; \
		echo "$(COLOR_YELLOW)Creating from template...$(COLOR_RESET)"; \
		cp .env.example .env; \
		echo "$(COLOR_GREEN)✓ Created .env file - please configure your API keys$(COLOR_RESET)"; \
		exit 1; \
	fi
	@echo "$(COLOR_GREEN)✓ Environment configured$(COLOR_RESET)"

install: dirs env-setup ## One-click installation
	@echo "$(BLUE)╔════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║     Installing Crawl4AI MCP Server        ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)Checking Docker...$(NC)"
	@docker --version || (echo "$(RED)✗ Docker not installed$(NC)" && exit 1)
	@docker compose version || (echo "$(RED)✗ Docker Compose not installed$(NC)" && exit 1)
	@echo "$(GREEN)✓ Docker ready$(NC)"
	@echo ""
	@echo "$(GREEN)Pulling images...$(NC)"
	@docker compose pull
	@echo ""
	@echo "$(GREEN)✅ Installation complete!$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Edit .env file with your API keys"
	@echo "  2. Run 'make start' to start services"
	@echo ""

quickstart: install start ## Complete setup and start

# ============================================
# Service Management (NEW SIMPLIFIED)
# ============================================
start: ## Start core services (includes Neo4j)
	@echo "$(GREEN)Starting services...$(NC)"
	@docker compose --profile core up -d
	@echo "$(GREEN)Waiting for services to be ready...$(NC)"
	@sleep 5
	@$(MAKE) health
	@echo ""
	@echo "$(GREEN)🚀 Services running at:$(NC)"
	@echo "  • MCP Server: http://localhost:8051"
	@echo "  • Qdrant Dashboard: http://localhost:6333/dashboard"
	@echo "  • Neo4j Browser: http://localhost:7474"
	@echo "  • SearXNG Search: http://localhost:8080"
	@echo ""

start-full: ## Start full services (same as core now)
	@$(MAKE) start

start-dev: ## Start development environment with all tools
	@echo "$(GREEN)Starting development environment...$(NC)"
	@docker compose --profile dev up -d
	@echo "$(GREEN)Waiting for services to be ready...$(NC)"
	@sleep 5
	@$(MAKE) health
	@echo ""
	@echo "$(GREEN)🚀 Development services running at:$(NC)"
	@echo "  • MCP Server: http://localhost:8051"
	@echo "  • Qdrant Dashboard: http://localhost:6333/dashboard"
	@echo "  • Neo4j Browser: http://localhost:7474"
	@echo "  • SearXNG Search: http://localhost:8080"
	@echo "  • Mailhog UI: http://localhost:8025"
	@echo "  • Jupyter Lab: http://localhost:8888 (token: crawl4ai)"
	@echo ""

stop: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	@docker compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: stop start ## Restart services

logs: ## View service logs
	@docker compose logs -f --tail=100

health: ## Check service health
	@echo "$(GREEN)Checking service health...$(NC)"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}"

status: health ## Alias for health

ps: status ## Show running containers

# ============================================
# Volume Management (NEW)
# ============================================
volumes: ## List all Docker volumes for this project
	@echo "$(GREEN)Project volumes:$(NC)"
	@docker volume ls | grep -E "crawl4ai" || echo "No volumes found"

backup: ## Backup data volumes to ./backups directory
	@echo "$(GREEN)Creating backup...$(NC)"
	@mkdir -p backups/$(shell date +%Y%m%d-%H%M%S)
	@cd backups/$(shell date +%Y%m%d-%H%M%S) && \
		docker run --rm -v crawl4ai_mcp_qdrant-data:/data -v $$(pwd):/backup alpine tar czf /backup/qdrant-data.tar.gz -C /data . && \
		docker run --rm -v crawl4ai_mcp_valkey-data:/data -v $$(pwd):/backup alpine tar czf /backup/valkey-data.tar.gz -C /data . && \
		docker run --rm -v crawl4ai_mcp_neo4j-data:/data -v $$(pwd):/backup alpine tar czf /backup/neo4j-data.tar.gz -C /data .
	@echo "$(GREEN)✓ Backup complete in backups/$(NC)"

restore: ## Restore data volumes from backup (specify BACKUP_DIR)
	@if [ -z "$(BACKUP_DIR)" ]; then \
		echo "$(RED)Error: Specify BACKUP_DIR=backups/YYYYMMDD-HHMMSS$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restoring from $(BACKUP_DIR)...$(NC)"
	@docker compose down
	@docker run --rm -v crawl4ai_mcp_qdrant-data:/data -v $$(pwd)/$(BACKUP_DIR):/backup alpine tar xzf /backup/qdrant-data.tar.gz -C /data
	@docker run --rm -v crawl4ai_mcp_valkey-data:/data -v $$(pwd)/$(BACKUP_DIR):/backup alpine tar xzf /backup/valkey-data.tar.gz -C /data
	@docker run --rm -v crawl4ai_mcp_neo4j-data:/data -v $$(pwd)/$(BACKUP_DIR):/backup alpine tar xzf /backup/neo4j-data.tar.gz -C /data
	@echo "$(GREEN)✓ Restore complete$(NC)"

# ============================================
# Development Environment (UPDATED)
# ============================================
dev: start-dev ## Start development environment

dev-bg: ## Start development in background with watch
	@echo "$(COLOR_GREEN)Starting development environment in background...$(COLOR_RESET)"
	@docker compose --profile dev up -d --build
	@echo "$(COLOR_GREEN)Starting watch mode...$(COLOR_RESET)"
	@docker compose --profile dev watch

dev-logs: ## View development logs
	@docker compose logs -f mcp-crawl4ai

dev-down: ## Stop development environment
	@echo "$(COLOR_YELLOW)Stopping development environment...$(COLOR_RESET)"
	@docker compose down

dev-restart: ## Restart development services
	@echo "$(COLOR_YELLOW)Restarting development services...$(COLOR_RESET)"
	@docker compose restart mcp-crawl4ai

dev-rebuild: ## Rebuild development environment
	@echo "$(COLOR_YELLOW)Rebuilding development environment...$(COLOR_RESET)"
	@docker compose down
	@docker compose build --no-cache mcp-crawl4ai
	@$(MAKE) dev

# ============================================
# Production Environment (UPDATED)
# ============================================
prod: start ## Start production environment (alias for start)

prod-down: stop ## Stop production environment (alias for stop)

prod-logs: logs ## View production logs (alias for logs)

prod-ps: ps ## Show production containers (alias for ps)

prod-restart: restart ## Restart production services (alias for restart)

# ============================================
# Testing
# ============================================
test: test-unit ## Run unit tests (alias)

test-unit: ## Run unit tests only
	@echo "$(COLOR_GREEN)Running unit tests...$(COLOR_RESET)"
	@if [ -f /.dockerenv ]; then \
		$(PYTEST) tests/unit -v --tb=short; \
	else \
		$(DOCKER_COMPOSE) run --rm mcp-crawl4ai $(PYTEST) tests/unit -v --tb=short; \
	fi

test-integration: ## Run integration tests
	@echo "$(COLOR_GREEN)Running integration tests with Docker services...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) --profile core up -d
	$(DOCKER_COMPOSE) run --rm mcp-crawl4ai $(PYTEST) tests/integration -v
	$(DOCKER_COMPOSE) down

test-all: ## Run all tests
	@echo "$(COLOR_GREEN)Running all tests...$(COLOR_RESET)"
	$(MAKE) test-unit
	$(MAKE) test-integration

test-coverage: ## Run tests with coverage
	@echo "$(COLOR_GREEN)Running tests with coverage...$(COLOR_RESET)"
	@docker compose run --rm mcp-crawl4ai uv run pytest --cov=src --cov-fail-under=80

test-quick: ## Run quick unit tests
	@docker compose run --rm mcp-crawl4ai uv run pytest tests/unit -v

# ============================================
# Docker Build & Release (NEW)
# ============================================
build-local: ## Build Docker image locally
	@echo "$(GREEN)Building local Docker image...$(NC)"
	@docker compose build mcp-crawl4ai
	@echo "$(GREEN)✓ Local build complete$(NC)"

docker-build: ## Build Docker image for multiple platforms
	@echo "$(GREEN)Building $(IMAGE):$(VERSION)...$(NC)"
	@docker buildx create --use --name multiarch || true
	@docker buildx build \
		--platform $(PLATFORMS) \
		--tag $(IMAGE):$(VERSION) \
		--tag $(IMAGE):latest \
		--cache-from type=registry,ref=$(IMAGE):buildcache \
		--cache-to type=registry,ref=$(IMAGE):buildcache,mode=max \
		--load .
	@echo "$(GREEN)✓ Build complete$(NC)"

docker-push: ## Push to Docker Hub
	@echo "$(GREEN)Pushing $(IMAGE):$(VERSION)...$(NC)"
	@docker push $(IMAGE):$(VERSION)
	@docker push $(IMAGE):latest
	@echo "$(GREEN)✓ Push complete$(NC)"

docker-scan: ## Security scan with Trivy
	@echo "$(GREEN)Running security scan...$(NC)"
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy image --severity HIGH,CRITICAL $(IMAGE):$(VERSION)

build: docker-build ## Alias for docker-build

push: docker-push ## Alias for docker-push

security-scan: docker-scan ## Alias for docker-scan

release: test security-scan build push ## Complete release process
	@echo "$(GREEN)✅ Release $(VERSION) complete!$(NC)"
	@echo "$(YELLOW)Don't forget to:$(NC)"
	@echo "  1. Create GitHub release"
	@echo "  2. Update changelog"
	@echo "  3. Tag the commit"

# ============================================
# Development Helpers
# ============================================
shell: ## Open shell in container
	@docker compose exec mcp-crawl4ai /bin/bash || \
		docker compose run --rm mcp-crawl4ai /bin/bash

python: ## Open Python REPL
	@docker compose exec mcp-crawl4ai python || \
		docker compose run --rm mcp-crawl4ai python

lint: ## Run code linting
	@echo "$(COLOR_GREEN)Running linting...$(COLOR_RESET)"
	@docker compose run --rm mcp-crawl4ai uv run ruff check src/ tests/

format: ## Format code
	@echo "$(COLOR_GREEN)Formatting code...$(COLOR_RESET)"
	@docker compose run --rm mcp-crawl4ai uv run ruff format src/ tests/

deps: ## Install/update dependencies
	@echo "$(COLOR_GREEN)Installing dependencies...$(COLOR_RESET)"
	@uv sync

# ============================================
# Cleanup
# ============================================
clean: ## Clean test artifacts and caches
	@echo "$(COLOR_YELLOW)Cleaning test artifacts and caches...$(COLOR_RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@rm -rf htmlcov coverage.xml .coverage.* 2>/dev/null || true
	@echo "$(COLOR_GREEN)✓ Cleanup complete$(COLOR_RESET)"

clean-all: stop clean ## Clean everything including volumes
	@echo "$(RED)⚠ WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		rm -rf data logs; \
		echo "$(GREEN)✓ Full cleanup complete$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi