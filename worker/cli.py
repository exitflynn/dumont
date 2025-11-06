"""
CycleOPS Worker - Command Line Interface
Main entry point for worker commands.
"""

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
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def cmd_start(args):
    """Start the worker agent."""
    from worker.worker_agent import WorkerAgent
    from urllib.parse import urlparse
    
    setup_logging(args.verbose)
    
    # Validate orchestrator URL
    if not args.orchestrator_url:
        print("❌ Error: --orchestrator-url is required")
        print("Example: cyclops-worker start --orchestrator-url http://192.168.1.100:5000")
        sys.exit(1)
    
    # Auto-detect Redis host from orchestrator URL if not explicitly set
    redis_host = args.redis_host
    if args.redis_host == 'localhost' and not args.orchestrator_url.startswith('http://localhost') and not args.orchestrator_url.startswith('http://127.0.0.1'):
        # Extract host from orchestrator URL
        parsed = urlparse(args.orchestrator_url)
        if parsed.hostname:
            redis_host = parsed.hostname
            print(f"ℹ️  Auto-detected Redis host from orchestrator: {redis_host}")
    
    # Create and start worker
    print(f"🚀 Starting CycleOPS Worker")
    print(f"   Orchestrator: {args.orchestrator_url}")
    print(f"   Redis: {redis_host}:{args.redis_port}")
    print()
    
    worker = WorkerAgent(
        orchestrator_url=args.orchestrator_url,
        redis_host=redis_host,
        redis_port=args.redis_port
    )
    
    # Register with orchestrator
    if not worker.register_with_orchestrator():
        print("❌ Failed to register with orchestrator")
        sys.exit(1)
    
    # Start job loop
    try:
        worker.start_job_loop()
    except KeyboardInterrupt:
        print("\n⏸️  Shutting down worker...")
        worker.stop_continuous_heartbeat()
        print("✅ Worker stopped")


def cmd_enroll(args):
    """Enroll this machine as a worker."""
    from enroll_worker import WorkerEnroller
    from urllib.parse import urlparse
    
    setup_logging(args.verbose)
    
    # Validate orchestrator URL
    if not args.orchestrator_url:
        print("❌ Error: --orchestrator-url is required")
        print("Example: cyclops-worker enroll --orchestrator-url http://192.168.1.100:5000")
        sys.exit(1)
    
    # Auto-detect Redis host from orchestrator URL if not explicitly set
    redis_host = args.redis_host
    if args.redis_host == 'localhost' and not args.orchestrator_url.startswith('http://localhost') and not args.orchestrator_url.startswith('http://127.0.0.1'):
        parsed = urlparse(args.orchestrator_url)
        if parsed.hostname:
            redis_host = parsed.hostname
            print(f"ℹ️  Auto-detected Redis host from orchestrator: {redis_host}")
    
    enroller = WorkerEnroller(
        orchestrator_url=args.orchestrator_url,
        redis_host=redis_host,
        redis_port=args.redis_port,
    )
    
    success = enroller.run_enrollment()
    sys.exit(0 if success else 1)


