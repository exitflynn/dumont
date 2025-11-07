#!/bin/bash

set -e

echo "CycleOPS Worker Agent"
echo "========================"
echo ""

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:5000}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6380}"
WORKER_NAME="${WORKER_NAME:-cycleops-worker-$(hostname)}"

echo "Configuration:"
echo "  Orchestrator: $ORCHESTRATOR_URL"
echo "  Redis: $REDIS_HOST:$REDIS_PORT"
echo "  Worker: $WORKER_NAME"
echo ""

echo "Checking orchestrator availability..."
for i in {1..10}; do
    if curl -sf "$ORCHESTRATOR_URL/api/health" > /dev/null 2>&1; then
        echo "Orchestrator is accessible!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "Could not reach orchestrator at $ORCHESTRATOR_URL"
        echo "   Make sure orchestrator is running:"
        echo "   cd /Users/akshittyagi/projects/lops"
        echo "   docker-compose up -d orchestrator"
        exit 1
    fi
    echo "   Attempt $i/10..."
    sleep 1
done

echo ""
echo "Worker is now listening for jobs..."
echo "   Stop with: Ctrl+C"
echo ""

cd /Users/akshittyagi/projects/dumont
export PYTHONUNBUFFERED=1
python3 << 'PYTHON_EOF'
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.insert(0, '/Users/akshittyagi/projects/dumont')

from worker.worker_agent import WorkerAgent

# Get environment variables
orchestrator_url = os.environ.get('ORCHESTRATOR_URL', 'http://localhost:5000')
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = int(os.environ.get('REDIS_PORT', '6379'))

try:
    from core.redis_client import RedisClient
    r = RedisClient(host=redis_host, port=int(redis_port))
    if not r.is_connected():
        logger.error(f"Cannot connect to Redis at {redis_host}:{redis_port}")
        sys.exit(1)
    logger.info(f"Redis connected")
    logger.info(f"Registering worker with orchestrator...")
    
    from worker.worker_agent import WorkerAgent
    worker = WorkerAgent(
        orchestrator_url=orchestrator_url,
        redis_host=redis_host,
        redis_port=int(redis_port)
    )
    
    if worker.register_with_orchestrator():
        logger.info("Worker registered successfully!")
        worker.start_job_loop()
    else:
        logger.error("Failed to register worker with orchestrator")
        sys.exit(1)

except Exception as e:
    logger.error(f"Fatal error: {e}", exc_info=True)
    sys.exit(1)
PYTHON_EOF
