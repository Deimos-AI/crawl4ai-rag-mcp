#!/usr/bin/env bash
set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# ============================================
# Crawl4AI MCP Server - Installation Script
# ============================================

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/krashnicov/crawl4ai-mcp.git"
INSTALL_DIR="${HOME}/crawl4ai-mcp"

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     Crawl4AI MCP Server Installer         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

check_docker_compose() {
    if docker compose version >/dev/null 2>&1; then
        print_success "Docker Compose is installed"
        return 0
    else
        print_error "Docker Compose is not installed"
        return 1
    fi
}

# Main installation
main() {
    print_header

    echo -e "${GREEN}Starting installation...${NC}"
    echo ""

    # Check dependencies
    echo -e "${BLUE}Checking dependencies...${NC}"
    
    if ! check_command docker; then
        print_error "Docker is required but not installed."
        echo "Please install Docker from: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! check_docker_compose; then
        print_error "Docker Compose is required but not installed."
        echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
        exit 1
    fi

    check_command git || print_warning "Git not found, downloading as archive instead"
    echo ""

    # Clone or download repository
    echo -e "${BLUE}Setting up repository...${NC}"
    
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory $INSTALL_DIR already exists"
        read -p "Do you want to update it? (y/N) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$INSTALL_DIR"
            if [ -d .git ]; then
                git pull
                print_success "Repository updated"
            else
                print_warning "Not a git repository, skipping update"
            fi
        fi
    else
        if command -v git >/dev/null 2>&1; then
            git clone "$REPO_URL" "$INSTALL_DIR"
            print_success "Repository cloned"
        else
            # Download as archive if git is not available
            mkdir -p "$INSTALL_DIR"
            cd "$INSTALL_DIR"
            curl -L https://github.com/krashnicov/crawl4ai-mcp/archive/main.tar.gz | tar xz --strip-components=1
            print_success "Repository downloaded"
        fi
    fi

    cd "$INSTALL_DIR"
    echo ""

    # Create directory structure
    echo -e "${BLUE}Creating directory structure...${NC}"
    mkdir -p data/{qdrant,neo4j,valkey} logs analysis_scripts/{user_scripts,validation_results}
    print_success "Directories created"
    echo ""

    # Setup environment
    echo -e "${BLUE}Setting up environment...${NC}"
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_success "Environment file created from template"
            print_warning "Please edit .env file with your API keys"
        else
            print_error ".env.example not found"
            exit 1
        fi
    else
        print_success "Environment file already exists"
    fi
    echo ""

    # Pull Docker images
    echo -e "${BLUE}Pulling Docker images...${NC}"
    docker compose pull
    print_success "Docker images pulled"
    echo ""

    # Start services
    read -p "Do you want to start the services now? (Y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo -e "${BLUE}Starting services...${NC}"
        docker compose --profile core up -d
        print_success "Services started"
        echo ""
        
        # Wait for services
        echo -e "${BLUE}Waiting for services to be ready...${NC}"
        sleep 10
        
        # Check health
        if docker compose ps | grep -q "healthy"; then
            print_success "Services are healthy"
        else
            print_warning "Services are starting, please wait a moment"
        fi
        echo ""
    fi

    # Create convenience script
    echo -e "${BLUE}Creating convenience commands...${NC}"
    cat > "$HOME/.crawl4ai-mcp" << 'EOF'
# Crawl4AI MCP Server convenience functions
alias crawl4ai-start="cd $HOME/crawl4ai-mcp && make start"
alias crawl4ai-stop="cd $HOME/crawl4ai-mcp && make stop"
alias crawl4ai-logs="cd $HOME/crawl4ai-mcp && make logs"
alias crawl4ai-status="cd $HOME/crawl4ai-mcp && make status"
EOF

    # Add to shell profile
    SHELL_RC=""
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        if ! grep -q "crawl4ai-mcp" "$SHELL_RC"; then
            echo "" >> "$SHELL_RC"
            echo "# Crawl4AI MCP Server" >> "$SHELL_RC"
            echo "[ -f ~/.crawl4ai-mcp ] && source ~/.crawl4ai-mcp" >> "$SHELL_RC"
            print_success "Added convenience commands to $SHELL_RC"
        fi
    fi

    # Success message
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║        Installation Complete! 🎉          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Service URLs:${NC}"
    echo -e "  • MCP Server: ${YELLOW}http://localhost:8051${NC}"
    echo -e "  • Qdrant Dashboard: ${YELLOW}http://localhost:6333/dashboard${NC}"
    if [[ $(docker compose --profile full ps -q neo4j) ]]; then
        echo -e "  • Neo4j Browser: ${YELLOW}http://localhost:7474${NC}"
    fi
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo -e "  1. Edit ${YELLOW}$INSTALL_DIR/.env${NC} with your API keys"
    echo -e "  2. View logs: ${YELLOW}cd $INSTALL_DIR && make logs${NC}"
    echo -e "  3. Stop services: ${YELLOW}cd $INSTALL_DIR && make stop${NC}"
    echo ""
    echo -e "${BLUE}Quick Commands (after reopening terminal):${NC}"
    echo -e "  ${YELLOW}crawl4ai-start${NC}  - Start services"
    echo -e "  ${YELLOW}crawl4ai-stop${NC}   - Stop services"
    echo -e "  ${YELLOW}crawl4ai-logs${NC}   - View logs"
    echo -e "  ${YELLOW}crawl4ai-status${NC} - Check status"
    echo ""
    echo -e "${GREEN}Documentation:${NC} https://github.com/krashnicov/crawl4ai-mcp${NC}"
    echo ""
}

# Run main function
main "$@"