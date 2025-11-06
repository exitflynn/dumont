#!/bin/bash
# Worker Environment Setup Script
# Creates a reproducible Python 3.12 environment with CoreML support

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}        CycleOPS Worker Environment Setup                     ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n"

# Step 1: Check for Python 3.12
echo -e "${BLUE}[1/5]${NC} Checking for Python 3.12..."

if command -v /opt/homebrew/bin/python3.12 &> /dev/null; then
    echo -e "  ${GREEN}✅${NC} Python 3.12 found"
    PYTHON312=/opt/homebrew/bin/python3.12
elif command -v python3.12 &> /dev/null; then
    echo -e "  ${GREEN}✅${NC} Python 3.12 found"
    PYTHON312=python3.12
else
    echo -e "  ${YELLOW}⚠️${NC} Python 3.12 not found"
    echo -e "  ${BLUE}ℹ️${NC} Installing Python 3.12 via Homebrew..."
    
    if ! command -v brew &> /dev/null; then
        echo -e "  ${RED}❌${NC} Homebrew not found. Please install Homebrew first:"
        echo -e "      /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    brew install python@3.12
    PYTHON312=/opt/homebrew/bin/python3.12
    echo -e "  ${GREEN}✅${NC} Python 3.12 installed"
fi

# Verify version
VERSION=$($PYTHON312 --version)
echo -e "  ${BLUE}ℹ️${NC} Version: $VERSION"

# Step 2: Create virtual environment
echo -e "\n${BLUE}[2/5]${NC} Creating virtual environment..."

if [ -d ".venv-worker" ]; then
    echo -e "  ${YELLOW}⚠️${NC} Virtual environment already exists"
    read -p "  Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .venv-worker
        echo -e "  ${BLUE}ℹ️${NC} Removed existing environment"
    else
        echo -e "  ${BLUE}ℹ️${NC} Using existing environment"
    fi
fi

if [ ! -d ".venv-worker" ]; then
    $PYTHON312 -m venv .venv-worker
    echo -e "  ${GREEN}✅${NC} Virtual environment created"
fi

# Step 3: Upgrade pip
echo -e "\n${BLUE}[3/5]${NC} Upgrading pip..."
.venv-worker/bin/pip install --upgrade pip > /dev/null 2>&1
echo -e "  ${GREEN}✅${NC} pip upgraded"

# Step 4: Install dependencies
echo -e "\n${BLUE}[4/5]${NC} Installing dependencies..."

if [ ! -f "requirements-worker.txt" ]; then
    echo -e "  ${RED}❌${NC} requirements-worker.txt not found"
    exit 1
fi

echo -e "  ${BLUE}ℹ️${NC} Installing packages (this may take a minute)..."
.venv-worker/bin/pip install -r requirements-worker.txt > /tmp/pip_install.log 2>&1

if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✅${NC} All dependencies installed"
else
    echo -e "  ${RED}❌${NC} Installation failed. See /tmp/pip_install.log for details"
    exit 1
fi

# Step 5: Verify setup
echo -e "\n${BLUE}[5/5]${NC} Verifying installation..."

# Check coremltools
if .venv-worker/bin/python -c "import coremltools" 2>/dev/null; then
    echo -e "  ${GREEN}✅${NC} coremltools"
else
    echo -e "  ${RED}❌${NC} coremltools"
    exit 1
fi

# Check for CoreML native bindings
if .venv-worker/bin/python -c "from coremltools import libcoremlpython" 2>/dev/null; then
    echo -e "  ${GREEN}✅${NC} CoreML native bindings (libcoremlpython)"
else
    echo -e "  ${YELLOW}⚠️${NC} CoreML native bindings not available"
    echo -e "      This means ACTUAL CoreML inference won't work"
    echo -e "      Try reinstalling coremltools in this environment"
fi

# Check other packages
for pkg in onnxruntime numpy psutil redis requests PIL; do
    if .venv-worker/bin/python -c "import ${pkg}" 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} $pkg"
    else
        echo -e "  ${YELLOW}⚠️${NC} $pkg (may need troubleshooting)"
    fi
done

# Summary
echo -e "\n${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}                   Setup Complete!                             ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Start the worker:"
echo -e "     ${YELLOW}./start_worker.sh${NC}"
echo -e ""
echo -e "  2. Or activate the environment manually:"
echo -e "     ${YELLOW}source .venv-worker/bin/activate${NC}"
echo -e "     ${YELLOW}python start_worker.py${NC}"
echo -e ""
echo -e "${BLUE}Environment details:${NC}"
echo -e "  Location: ${YELLOW}.venv-worker/${NC}"
echo -e "  Python: ${YELLOW}$($PYTHON312 --version)${NC}"
echo -e "  Requirements: ${YELLOW}requirements-worker.txt${NC}"
echo -e ""

