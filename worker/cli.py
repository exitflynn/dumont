import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add project root to path
import os
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def cmd_start(args):
    from worker.worker_agent import WorkerAgent
    from urllib.parse import urlparse
    
    setup_logging(args.verbose)
    
    if not args.orchestrator_url:
        print("Error: --host is required")
        sys.exit(1)
    
    redis_host = args.redis_host
    if args.redis_host == 'localhost' and not args.orchestrator_url.startswith('http://localhost') and not args.orchestrator_url.startswith('http://127.0.0.1'):
        parsed = urlparse(args.orchestrator_url)
        if parsed.hostname:
            redis_host = parsed.hostname
    
    print(f"Starting Dumont")
    print(f"   Orchestrator: {args.orchestrator_url}")
    print(f"   Redis: {redis_host}:{args.redis_port}")
    
    worker = WorkerAgent(
        orchestrator_url=args.orchestrator_url,
        redis_host=redis_host,
        redis_port=args.redis_port
    )
    
    # Register with orchestrator
    if not worker.register_with_orchestrator():
        print("Failed to register with orchestrator")
        sys.exit(1)
    
    try:
        worker.start_job_loop()
    except KeyboardInterrupt:
        print("\nShutting down...")
        worker.stop_continuous_heartbeat()
        print("Worker stopped")


def cmd_enroll(args):
    from enroll_worker import WorkerEnroller
    from urllib.parse import urlparse
    
    setup_logging(args.verbose)
    
    if not args.orchestrator_url:
        print("Error: --host is required")
        sys.exit(1)
    
    redis_host = args.redis_host
    enroller = WorkerEnroller(
        orchestrator_url=args.orchestrator_url,
        redis_host=redis_host,
        redis_port=args.redis_port,
    )
    
    success = enroller.run_enrollment()
    sys.exit(0 if success else 1)


def cmd_info(args):
    import platform
    import json
    
    setup_logging(args.verbose)
    
    try:
        sys.path.insert(0, str(Path.cwd()))
        from worker.device_info import get_device_info, get_compute_units
        
        print("Dumont - System Information")
        print("=" * 70)
        
        print(f"\nPlatform:")
        print(f"   System:      {platform.system()}")
        print(f"   Release:     {platform.release()}")
        print(f"   Machine:     {platform.machine()}")
        print(f"   Python:      {platform.python_version()}")
        
        device_info = get_device_info()
        print(f"\nDevice:")
        print(f"   Name:        {device_info.get('DeviceName', 'N/A')}")
        print(f"   CPU/SoC:     {str(device_info.get('Soc', 'N/A'))[:60]}")
        print(f"   RAM:         {device_info.get('Ram', 0)} GB")
        print(f"   OS:          {device_info.get('DeviceOs', 'N/A')}")
        print(f"   OS Version:  {device_info.get('DeviceOsVersion', 'N/A')}")
        
        capabilities = get_compute_units()
        print(f"\nCompute Capabilities:")
        for cap in capabilities:
            print(f"   - {cap}")
        
        if args.json:
            output = {
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'machine': platform.machine(),
                    'python': platform.python_version(),
                },
                'device': device_info,
                'capabilities': capabilities,
            }
            print(f"\n{json.dumps(output, indent=2)}")
        
        print()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_validate(args):
    import importlib
    
    setup_logging(args.verbose)
    
    print("Dumont - Validation")
    print("=" * 70)
    
    version = sys.version_info
    print(f"\nPython {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 8):
        print("Python 3.8+ required")
        sys.exit(1)
    
    required = {
        'psutil': 'System monitoring',
        'numpy': 'Numerical computing',
        'requests': 'HTTP client',
        'redis': 'Redis client',
        'onnxruntime': 'ONNX Runtime',
    }
    
    optional = {}
    import platform
    if platform.system() == 'Darwin':
        optional['coremltools'] = 'CoreML (macOS)'
        optional['PIL'] = 'Image processing (CoreML)'
    
    print("\nRequired Dependencies:")
    all_ok = True
    for module, desc in required.items():
        try:
            mod = importlib.import_module(module)
            version = getattr(mod, '__version__', 'unknown')
            print(f"   {module:20} {version:15} ({desc})")
        except ImportError:
            print(f"   {module:20} MISSING ({desc})")
            all_ok = False
    
    print("\nOptional Dependencies:")
    for module, desc in optional.items():
        try:
            mod = importlib.import_module(module)
            version = getattr(mod, '__version__', 'unknown')
            print(f"   {module:20} {version:15} ({desc})")
        except ImportError:
            print(f"   {module:20} not installed ({desc})")
    
    if all_ok:
        print("\nAll required dependencies installed!")
    else:
        print("\nSome dependencies missing. Run:")
        print("   pip install -r requirements-worker.txt")
        sys.exit(1)


def cmd_test(args):
    import socket
    from urllib.parse import urlparse
    
    setup_logging(args.verbose)
    
    print("Dumont - Connectivity Test")
    print("=" * 70)
    
    redis_host = args.redis_host
    if args.redis_host == 'localhost' and not args.orchestrator_url.startswith('http://localhost') and not args.orchestrator_url.startswith('http://127.0.0.1'):
        parsed = urlparse(args.orchestrator_url)
        if parsed.hostname:
            redis_host = parsed.hostname
    
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        print(f"\nLocal Machine:")
        print(f"   Hostname: {hostname}")
        print(f"   IP:       {ip}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print(f"\nOrchestrator ({args.orchestrator_url}):")
    try:
        import requests
        response = requests.get(f"{args.orchestrator_url}/api/health", timeout=5)
        if response.status_code == 200:
            print(f"   Reachable (HTTP {response.status_code})")
        else:
            print(f"   Responded with HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"   Cannot connect")
        print(f"      Make sure orchestrator is running at {args.orchestrator_url}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print(f"\nRedis ({redis_host}:{args.redis_port}):")
    try:
        import redis
        r = redis.Redis(host=redis_host, port=args.redis_port, socket_connect_timeout=2)
        r.ping()
        print(f"   Reachable")
    except Exception as e:
        print(f"   Cannot connect: {e}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        prog='dumont',
        description='Dumont - Distributed ML Inference Benchmark Worker'
    )
    
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    parser_start = subparsers.add_parser('start', help='Start worker agent')
    parser_start.add_argument('--host', required=True, help='Orchestrator URL')
    parser_start.add_argument('--redis-host', default='localhost', help='Redis host')
    parser_start.add_argument('--redis-port', type=int, default=6379, help='Redis port')
    parser_start.set_defaults(func=cmd_start)
    
    parser_enroll = subparsers.add_parser('enroll', help='Enroll worker')
    parser_enroll.add_argument('--host', required=True, help='Orchestrator URL')
    parser_enroll.add_argument('--redis-host', default='localhost', help='Redis host')
    parser_enroll.add_argument('--redis-port', type=int, default=6379, help='Redis port')
    parser_enroll.set_defaults(func=cmd_enroll)
    
    parser_info = subparsers.add_parser('info', help='Display system info')
    parser_info.add_argument('--json', action='store_true', help='Output as JSON')
    parser_info.set_defaults(func=cmd_info)
    
    parser_validate = subparsers.add_parser('validate', help='Validate installation')
    parser_validate.set_defaults(func=cmd_validate)
    
    parser_test = subparsers.add_parser('test', help='Test connectivity')
    parser_test.add_argument('--host', required=True, help='Orchestrator URL')
    parser_test.add_argument('--redis-host', default='localhost', help='Redis host')
    parser_test.add_argument('--redis-port', type=int, default=6379, help='Redis port')
    parser_test.set_defaults(func=cmd_test)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
