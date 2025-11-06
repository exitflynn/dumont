#!/usr/bin/env python3
"""
Wrapper script to properly run the worker agent from any directory.
This ensures Python path is set up correctly for imports.

NOTE: This script expects to run under the lops project's Python venv,
which has all required dependencies including coremltools.
If running standalone, activate the venv first:
  source ../lops/.env/bin/activate
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add parent project (lops) to path for shared modules like core.redis_client
parent_root = os.path.dirname(project_root)
sys.path.insert(0, parent_root)

args = []

orchestrator_url = os.environ.get('ORCHESTRATOR_URL')
if orchestrator_url:
    args.extend(['--orchestrator-url', orchestrator_url])

# Default to Docker Redis port 6380
redis_port = os.environ.get('REDIS_PORT', '6380')
args.extend(['--redis-port', redis_port])

# Extend sys.argv so argparse picks up the defaults
if args:
    sys.argv.extend(args)

# Now import and run the worker
from worker.worker_agent import main

if __name__ == '__main__':
    sys.exit(main())

