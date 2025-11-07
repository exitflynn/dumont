#!/bin/bash
# Build Dumont Binary for macOS with CoreML Support
# This version uses a different approach to handle CoreML native bindings

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo " ║      Dumont - macOS Binary Build (with CoreML)               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 not found"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✓ Python $PYTHON_VERSION"

# Check macOS version
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "✗ This script is for macOS only"
    echo "  Use build-linux.sh for Linux"
    exit 1
fi

echo "✓ macOS detected"

# Create build environment
echo ""
echo "▶ Setting up build environment..."

if [ ! -d ".venv_build" ]; then
    python3 -m venv .venv_build
    echo "  ✓ Created build environment"
fi

source .venv_build/bin/activate
echo "  ✓ Activated build environment"

# Install dependencies
echo ""
echo "▶ Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements-worker.txt
pip install -q -r requirements-build.txt
echo "  ✓ Dependencies installed"

# Ensure hooks directory exists
mkdir -p hooks
echo "  ✓ Hooks directory ready"

# Build binary using macOS-specific spec
echo ""
echo "▶ Building macOS binary with PyInstaller..."
echo "  ⚠️  NOTE: CoreML native bindings may not work in binary."
echo "  Consider using Python package distribution for macOS instead."
echo ""

pyinstaller --clean dumont-macos.spec

if [ -f "dist/dumont" ]; then
    echo "  ✓ Binary created successfully"
else
    echo "  ✗ Binary creation failed"
    exit 1
fi

# Create distribution package
echo ""
echo "▶ Creating distribution package..."

mkdir -p dist_binary
cp dist/dumont dist_binary/
chmod +x dist_binary/dumont

# Get binary size
SIZE=$(du -h dist_binary/dumont | awk '{print $1}')
echo "  ✓ Binary size: $SIZE"

# Test binary (basic check)
echo ""
echo "▶ Testing binary..."
if ./dist_binary/dumont --help > /dev/null 2>&1; then
    echo "  ✓ Binary is functional"
else
    echo "  ⚠ Warning: Binary test failed"
fi

# Create README for distribution
cat > dist_binary/README-MACOS.txt << 'EOF'
Dumont - macOS Binary
===============================

⚠️  IMPORTANT NOTE ABOUT COREML:
   
   This binary may NOT support CoreML due to native library limitations.
   
   For full CoreML support on macOS, we recommend:
   1. Use the Python package distribution (install.sh)
   2. Or run the worker directly with: python start_worker.py

ONNX models will work fine in this binary.

Quick Start (ONNX only):
-----------

1. Check system info:
   ./dumont info

2. Start worker:
   ./dumont start --orchestrator-url http://192.168.1.100:5000

System Requirements:
-------------------
- macOS 10.15+
- Network access to orchestrator
- 100MB disk space

For CoreML Support:
------------------
Use Python installation instead:
   ./install.sh
   source activate_worker.sh
   dumont start --orchestrator-url http://IP:5000
EOF

echo "  ✓ Created distribution README"

# Create deployment package
echo ""
echo "▶ Creating deployment archive..."

PLATFORM="darwin"
ARCH=$(uname -m)
ARCHIVE_NAME="dumont-${PLATFORM}-${ARCH}-onnx.tar.gz"

cd dist_binary
tar czf "../${ARCHIVE_NAME}" dumont README-MACOS.txt
cd ..

echo "  ✓ Created ${ARCHIVE_NAME}"

# Warning message
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║               Binary Build Complete (ONNX Only)                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  IMPORTANT:"
echo "   This binary supports ONNX models but NOT CoreML (native binding issues)"
echo ""
echo "Binary:   dist_binary/dumont (${SIZE})"
echo "Archive:  ${ARCHIVE_NAME}"
echo ""
echo "For ONNX benchmarking:"
echo "  ./dist_binary/dumont start --orchestrator-url http://IP:5000"
echo ""
echo "For FULL CoreML support, use Python package instead:"
echo "  ./install.sh"
echo "  source activate_worker.sh"
echo "  dumont start --orchestrator-url http://IP:5000"
echo ""
