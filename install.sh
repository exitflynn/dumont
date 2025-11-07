#!/bin/bash
# Dumont - Installation Script for macOS/Linux
# This script sets up a clean Python environment and installs the worker

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
VENV_NAME=".venv_worker"
PYTHON_MIN_VERSION="3.8"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN} ║                    Dumont - Installation Script             ║${NC}"
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}▶ $1${NC}"
    echo -e "${BLUE}$(printf '─%.0s' {1..70})${NC}"
}

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check Python version
print_section "Checking Python Installation"

if ! command_exists python3; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    echo "  Please install Python 3.8 or higher from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Verify Python version meets minimum requirement
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}✗ Python 3.8+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi

# Step 2: Create virtual environment
print_section "Creating Virtual Environment"

if [ -d "$VENV_NAME" ]; then
    echo -e "${YELLOW}⚠ Virtual environment already exists at $VENV_NAME${NC}"
    read -p "Remove and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_NAME"
        echo -e "${GREEN}✓ Removed old environment${NC}"
    else
        echo -e "${YELLOW}Using existing environment${NC}"
    fi
fi

if [ ! -d "$VENV_NAME" ]; then
    python3 -m venv "$VENV_NAME"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source "$VENV_NAME/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Step 3: Upgrade pip
print_section "Upgrading pip"
pip install --quiet --upgrade pip setuptools wheel
echo -e "${GREEN}✓ pip upgraded${NC}"

# Step 4: Install worker package
print_section "Installing Dumont Package"

# Detect platform and install appropriate extras
PLATFORM=$(uname -s)
if [ "$PLATFORM" = "Darwin" ]; then
    echo -e "${CYAN}ℹ macOS detected - installing with CoreML support${NC}"
    pip install -e ".[macos]"
else
    echo -e "${CYAN}ℹ Linux detected - installing CPU version${NC}"
    pip install -e .
fi

echo -e "${GREEN}✓ Worker package installed${NC}"

# Step 5: Verify installation
print_section "Verifying Installation"

if command_exists cyclops-worker; then
    echo -e "${GREEN}✓ cyclops-worker command available${NC}"
else
    echo -e "${RED}✗ cyclops-worker command not found${NC}"
    exit 1
fi

# Run validation
cyclops-worker validate

# Step 6: Create activation script
print_section "Creating Activation Helper"

cat > activate_worker.sh << 'EOF'
#!/bin/bash
# Activate Dumont environment
source .venv_worker/bin/activate
echo "✓ Dumont environment activated"
echo ""
echo "Available commands:"
echo "  cyclops-worker start --orchestrator-url <url>"
echo "  cyclops-worker enroll --orchestrator-url <url>"
echo "  cyclops-worker info"
echo "  cyclops-worker validate"
echo ""
EOF

chmod +x activate_worker.sh
echo -e "${GREEN}✓ Created activation script: ${CYAN}./activate_worker.sh${NC}"

# Success message
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                 Installation Successful! ✓                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Quick Start:${NC}"
echo ""
echo -e "  ${YELLOW}1. Activate the environment:${NC}"
echo -e "     ${CYAN}source activate_worker.sh${NC}"
echo ""
echo -e "  ${YELLOW}2. Check system info:${NC}"
echo -e "     ${CYAN}cyclops-worker info${NC}"
echo ""
echo -e "  ${YELLOW}3. Enroll with orchestrator:${NC}"
echo -e "     ${CYAN}cyclops-worker enroll --orchestrator-url http://<ip>:5000${NC}"
echo ""
echo -e "  ${YELLOW}4. Start the worker:${NC}"
echo -e "     ${CYAN}cyclops-worker start --orchestrator-url http://<ip>:5000${NC}"
echo ""
echo -e "${CYAN}For help:${NC}"
echo -e "  ${CYAN}cyclops-worker --help${NC}"
echo ""
