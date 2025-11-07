#!/bin/bash
# Dumont - Platform-Aware Build Script
# Automatically detects platform and calls appropriate build script

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo " ║                 Dumont - Platform Detection                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

PLATFORM=$(uname -s)

case "$PLATFORM" in
    Darwin)
        echo "✓ Platform: macOS"
        echo ""
        echo "⚠️  Note: macOS binary will support ONNX only."
        echo "   For CoreML support, use: ./install.sh (Python package)"
        echo ""
        read -p "Continue with ONNX-only binary build? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            exec ./build-macos.sh
        else
            echo "Build cancelled."
            echo "For full CoreML support: ./install.sh"
            exit 0
        fi
        ;;
    
    Linux)
        echo "✓ Platform: Linux"
        echo "   Building ONNX binary with CPU/GPU support..."
        echo ""
        exec ./build-linux.sh
        ;;
    
    *)
        echo "✗ Unsupported platform: $PLATFORM"
        echo "  Supported platforms: macOS, Linux"
        echo "  For Windows, use: build.bat"
        exit 1
        ;;
esac
