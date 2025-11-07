# Dumont

Distributed ML inference worker for the CycleOPS orchestration system.

## Quick Start

### Option 1: pip install (Recommended)

```bash
# Install directly from GitHub
pip install git+https://github.com/exitflynn/dumont.git

# Or with platform-specific features
pip install "dumont[macos] @ git+https://github.com/exitflynn/dumont.git"  # macOS with CoreML
pip install "dumont[windows] @ git+https://github.com/exitflynn/dumont.git"  # Windows with DirectML
```

Then run:
```bash
dumont info
dumont start --host http://<orchestrator-ip>:5000
```

### Option 2: Standalone Binary (No Python Required)

For users who prefer a single executable without Python installation:

```bash
curl -fsSL https://github.com/exitflynn/dumont/raw/refs/heads/main/init_dumont.sh | bash
```

This will build and install a platform-specific binary to `~/bin/dumont`.

## System Requirements

- Python 3.8+ (not required for standalone binary)
- macOS 10.15+, Windows 10+, or Linux
- 4GB RAM minimum (8GB recommended)
- Network access to orchestrator and Redis

## Usage

```bash
# Check system info
dumont info

# Validate setup
dumont validate

# Test connectivity
dumont test --host http://192.168.1.100:5000

# Enroll worker
dumont enroll --host http://192.168.1.100:5000

# Start worker
dumont start --host http://192.168.1.100:5000 \
              --redis-host 192.168.1.100 \
              --redis-port 6379
```

## Development

### From Source

```bash
git clone https://github.com/exitflynn/dumont.git
cd dumont
pip install -e ".[dev]"
```

### Build Binary

```bash
# Install build dependencies
pip install -e ".[build]"

# Build for your platform
./build.sh              # Auto-detect platform
# or
./build-macos.sh       # macOS
./build-linux.sh       # Linux
build.bat              # Windows
```

Binary will be in `dist_binary/dumont` (or `dumont.exe` on Windows)

## License

MIT

## Support

For issues: [GitHub Issues](https://github.com/exitflynn/dumont/issues)
````
