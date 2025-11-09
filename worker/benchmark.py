import time
import psutil
import numpy as np
from typing import Dict, List, Optional
from .model_loader import ModelLoader


class Benchmark:
    
    def __init__(self):
        self.process = psutil.Process()
    
    def _get_ram_usage_mb(self) -> float:
        return self.process.memory_info().rss / (1024 ** 2)
    
    def _get_cpu_percent(self) -> float:
        return self.process.cpu_percent(interval=0.1)
    
    def benchmark_load(self, model_loader: ModelLoader, model_path: str) -> Dict[str, float]:
        baseline_ram = self._get_ram_usage_mb()
        
        start_time = time.perf_counter()
        model_loader.load_model(model_path)
        load_time_ms = (time.perf_counter() - start_time) * 1000
        
        peak_ram = self._get_ram_usage_mb()
        peak_ram_usage = max(0.0, peak_ram - baseline_ram)
        
        return {
            'LoadMsMedian': float(load_time_ms),
            'LoadMsMin': float(load_time_ms),
            'LoadMsMax': float(load_time_ms),
            'LoadMsAverage': float(load_time_ms),
            'LoadMsStdDev': 0.0,
            'LoadMsFirst': float(load_time_ms),
            'PeakLoadRamUsage': float(peak_ram_usage),
        }
    
    def benchmark_inference(self, model_loader: ModelLoader, num_runs: int = 10) -> Dict[str, float]:
        if model_loader.engine is None:
            raise ValueError("Model not loaded. Call benchmark_load() first.")
        
        baseline_ram = self._get_ram_usage_mb()
        peak_ram = baseline_ram
        
        input_data = model_loader.create_sample_input()
        
        inference_times = []
        ram_usage_during_inference = []
        
        for _ in range(num_runs):
            start_time = time.perf_counter()
            _ = model_loader.run_inference(input_data)
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            
            current_ram = self._get_ram_usage_mb()
            if current_ram > peak_ram:
                peak_ram = current_ram
            
            ram_delta = current_ram - baseline_ram
            inference_times.append(inference_time_ms)
            ram_usage_during_inference.append(ram_delta)
        
        if len(inference_times) > 0:
            times_array = np.array(inference_times)
            peak_ram_usage = max(0.0, peak_ram - baseline_ram)
            return {
                'InferenceMsMedian': float(np.median(times_array)),
                'InferenceMsMin': float(np.min(times_array)),
                'InferenceMsMax': float(np.max(times_array)),
                'InferenceMsAverage': float(np.mean(times_array)),
                'InferenceMsStdDev': float(np.std(times_array)) if len(times_array) > 1 else 0.0,
                'InferenceMsFirst': float(inference_times[0]),
                'PeakInferenceRamUsage': float(peak_ram_usage),
            }
        else:
            raise ValueError("No inference runs completed")
    
    def run_full_benchmark(self, model_loader: ModelLoader, model_path: str, 
                          num_inference_runs: int = 10) -> Dict[str, float]:
        load_metrics = self.benchmark_load(model_loader, model_path)
        
        inference_metrics = self.benchmark_inference(model_loader, num_inference_runs)
        
        return {**load_metrics, **inference_metrics}

