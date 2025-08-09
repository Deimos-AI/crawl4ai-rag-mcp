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

# Docker compose files (for legacy support)
DOCKER_COMPOSE := docker compose
DOCKER_COMPOSE_PROD := $(DOCKER_COMPOSE) -f archives/docker-compose/docker-compose.prod.yml
DOCKER_COMPOSE_DEV := $(DOCKER_COMPOSE) -f archives/docker-compose/docker-compose.dev.yml
DOCKER_COMPOSE_TEST := $(DOCKER_COMPOSE) -f archives/docker-compose/docker-compose.test.yml
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
.PHONY: docker-build docker-push docker-scan
.PHONY: dirs env-setup quickstart
.PHONY: restart status shell python lint format
.PHONY: dev-bg dev-logs dev-down dev-restart dev-rebuild
.PHONY: test-unit test-integration test-all test-coverage
.PHONY: clean-all env-check deps ps
.PHONY: prod-down prod-logs prod-ps prod-restart

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
	@mkdir -p data/{qdrant,neo4j,valkey}
	@mkdir -p logs
	@mkdir -p analysis_scripts/{user_scripts,validation_results}
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
start: ## Start core services
	@echo "$(GREEN)Starting services...$(NC)"
	@docker compose --profile core up -d
	@echo "$(GREEN)Waiting for services to be ready...$(NC)"
	@sleep 5
	@$(MAKE) health
	@echo ""
	@echo "$(GREEN)🚀 Services running at:$(NC)"
	@echo "  • MCP Server: http://localhost:8051"
	@echo "  • Qdrant Dashboard: http://localhost:6333/dashboard"
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
# Development Environment (LEGACY SUPPORT)
# ============================================
dev: env-check ## Start development with watch mode
	@echo "$(COLOR_GREEN)Starting development environment with watch mode...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) up --build --watch

dev-bg: env-check ## Start development in background
	@echo "$(COLOR_GREEN)Starting development environment in background...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) up -d --build
	@echo "$(COLOR_GREEN)Starting watch mode...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) watch

dev-logs: ## View development logs
	$(DOCKER_COMPOSE_DEV) logs -f mcp-crawl4ai

dev-down: ## Stop development environment
	@echo "$(COLOR_YELLOW)Stopping development environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) down

dev-restart: ## Restart development services
	@echo "$(COLOR_YELLOW)Restarting development services...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) restart mcp-crawl4ai

dev-rebuild: ## Rebuild development environment
	@echo "$(COLOR_YELLOW)Rebuilding development environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) down
	$(DOCKER_COMPOSE_DEV) build --no-cache
	$(MAKE) dev

# ============================================
# Production Environment (LEGACY SUPPORT)
# ============================================
prod: env-check ## Start production environment
	@echo "$(COLOR_GREEN)Starting production environment...$(COLOR_RESET)"
	@docker compose --profile core up -d

prod-down: ## Stop production environment
	@echo "$(COLOR_YELLOW)Stopping production environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_PROD) down

prod-logs: ## View production logs
	$(DOCKER_COMPOSE_PROD) logs -f

prod-ps: ## Show production containers
	$(DOCKER_COMPOSE_PROD) ps

prod-restart: ## Restart production services
	@echo "$(COLOR_YELLOW)Restarting production services...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_PROD) restart

# ============================================
# Testing
# ============================================
test: test-unit ## Run unit tests (alias)

test-unit: ## Run unit tests only
	@echo "$(COLOR_GREEN)Running unit tests...$(COLOR_RESET)"
	@if [ -f /.dockerenv ]; then \
		$(PYTEST) tests/unit -v --tb=short; \
	else \
		$(DOCKER_COMPOSE_TEST) run --rm mcp-crawl4ai-test $(PYTEST) tests/unit -v --tb=short; \
	fi

test-integration: ## Run integration tests
	@echo "$(COLOR_GREEN)Running integration tests with Docker services...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_TEST) up -d
	$(DOCKER_COMPOSE_TEST) run --rm mcp-crawl4ai-test $(PYTEST) tests/integration -v
	$(DOCKER_COMPOSE_TEST) down

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
docker-build: ## Build Docker image
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