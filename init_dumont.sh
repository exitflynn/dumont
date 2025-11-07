#!/bin/bash
# Universal CycleOPS Worker Installer
# Downloads, builds, and installs the worker binary for any platform

set -e

REPO_URL="https://github.com/exitflynn/sark.git"
INSTALL_DIR="$HOME/dumont"
BRANCH="main"

print_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║           CycleOPS Worker - Universal Installer               ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
}

print_step() {
    echo ""
    echo "▶ $1"
}

print_success() {
    echo "  ✓ $1"
}

print_error() {
    echo "  ✗ $1"
}

detect_os() {
    print_step "Detecting operating system..."
    
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    
    case "$OS" in
        linux*)
            OS_TYPE="linux"
            BUILD_SCRIPT="build-linux.sh"
            ;;
        darwin*)
            OS_TYPE="macos"
            BUILD_SCRIPT="build-macos.sh"
            ;;
        mingw*|msys*|cygwin*)
            OS_TYPE="windows"
            BUILD_SCRIPT="build.bat"
            ;;
        *)
            print_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    
    print_success "Detected: $OS_TYPE ($ARCH)"
}

check_dependencies() {
    print_step "Checking dependencies..."
    
    # Check git
    if ! command -v git &> /dev/null; then
        print_error "git not found. Please install git first."
        exit 1
    fi
    print_success "git installed"
    
    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        print_error "python3 not found. Please install Python 3.8+ first."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_success "python3 $PYTHON_VERSION installed"
    
    # Check pip
    if ! python3 -m pip --version &> /dev/null; then
        print_error "pip not found. Please install pip first."
        exit 1
    fi
    print_success "pip installed"
}

clone_repo() {
    print_step "Setting up installation directory..."
    
    if [ -d "$INSTALL_DIR" ]; then
        echo "  Installation directory already exists at $INSTALL_DIR"
        read -p "  Remove and reinstall? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
            print_success "Removed existing installation"
        else
            echo "  Using existing directory"
            cd "$INSTALL_DIR/dumont"
            git pull origin $BRANCH
            print_success "Updated from git"
            return
        fi
    fi
    
    print_step "Cloning repository..."
    git clone --depth 1 --branch $BRANCH $REPO_URL "$INSTALL_DIR"
    print_success "Repository cloned to $INSTALL_DIR"
    
    cd "$INSTALL_DIR/dumont"
}

install_python_deps() {
    print_step "Installing Python dependencies..."
    
    # Create virtual environment
    if [ ! -d ".venv_build" ]; then
        python3 -m venv .venv_build
        print_success "Created build environment"
    fi
    
    # Activate virtual environment
    if [ "$OS_TYPE" = "windows" ]; then
        source .venv_build/Scripts/activate
    else
        source .venv_build/bin/activate
    fi
    print_success "Activated build environment"
    
    # Install requirements
    pip install -q --upgrade pip
    pip install -q -r requirements-worker.txt
    pip install -q -r requirements-build.txt
    print_success "Dependencies installed"
}

build_binary() {
    print_step "Building binary for $OS_TYPE..."
    
    if [ "$OS_TYPE" = "windows" ]; then
        cmd //c "$BUILD_SCRIPT"
    else
        bash "$BUILD_SCRIPT"
    fi
    
    print_success "Binary built successfully"
}

install_binary() {
    print_step "Installing binary..."
    
    # Find the built binary
    if [ "$OS_TYPE" = "windows" ]; then
        BINARY_PATH="dist_binary/dumont.exe"
        INSTALL_PATH="$HOME/bin/dumont.exe"
    else
        BINARY_PATH="dist_binary/dumont"
        INSTALL_PATH="$HOME/bin/dumont"
    fi
    
    if [ ! -f "$BINARY_PATH" ]; then
        print_error "Binary not found at $BINARY_PATH"
        exit 1
    fi
    
    # Create ~/bin if it doesn't exist
    mkdir -p "$HOME/bin"
    
    # Copy binary
    cp "$BINARY_PATH" "$INSTALL_PATH"
    chmod +x "$INSTALL_PATH"
    
    print_success "Binary installed to $INSTALL_PATH"
}

add_to_path() {
    print_step "Configuring PATH..."
    
    SHELL_RC=""
    case "$SHELL" in
        */bash)
            SHELL_RC="$HOME/.bashrc"
            ;;
        */zsh)
            SHELL_RC="$HOME/.zshrc"
            ;;
        */fish)
            SHELL_RC="$HOME/.config/fish/config.fish"
            ;;
    esac
    
    if [ -n "$SHELL_RC" ]; then
        if ! grep -q '$HOME/bin' "$SHELL_RC" 2>/dev/null; then
            echo 'export PATH="$HOME/bin:$PATH"' >> "$SHELL_RC"
            print_success "Added ~/bin to PATH in $SHELL_RC"
            echo "  Run: source $SHELL_RC"
        else
            print_success "PATH already configured"
        fi
    fi
}

print_next_steps() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                  Installation Complete! ✓                     ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Binary installed at: $HOME/bin/dumont"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Reload your shell or run:"
    if [ -n "$SHELL_RC" ]; then
        echo "   source $SHELL_RC"
    else
        echo "   export PATH=\"\$HOME/bin:\$PATH\""
    fi
    echo ""
    echo "2. Check system info:"
    echo "   dumont info"
    echo ""
    echo "3. Validate setup:"
    echo "   dumont validate"
    echo ""
    echo "4. Enroll with orchestrator:"
    echo "   dumont enroll --orchestrator-url http://ORCHESTRATOR_IP:5000"
    echo ""
    echo "5. Start the worker:"
    echo "   dumont start --orchestrator-url http://ORCHESTRATOR_IP:5000"
    echo ""
    echo "For help:"
    echo "   dumont --help"
    echo ""
}

main() {
    print_header
    detect_os
    check_dependencies
    clone_repo
    install_python_deps
    build_binary
    install_binary
    add_to_path
    print_next_steps
}

main
