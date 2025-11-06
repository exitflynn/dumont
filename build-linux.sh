#!/bin/bash
# Build CycleOPS Worker Binary for Linux (ONNX support)

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║      CycleOPS Worker - Linux Binary Build (ONNX Only)         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 not found"
    exit 1
fi

echo "✓ Python $(python3 --version | awk '{print $2}')"

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

# Build binary
echo ""
echo "▶ Building binary with PyInstaller..."
pyinstaller --clean cyclops-worker-linux.spec

if [ -f "dist/cyclops-worker" ]; then
    echo "  ✓ Binary created successfully"
else
    echo "  ✗ Binary creation failed"
    exit 1
fi

# Create distribution package
echo ""
echo "▶ Creating distribution package..."

mkdir -p dist_binary
cp dist/cyclops-worker dist_binary/
chmod +x dist_binary/cyclops-worker

# Get binary size
SIZE=$(du -h dist_binary/cyclops-worker | awk '{print $1}')
echo "  ✓ Binary size: $SIZE"

# Test binary
echo ""
echo "▶ Testing binary..."
if ./dist_binary/cyclops-worker --help > /dev/null 2>&1; then
    echo "  ✓ Binary is functional"
else
    echo "  ⚠ Warning: Binary test failed"
fi

# Create README for distribution
cat > dist_binary/README.txt << 'EOF'
CycleOPS Worker - Linux Binary (ONNX Support)
==============================================

This is a standalone executable for Linux with ONNX Runtime support.

Quick Start:
-----------

1. Check system info:
   ./cyclops-worker info

2. Validate requirements:
   ./cyclops-worker validate

3. Test connectivity:
   ./cyclops-worker test --orchestrator-url http://192.168.1.100:5000

4. Enroll worker:
   ./cyclops-worker enroll --orchestrator-url http://192.168.1.100:5000

5. Start worker:
   ./cyclops-worker start --orchestrator-url http://192.168.1.100:5000

For help:
   ./cyclops-worker --help

System Requirements:
-------------------
- No Python required!
- Linux (most distributions)
- Network access to orchestrator
- 100MB disk space
- Optional: CUDA for GPU acceleration

Model Support:
-------------
- ✓ ONNX models (CPU/GPU)
- ✗ CoreML (macOS only)

Distribution:
------------
Just copy the 'cyclops-worker' file to any Linux machine and run it.
No installation needed!
EOF

echo "  ✓ Created distribution README"

# Create deployment package
echo ""
echo "▶ Creating deployment archive..."

PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
ARCHIVE_NAME="cyclops-worker-${PLATFORM}-${ARCH}.tar.gz"

cd dist_binary
tar czf "../${ARCHIVE_NAME}" cyclops-worker README.txt
cd ..

echo "  ✓ Created ${ARCHIVE_NAME}"

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    Build Successful! ✓                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Binary:   dist_binary/cyclops-worker (${SIZE})"
echo "Archive:  ${ARCHIVE_NAME}"
echo ""
echo "To test locally:"
echo "  ./dist_binary/cyclops-worker info"
echo ""
echo "To distribute:"
echo "  Just copy 'cyclops-worker' to target machines - no Python needed!"
echo ""
echo "To deploy to remote machine:"
echo "  scp dist_binary/cyclops-worker user@remote:~/"
echo "  ssh user@remote './cyclops-worker start --orchestrator-url http://IP:5000'"
echo ""
