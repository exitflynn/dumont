#!/bin/bash

# CycleOPS Worker Startup Script - Cross-Platform
# Handles platform-specific setup and starts the worker agent
#
# Usage:
#   ./start_worker.sh [options]
#   
# Options:
#   --orchestrator-url URL     Orchestrator URL (default: http://localhost:5000)
#   --redis-host HOST          Redis host (default: localhost)
#   --redis-port PORT          Redis port (default: 6379)
#   --debug                    Enable debug logging
#   --no-venv                  Don't activate virtual environment
#   --help                     Show this help message

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ORCHESTRATOR_URL="http://localhost:5000"
REDIS_HOST="localhost"
REDIS_PORT="6379"
DEBUG_MODE=0
USE_VENV=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Functions
print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $(printf '%-62s' "$1")${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n"
}

print_check() {
    if [ $1 -eq 0 ]; then
        echo -e "  ${GREEN}✅${NC} $2"
    else
        echo -e "  ${RED}❌${NC} $2"
    fi
}

print_info() {
    echo -e "  ${BLUE}ℹ️${NC} $1"
}

print_warning() {
    echo -e "  ${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "  ${RED}❌${NC} $1"
}

print_success() {
    echo -e "  ${GREEN}✅${NC} $1"
}

show_help() {
    echo "CycleOPS Worker Startup Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --orchestrator-url URL     Orchestrator URL (default: http://localhost:5000)"
    echo "  --redis-host HOST          Redis host (default: localhost)"
    echo "  --redis-port PORT          Redis port (default: 6379)"
    echo "  --debug                    Enable debug logging"
    echo "  --no-venv                  Don't activate virtual environment"
    echo "  --help                     Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./start_worker.sh"
    echo "  ./start_worker.sh --orchestrator-url http://192.168.1.100:5000"
    echo "  ./start_worker.sh --debug --redis-host 192.168.1.100"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --orchestrator-url)
            ORCHESTRATOR_URL="$2"
            shift 2
            ;;
        --redis-host)
            REDIS_HOST="$2"
            shift 2
            ;;
        --redis-port)
            REDIS_PORT="$2"
            shift 2
            ;;
        --debug)
            DEBUG_MODE=1
            shift
            ;;
        --no-venv)
            USE_VENV=0
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Print header
print_header "CycleOPS Worker Agent"

# Step 1: Check Python
echo "${BLUE}[1/6] Checking Python Environment${NC}"
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
print_check 0 "Python $PYTHON_VERSION"

# Step 2: Activate virtual environment (if needed)
echo ""
echo "${BLUE}[2/6] Setting Up Virtual Environment${NC}"

if [ $USE_VENV -eq 1 ]; then
    # Priority: Use .venv-worker (Python 3.12 environment with CoreML support)
    if [ -d ".venv-worker" ]; then
        source ".venv-worker/bin/activate"
        print_check 0 "Worker virtual environment activated (.venv-worker)"
        
        # Verify Python version for CoreML
        PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -eq 12 ]; then
            print_check 0 "Python 3.12 detected - CoreML native bindings supported"
        elif [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 13 ]; then
            print_warning "Python 3.13+ detected - CoreML may not have native bindings"
            print_info "For CoreML benchmarking, use Python 3.12 environment"
        fi
    elif [ -d ".env_worker" ]; then
        source ".env_worker/bin/activate"
        print_check 0 "Virtual environment activated (.env_worker)"
    elif [ -d ".env" ]; then
        source ".env/bin/activate"
        print_check 0 "Virtual environment activated (.env)"
    else
        print_warning "Virtual environment not found"
        print_info "Create one with: /opt/homebrew/bin/python3.12 -m venv .venv-worker"
        print_info "Then install: .venv-worker/bin/pip install -r requirements-worker.txt"
    fi
else
    print_info "Virtual environment not activated (--no-venv flag)"
fi

# Step 3: Verify dependencies
echo ""
echo "${BLUE}[3/6] Verifying Dependencies${NC}"

MISSING_DEPS=0

# Check core packages
for package in psutil numpy pandas onnxruntime redis flask requests; do
    if python3 -c "import ${package}" 2>/dev/null; then
        print_check 0 "$package"
    else
        print_error "$package (missing: pip install $package)"
        MISSING_DEPS=1
    fi
done

if [ $MISSING_DEPS -eq 1 ]; then
    print_error "Missing dependencies. Install with: pip install -r requirements.txt"
    exit 1
fi

# Step 4: Detect platform
echo ""
echo "${BLUE}[4/6] Detecting Platform${NC}"

OS=$(uname -s)
case "$OS" in
    Darwin)
        OS_NAME="macOS"
        if python3 -c "import coremltools" 2>/dev/null; then
            print_check 0 "Platform: $OS_NAME (CoreML available)"
        else
            print_warning "Platform: $OS_NAME (CoreML not installed)"
        fi
        ;;
    Linux)
        print_check 0 "Platform: Linux"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        OS_NAME="Windows"
        print_check 0 "Platform: $OS_NAME"
        ;;
    *)
        print_warning "Unknown platform: $OS"
        ;;
esac

# Step 5: Test connectivity
echo ""
echo "${BLUE}[5/6] Testing Connectivity${NC}"

# Test orchestrator
echo "Testing orchestrator: $ORCHESTRATOR_URL"
if python3 << 'EOF' 2>/dev/null; then
    import sys
    import requests
    sys.exit(0)
else
    print_error "Requests library not available"
    exit 1
fi

if python3 << EOF 2>/dev/null; then
    import requests
    import sys
    try:
        response = requests.get("$ORCHESTRATOR_URL/api/health", timeout=2)
        if response.status_code == 200:
            sys.exit(0)
        else:
            sys.exit(1)
    except:
        sys.exit(1)
EOF
then
    print_check 0 "Orchestrator reachable"
else
    print_warning "Orchestrator not reachable (will retry at startup)"
fi

# Step 6: Start worker
echo ""
echo "${BLUE}[6/6] Starting Worker Agent${NC}"

print_info "Configuration:"
print_info "  Orchestrator: $ORCHESTRATOR_URL"
print_info "  Redis Host: $REDIS_HOST:$REDIS_PORT"

if [ $DEBUG_MODE -eq 1 ]; then
    print_info "  Debug: Enabled"
    DEBUG_FLAG="--debug"
else
    DEBUG_FLAG=""
fi

echo ""
echo "${GREEN}Starting worker...${NC}"
echo ""

# Start the worker
cd "$SCRIPT_DIR"

python3 worker/worker_agent.py \
    --orchestrator-url "$ORCHESTRATOR_URL" \
    --redis-host "$REDIS_HOST" \
    --redis-port "$REDIS_PORT" \
    $DEBUG_FLAG

# If we get here, the worker exited
echo ""
echo "${YELLOW}Worker stopped${NC}"

