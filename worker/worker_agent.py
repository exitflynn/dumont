"""
Worker Agent - Listens for benchmarking jobs on Redis and executes them.
Registers with orchestrator, consumes jobs, runs benchmarks, publishes results.
"""

import logging
import argparse
import time
import requests
import json
import os
import threading
from typing import Dict, Optional, List

# Import benchmarking modules using relative imports
from .model_loader import ModelLoader
from .benchmark import Benchmark
from .device_info import get_device_info, get_compute_units


logger = logging.getLogger(__name__)


class WorkerAgent:
    """Worker agent that executes benchmarking jobs from Redis queues."""
    
    def __init__(self, orchestrator_url: str, redis_host: str = 'localhost',
                 redis_port: int = 6379):
        self.orchestrator_url = orchestrator_url
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.worker_id: Optional[str] = None
        self.redis_client = None
        self.running = False
        
        # Heartbeat thread management
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.heartbeat_running = False
        self.heartbeat_interval = 10  # seconds
        self.continuous_heartbeat = False  # For heartbeat during idle & execution
        
        # Lazy imports to avoid issues if Redis not available
        self._redis = None
    
    @property
    def redis_client(self):
        if self._redis is None:
            from core.redis_client import RedisClient
            self._redis = RedisClient(
                host=self.redis_host,
                port=self.redis_port
            )
        return self._redis
    
    @redis_client.setter
    def redis_client(self, value):
        self._redis = value
    
    def start_heartbeat_during_execution(self, interval: int = 10) -> None:
        if self.heartbeat_running:
            logger.warning("Heartbeat thread already running")
            return
        
        self.heartbeat_interval = interval
        self.heartbeat_running = True
        self.continuous_heartbeat = True
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(interval,),
            daemon=False,  # Non-daemon - thread will stay alive during job execution
            name="WorkerHeartbeatThread"
        )
        self.heartbeat_thread.start()
        logger.info(f"Started heartbeat thread (every {interval}s) for worker {self.worker_id}")
    
    def stop_heartbeat_during_execution(self) -> None:
        if not self.heartbeat_running:
            return
        
        logger.info(f"🛑 Stopping heartbeat thread for worker {self.worker_id}")
        self.continuous_heartbeat = False
        self.heartbeat_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)
            logger.info(f"Heartbeat thread stopped")
    
    def start_continuous_heartbeat(self, interval: int = 10) -> None:
        if self.heartbeat_running:
            logger.warning("Heartbeat thread already running")
            return
        
        self.heartbeat_interval = interval
        self.heartbeat_running = True
        self.continuous_heartbeat = True
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(interval,),
            daemon=False,  # Non-daemon - thread stays alive
            name="WorkerContinuousHeartbeatThread"
        )
        self.heartbeat_thread.start()
        logger.info(f"Started continuous heartbeat thread (every {interval}s) for worker {self.worker_id}")
    
    def stop_continuous_heartbeat(self) -> None:
        if not self.heartbeat_running:
            return
        
        logger.info(f"Stopping continuous heartbeat for worker {self.worker_id}")
        self.continuous_heartbeat = False
        self.heartbeat_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)
            logger.info(f"Continuous heartbeat stopped")
    
    def _heartbeat_loop(self, interval: int) -> None:
        heartbeat_count = 0
        
        logger.info(f"Heartbeat loop started for {self.worker_id}")
        
        while self.heartbeat_running:
            try:
                # Send heartbeat
                response = requests.post(
                    f"{self.orchestrator_url}/api/workers/{self.worker_id}/heartbeat",
                    timeout=5,
                    json={'timestamp': time.time()}
                )
                
                heartbeat_count += 1
                
                if response.status_code == 200:
                    logger.debug(f"Heartbeat #{heartbeat_count} sent")
                else:
                    logger.warning(f"Heartbeat #{heartbeat_count} failed: HTTP {response.status_code}")
            
            except requests.Timeout:
                logger.warning(f"Heartbeat #{heartbeat_count} timeout")
            except Exception as e:
                logger.warning(f"Heartbeat #{heartbeat_count} error: {e}")
            
            for _ in range(int(interval * 10)):
                if not self.heartbeat_running:
                    logger.info(f"Heartbeat loop exiting (sent {heartbeat_count} beats)")
                    break
                time.sleep(0.1)
    
    def _send_heartbeat(self) -> bool:
        try:
            response = requests.post(
                f"{self.orchestrator_url}/api/workers/{self.worker_id}/heartbeat",
                timeout=5,
                json={'timestamp': time.time()}
            )
            success = response.status_code == 200
            if not success:
                logger.warning(f"Direct heartbeat failed: {response.status_code}")
            return success
        except Exception as e:
            logger.warning(f"Failed to send direct heartbeat: {e}")
            return False
    
    def register_with_orchestrator(self) -> bool:
        try:
            device_info = get_device_info()
            capabilities = get_compute_units()
            
            registration_data = {
                'device_name': device_info.get('DeviceName', 'Unknown'),
                'ip_address': 'localhost',
                'capabilities': capabilities,
                'device_info': {
                    'DeviceName': device_info.get('DeviceName', ''),
                    'Soc': device_info.get('Soc', ''),
                    'Ram': device_info.get('Ram', 0),
                    'DeviceOs': device_info.get('DeviceOs', ''),
                    'DeviceOsVersion': device_info.get('DeviceOsVersion', ''),
                }
            }
            
            # Register with orchestrator
            response = requests.post(
                f"{self.orchestrator_url}/api/register",
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.worker_id = data['worker_id']
                logger.info(f"Registered with orchestrator as {self.worker_id}")
                logger.info(f"Device: {registration_data['device_name']}, Capabilities: {', '.join(capabilities)}")
                return True
            else:
                logger.error(f"Failed to register: {response.status_code} {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to register with orchestrator: {e}")
            return False
    
    def get_job_details(self, job_id: str) -> Optional[Dict]:
        try:
            response = requests.get(
                f"{self.orchestrator_url}/api/jobs/{job_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('job')
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get job details: {e}")
            return None
    
    def execute_benchmark_job(self, job_info: Dict) -> Dict:
        job_id = job_info['job_id']
        model_url = job_info['model_url']
        compute_unit = job_info.get('compute_unit', 'CPU')
        num_inference_runs = job_info.get('num_inference_runs', 10)
        
        start_time = time.time()
        
        logger.info(f"Executing job {job_id} - Model: {model_url}, Compute: {compute_unit}")
        
        start_time = time.time()
        
        try:
            model_loader = ModelLoader(compute_unit=compute_unit)
            benchmark = Benchmark()
            
            model_path = model_loader.download_model(model_url)
            metrics = benchmark.run_full_benchmark(
                model_loader,
                model_path,
                num_inference_runs=num_inference_runs
            )
            
            import os
            file_size = os.path.getsize(model_path)
            filename = os.path.basename(model_path)
            
            device_info = get_device_info()
            model_loader.cleanup()
            
            elapsed = time.time() - start_time
            
            result = {
                'job_id': job_id,
                'campaign_id': job_info.get('campaign_id'),
                'worker_id': self.worker_id,
                'status': 'Complete',
                'FileName': filename,
                'FileSize': file_size,
                'ComputeUnits': compute_unit,
                'DeviceName': device_info.get('DeviceName') or 'Unknown',
                'DeviceOs': device_info.get('DeviceOs') or '',
                'DeviceOsVersion': device_info.get('DeviceOsVersion') or '',
                'DeviceYear': device_info.get('DeviceYear') or '',
                'Soc': device_info.get('Soc') or '',
                'Ram': device_info.get('Ram') or 0,
                'DiscreteGpu': device_info.get('DiscreteGpu') or '',
                'VRam': device_info.get('VRam') or '',
                **metrics
            }
            
            logger.info(f"Job {job_id} completed in {elapsed:.1f}s")
            return result
        
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Job {job_id} failed after {elapsed:.1f}s: {e}", exc_info=True)
            device_info = get_device_info()
            
            return {
                'job_id': job_id,
                'campaign_id': job_info.get('campaign_id'),
                'worker_id': self.worker_id,
                'status': 'Failed',
                'remark': str(e),
                'FileName': '',
                'FileSize': 0,
                'ComputeUnits': compute_unit,
                'DeviceName': device_info.get('DeviceName') or 'Unknown',
                'DeviceOs': device_info.get('DeviceOs') or '',
                'DeviceOsVersion': device_info.get('DeviceOsVersion') or '',
                'DeviceYear': device_info.get('DeviceYear') or '',
                'Soc': device_info.get('Soc') or '',
                'Ram': device_info.get('Ram') or 0,
                'DiscreteGpu': device_info.get('DiscreteGpu') or '',
                'VRam': device_info.get('VRam') or '',
            }
    
    def publish_result(self, result: Dict) -> bool:
        try:
            success = self.redis_client.push_result(result)
            if success:
                logger.info(f"Published result for job {result['job_id']}")
            return success
        
        except Exception as e:
            logger.error(f"Failed to publish result: {e}")
            return False
    
    def get_job_queue_names(self) -> List[str]:
        from core.job_dispatcher import JobDispatcher
        capabilities = get_compute_units()
        queues = JobDispatcher.get_worker_queue_priority(str(self.worker_id), capabilities)
        
        return queues
    
    def start_job_loop(self) -> None:
        if not self.worker_id:
            logger.error("Worker not registered")
            return
        
        if not self.redis_client.is_connected():
            logger.error("Redis not connected")
            return
        
        logger.info(f"Starting job loop for worker {self.worker_id}")
        self.start_continuous_heartbeat(interval=10)
        
        self.running = True
        job_count = 0
        
        try:
            while self.running:
                queue_names = self.get_job_queue_names()
                job_id = self.redis_client.pop_job(queue_names, timeout=0)
                
                if job_id:
                    job_count += 1
                    logger.debug(f"Got job {job_id}")
                    job_info = self.get_job_details(job_id)
                    
                    if job_info:
                        result = self.execute_benchmark_job(job_info)
                        self.publish_result(result)
                    else:
                        logger.warning(f"Could not fetch job details for {job_id}")
                else:
                    time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        
        except Exception as e:
            logger.error(f"Error in job loop: {e}", exc_info=True)
        
        finally:
            self.stop_continuous_heartbeat()
            self.running = False
            logger.info(f"Job loop complete: {job_count} jobs executed")


def main():
    parser = argparse.ArgumentParser(description='ML Model Benchmarking Worker Agent')
    parser.add_argument('--orchestrator-url', type=str, default='http://localhost:5000')
    parser.add_argument('--redis-host', type=str, default='localhost')
    parser.add_argument('--redis-port', type=int, default=6379)
    parser.add_argument('--debug', action='store_true')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    worker = WorkerAgent(
        orchestrator_url=args.orchestrator_url,
        redis_host=args.redis_host,
        redis_port=args.redis_port
    )
    
    if not worker.register_with_orchestrator():
        logger.error("Failed to register with orchestrator")
        return 1
    
    try:
        worker.start_job_loop()
    except KeyboardInterrupt:
        logger.info("Shutting down worker")
    
    return 0


if __name__ == '__main__':
    exit(main())

