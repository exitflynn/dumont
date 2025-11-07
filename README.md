# Dumont

Distributed benchmarking worker agent for the CycleOPS orchestration system.

## Quick Start

### Installation

```bash
curl -fsSL https://raw.githubusercontent.com/exitflynn/dumont/main/init_dumont.sh | bash
```

This will:
1. Clone the repository
2. Create a Python virtual environment
3. Install all dependencies
4. Set up the worker

### Running the Worker

```bash
source activate_worker.sh
cyclops-worker start --orchestrator-url http://<orchestrator-ip>:5000
```

## System Requirements

- Python 3.8 or higher
- macOS 10.15+, Windows 10+, or Linux
- 4GB RAM minimum (8GB recommended)
- Network access to orchestrator and Redis

## Configuration

```bash
cyclops-worker start \
  --orchestrator-url http://192.168.1.100:5000 \
  --redis-host 192.168.1.100 \
  --redis-port 6379
```

## Common Commands

```bash
# Check system info
cyclops-worker info

# Validate setup
cyclops-worker validate

# Test connectivity
cyclops-worker test --orchestrator-url http://192.168.1.100:5000

# Enroll worker
cyclops-worker enroll --orchestrator-url http://192.168.1.100:5000
```