def cmd_info(args):
    """Display system information and capabilities."""
    import platform
    import json
    
    setup_logging(args.verbose)
    
    try:
        # Add project root to path
        sys.path.insert(0, str(Path.cwd()))
        from worker.legacy.device_info import get_device_info, get_compute_units
        
        print("🖥️  CycleOPS Worker - System Information")
        print("=" * 70)
        
        # Platform info
        print(f"\n📋 Platform:")
        print(f"   System:      {platform.system()}")
        print(f"   Release:     {platform.release()}")
        print(f"   Machine:     {platform.machine()}")
        print(f"   Python:      {platform.python_version()}")
        
        # Device info
        device_info = get_device_info()
        print(f"\n💻 Device:")
        print(f"   Name:        {device_info.get('DeviceName', 'N/A')}")
        print(f"   CPU/SoC:     {device_info.get('Soc', 'N/A')[:60]}")
        print(f"   RAM:         {device_info.get('Ram', 0)} GB")
        print(f"   OS:          {device_info.get('DeviceOs', 'N/A')}")
        print(f"   OS Version:  {device_info.get('DeviceOsVersion', 'N/A')}")
        
        # Capabilities
        capabilities = get_compute_units()
        print(f"\n⚡ Compute Capabilities:")
        for cap in capabilities:
            print(f"   ✓ {cap}")
        
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
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_validate(args):
    """Validate worker installation and dependencies."""
    import importlib
    
    setup_logging(args.verbose)
    
    print("🔍 CycleOPS Worker - Validation")
    print("=" * 70)
    
    # Check Python version
    version = sys.version_info
    print(f"\n✓ Python {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 8):
        print("  ❌ Python 3.8+ required")
        sys.exit(1)
    
    # Check dependencies
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
    
    print("\n📦 Required Dependencies:")
    all_ok = True
    for module, desc in required.items():
        try:
            mod = importlib.import_module(module)
            version = getattr(mod, '__version__', 'unknown')
            print(f"   ✓ {module:20} {version:15} ({desc})")
        except ImportError:
            print(f"   ❌ {module:20} {'MISSING':15} ({desc})")
            all_ok = False
    
    print("\n📦 Optional Dependencies:")
    for module, desc in optional.items():
        try:
            mod = importlib.import_module(module)
            version = getattr(mod, '__version__', 'unknown')
            print(f"   ✓ {module:20} {version:15} ({desc})")
        except ImportError:
            print(f"   ⚠️  {module:20} {'not installed':15} ({desc})")
    
    if all_ok:
        print("\n✅ All required dependencies installed!")
    else:
        print("\n❌ Some dependencies missing. Run:")
        print("   pip install -r requirements-worker.txt")
        sys.exit(1)


def cmd_test(args):
    """Test connectivity to orchestrator and Redis."""
    import socket
    from urllib.parse import urlparse
    
    setup_logging(args.verbose)
    
    print("🔌 CycleOPS Worker - Connectivity Test")
    print("=" * 70)
    
    # Auto-detect Redis host from orchestrator URL if not explicitly set
    redis_host = args.redis_host
    if args.redis_host == 'localhost' and not args.orchestrator_url.startswith('http://localhost') and not args.orchestrator_url.startswith('http://127.0.0.1'):
        parsed = urlparse(args.orchestrator_url)
        if parsed.hostname:
            redis_host = parsed.hostname
            print(f"ℹ️  Auto-detected Redis host from orchestrator: {redis_host}\n")
    
    # Get local info
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        print(f"\n🖥️  Local Machine:")
        print(f"   Hostname: {hostname}")
        print(f"   IP:       {ip}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test orchestrator
    print(f"\n🎯 Orchestrator ({args.orchestrator_url}):")
    try:
        import requests
        response = requests.get(f"{args.orchestrator_url}/api/health", timeout=5)
        if response.status_code == 200:
            print(f"   ✓ Reachable (HTTP {response.status_code})")
        else:
            print(f"   ⚠️  Responded with HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect")
        print(f"      Make sure orchestrator is running at {args.orchestrator_url}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test Redis
    print(f"\n📮 Redis ({redis_host}:{args.redis_port}):")
    try:
        import redis
        r = redis.Redis(host=redis_host, port=args.redis_port, socket_connect_timeout=2)
        r.ping()
        print(f"   ✓ Reachable")
    except Exception as e:
        print(f"   ❌ Cannot connect: {e}")
    
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='cyclops-worker',
        description='CycleOPS Distributed Benchmarking Worker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  start      Start the worker agent
  enroll     Register this machine with the orchestrator
  info       Display system information and capabilities
  validate   Check installation and dependencies
  test       Test connectivity to orchestrator and Redis

Examples:
  # Start worker
  cyclops-worker start --orchestrator-url http://192.168.1.100:5000

  # Enroll worker
  cyclops-worker enroll --orchestrator-url http://192.168.1.100:5000

  # Check system info
  cyclops-worker info

  # Validate installation
  cyclops-worker validate
        """
    )
    
    # Global arguments
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Start command
    parser_start = subparsers.add_parser('start', help='Start worker agent')
    parser_start.add_argument('--orchestrator-url', required=True, help='Orchestrator URL')
    parser_start.add_argument('--redis-host', default='localhost', help='Redis host (default: auto-detect from orchestrator URL)')
    parser_start.add_argument('--redis-port', type=int, default=6379, help='Redis port (default: 6379)')
    parser_start.set_defaults(func=cmd_start)
    
    # Enroll command
    parser_enroll = subparsers.add_parser('enroll', help='Enroll worker')
    parser_enroll.add_argument('--orchestrator-url', required=True, help='Orchestrator URL')
    parser_enroll.add_argument('--redis-host', default='localhost', help='Redis host (default: auto-detect from orchestrator URL)')
    parser_enroll.add_argument('--redis-port', type=int, default=6379, help='Redis port (default: 6379)')
    parser_enroll.set_defaults(func=cmd_enroll)
    
    # Info command
    parser_info = subparsers.add_parser('info', help='Display system info')
    parser_info.add_argument('--json', action='store_true', help='Output as JSON')
    parser_info.set_defaults(func=cmd_info)
    
    # Validate command
    parser_validate = subparsers.add_parser('validate', help='Validate installation')
    parser_validate.set_defaults(func=cmd_validate)
    
    # Test command
    parser_test = subparsers.add_parser('test', help='Test connectivity')
    parser_test.add_argument('--orchestrator-url', required=True, help='Orchestrator URL')
    parser_test.add_argument('--redis-host', default='localhost', help='Redis host (default: auto-detect from orchestrator URL)')
    parser_test.add_argument('--redis-port', type=int, default=6379, help='Redis port (default: 6379)')
    parser_test.set_defaults(func=cmd_test)
    
    # Parse args
    args = parser.parse_args()
    
    # Show help if no command
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Run command
    args.func(args)


if __name__ == '__main__':
    main()
