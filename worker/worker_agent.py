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
import sys
import subprocess
import psutil
import threading
from typing import Dict, Optional, List, Tuple

# Import benchmarking modules using relative imports
from .model_loader import ModelLoader
from .device_info import get_device_info, get_compute_units
from core.constants import WORKER_STATUS_ACTIVE, WORKER_STATUS_BUSY, RESULT_STATUS_COMPLETE, RESULT_STATUS_FAILED


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
    
    def _update_status(self, status: str) -> bool:
        """Update worker status in orchestrator."""
        try:
            response = requests.put(
                f"{self.orchestrator_url}/api/workers/{self.worker_id}/status",
                timeout=5,
                json={'status': status}
            )
            success = response.status_code == 200
            if success:
                logger.debug(f"Status updated to: {status}")
            else:
                logger.warning(f"Status update failed: {response.status_code}")
            return success
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")
            return False
    
    def _monitor_subprocess(self, proc: psutil.Process, results: dict) -> None:
        """
        Monitor a subprocess's RAM and CPU usage at high frequency.
        This runs in a separate thread and samples every 5ms to catch peak transient allocations.
        
        Args:
            proc: psutil.Process object to monitor
            results: Dictionary to store monitoring results
        """
        peak_ram = 0
        cpu_samples = []
        
        try:
            # Call cpu_percent() once outside the loop to establish a baseline
            proc.cpu_percent(interval=None)
            
            while proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                try:
                    # Sample RAM and CPU
                    current_ram = proc.memory_info().rss
                    if current_ram > peak_ram:
                        peak_ram = current_ram
                    
                    cpu_samples.append(proc.cpu_percent(interval=None))
                
                except psutil.NoSuchProcess:
                    break
                
                time.sleep(0.005)
        
        except psutil.NoSuchProcess:
            pass
        
        finally:
            results['peak_ram_bytes'] = peak_ram
            if cpu_samples:
                results['average_cpu_percent'] = sum(cpu_samples) / len(cpu_samples)
            else:
                results['average_cpu_percent'] = 0.0
    
    def _run_benchmark_task(self, args: List[str]) -> Tuple[dict, float, float]:
        """
        Run a benchmark task in a subprocess and monitor its peak RAM and CPU usage.
        
        Args:
            args: Command-line arguments for run_job_task.py
        
        Returns:
            Tuple of (task_metrics_dict, peak_ram_mb, average_cpu_percent)
        
        Raises:
            RuntimeError: If the subprocess fails
        """
        # Build command: python -m worker.run_job_task <args>
        command = [sys.executable, "-m", "worker.run_job_task"] + args
        
        logger.debug(f"Running subprocess: {' '.join(command)}")
        
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        ps_proc = psutil.Process(proc.pid)
        
        monitor_results = {}
        monitor_thread = threading.Thread(
            target=self._monitor_subprocess,
            args=(ps_proc, monitor_results),
            daemon=True,
            name="SubprocessMonitor"
        )
        monitor_thread.start()
        
        # Wait for the process to finish
        stdout, stderr = proc.communicate()
        
        monitor_thread.join(timeout=1.0)
        
        if proc.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "Unknown error"
            raise RuntimeError(f"Benchmark task failed: {error_msg}")
        
        try:
            task_metrics = json.loads(stdout.decode())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse task output: {e}")
        
        peak_ram_mb = monitor_results.get('peak_ram_bytes', 0) / (1024 ** 2)
        average_cpu = monitor_results.get('average_cpu_percent', 0.0)
        
        return task_metrics, peak_ram_mb, average_cpu
    
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
        """
        Execute a benchmarking job using the subprocess-based approach.
        
        This method:
        1. Downloads the model once
        2. Spawns isolated subprocesses for 'load' and 'infer' tasks
        3. Monitors each subprocess's peak RAM and CPU from outside
        4. Combines results and cleans up
        
        Args:
            job_info: Job information dictionary
        
        Returns:
            Result dictionary with metrics
        """
        job_id = job_info['job_id']
        model_url = job_info['model_url']
        compute_unit = job_info.get('compute_unit', 'CPU')
        num_inference_runs = job_info.get('num_inference_runs', 10)
        
        start_time = time.time()
        
        logger.info(f"Executing job {job_id} - Model: {model_url}, Compute: {compute_unit}")
        
        self._update_status(WORKER_STATUS_BUSY)
        
        try:
            model_loader = ModelLoader(compute_unit=compute_unit)
            model_path = model_loader.download_model(model_url)
            
            file_size = os.path.getsize(model_path)
            filename = os.path.basename(model_path)
            
            logger.info(f"Model downloaded: {filename} ({file_size / (1024**2):.2f} MB)")
            
            load_args = [
                "--task", "load",
                "--model-path", model_path,
                "--compute-unit", compute_unit
            ]
            
            logger.debug("Running load task...")
            load_metrics, peak_load_ram, avg_load_cpu = self._run_benchmark_task(load_args)
            logger.info(f"Load completed: {load_metrics['LoadMsMedian']:.2f}ms, "
                       f"Peak RAM: {peak_load_ram:.2f}MB, Avg CPU: {avg_load_cpu:.1f}%")
            
            infer_args = [
                "--task", "infer",
                "--model-path", model_path,
                "--compute-unit", compute_unit,
                "--num-runs", str(num_inference_runs)
            ]
            
            logger.debug("Running inference task...")
            infer_metrics, peak_infer_ram, avg_infer_cpu = self._run_benchmark_task(infer_args)
            logger.info(f"Inference completed: {infer_metrics['InferenceMsMedian']:.2f}ms median, "
                       f"Peak RAM: {peak_infer_ram:.2f}MB, Avg CPU: {avg_infer_cpu:.1f}%")
            
            try:
                os.remove(model_path)
                logger.debug(f"Cleaned up model file: {model_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up model {model_path}: {e}")
            
            device_info = get_device_info()
            elapsed = time.time() - start_time
            
            result = {
                'job_id': job_id,
                'campaign_id': job_info.get('campaign_id'),
                'worker_id': self.worker_id,
                'status': RESULT_STATUS_COMPLETE,
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
                **load_metrics,
                'PeakLoadRamUsage': float(peak_load_ram),
                'AverageLoadCpuPercent': float(avg_load_cpu),
                **infer_metrics,
                'PeakInferenceRamUsage': float(peak_infer_ram),
                'AverageInferenceCpuPercent': float(avg_infer_cpu),
            }
            
            logger.info(f"Job {job_id} completed successfully in {elapsed:.1f}s")
            
            # Update status back to active
            self._update_status(WORKER_STATUS_ACTIVE)
            
            return result
        
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Job {job_id} failed after {elapsed:.1f}s: {e}", exc_info=True)
            device_info = get_device_info()
            
            # Update status back to active even on failure
            self._update_status(WORKER_STATUS_ACTIVE)
            
            return {
                'job_id': job_id,
                'campaign_id': job_info.get('campaign_id'),
                'worker_id': self.worker_id,
                'status': RESULT_STATUS_FAILED,
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
    parser.add_argument('--host', type=str, default='http://localhost:5000', 
                       help='Orchestrator URL')
    parser.add_argument('--redis-host', type=str, default='localhost',
                       help='Redis host')
    parser.add_argument('--redis-port', type=int, default=6379,
                       help='Redis port')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    worker = WorkerAgent(
        orchestrator_url=args.host,
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

