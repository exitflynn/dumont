# Dumont - Distributed ML Worker 🧍🥏

Worker node for [SARK](https://github.com/exitflynn/sark). Executes benchmarking jobs on local hardware and reports metrics (speed, RAM, CPU, GPU utilization).

---

## Command Line Interface
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

**Options**:
```bash
--redis-host localhost      # Redis server
--redis-port 6379          # Redis port
--device-name MyDevice     # Override device name
--log-level DEBUG          # Logging level
```

### The Flow

1. **Start**: Worker registers with orchestrator via `/api/register`
2. **Poll**: Worker polls Redis for jobs matching its capabilities
3. **Execute**: Worker downloads model → loads → runs benchmarks
4. **Report**: Worker pushes results to Redis `results` queue
5. **Heartbeat**: Worker sends periodic heartbeats via `/api/workers/{id}/heartbeat`

### Supported Inference Engines

- **ONNX** (.onnx) - CPU, GPU (CUDA, DirectML)
- **CoreML** (.mlmodel) - GPU, Neural Engine (Apple Silicon)
- (made to be extensible!)

### Metrics Collected

**Model Loading**:
- Time: Min, Max, Average, Median, StdDev (ms)
- RAM: Peak usage during load (MB)

**Inference** (N runs, default 10):
- Time: Min, Max, Average, Median, StdDev (ms)
- RAM: Peak usage during inference (MB)
- CPU: Utilization percentage
- GPU: Utilization and VRAM (when available)

**Device Info**:
- Device name and model
- CPU/SOC details
- RAM total
- GPU/Neural Engine availability
- OS and version

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


### Check Capabilities

```bash
dumont info
```

Lists available compute units for this device.

**Output**:
```
Available Compute Units:
- CPU (ONNX)
- GPU (CoreML)
- Neural Engine (CoreML)
```

**Output**:
```json
{
  "LoadMsMedian": 45.23,
  "LoadMsAverage": 45.5,
  "LoadMsStdDev": 0.8,
  "PeakLoadRamUsage": 256.5,
  "InferenceMsMedian": 12.50,
  "InferenceMsAverage": 12.52,
  "InferenceMsStdDev": 0.15,
  "PeakInferenceRamUsage": 512.0
}
```

When worker starts, it automatically:
1. Detects local device capabilities
2. Gathers device info (CPU, RAM, GPU, OS)
3. Registers with orchestrator via `POST /api/register`
4. Starts polling Redis for jobs

### Status Updates

Worker updates its status via `PUT /api/workers/{id}/status`:
- **active** - Idle, waiting for jobs
- **busy** - Executing a job
- **cleanup** - Cleaning up after job
- **faulty** - Error detected, not accepting jobs

### Heartbeat Monitoring

During job execution, worker sends heartbeats every 10 seconds via `POST /api/workers/{id}/heartbeat`.

---

## Performance Optimization

### Batch Processing
For multiple models, reuse model loader:
```python
loader = ModelLoader(compute_unit="GPU (CoreML)")

for model_path in model_list:
    loader.load_model(model_path)
    metrics = benchmark.run_full_benchmark(loader, model_path)
    loader.cleanup()
```

### Compute Unit Selection
Choose compute unit based on model type:
- **CPU (ONNX)**: Always available, fallback
- **GPU (ONNX)**: NVIDIA/AMD GPUs with CUDA/ROCm
- **GPU (CoreML)**: Metal GPU on macOS
- **Neural Engine (CoreML)**: Apple Neural Engine on Silicon