"""
Isolated benchmark task runner for subprocess execution.
This script runs a single benchmarking task (load OR inference) in isolation,
measures timing, and outputs metrics as JSON to stdout.

This design eliminates the "observer effect" on timing measurements.
"""

import sys
import time
import json
import argparse
import numpy as np

try:
    from .model_loader import ModelLoader
except ImportError:
    from model_loader import ModelLoader


def run_load_task(model_path: str, compute_unit: str) -> dict:
    """
    Load a model and measure the loading time.
    
    Args:
        model_path: Local path to the model file
        compute_unit: Compute unit to use (CPU, GPU, etc.)
    
    Returns:
        Dictionary with load timing metrics
    """
    import os
    import warnings
    
    warnings.filterwarnings('ignore')
    
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    
    try:
        model_loader = ModelLoader(compute_unit=compute_unit)
        
        start_time = time.perf_counter()
        model_loader.load_model(model_path, compute_unit=compute_unit)
        load_time_ms = (time.perf_counter() - start_time) * 1000
        
        model_loader.cleanup()
    finally:
        # Restore stdout and stderr
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    return {
        "LoadMsMedian": load_time_ms,
        "LoadMsMin": load_time_ms,
        "LoadMsMax": load_time_ms,
        "LoadMsAverage": load_time_ms,
        "LoadMsStdDev": 0.0,
        "LoadMsFirst": load_time_ms,
    }


def run_infer_task(model_path: str, compute_unit: str, num_runs: int) -> dict:
    """
    Load a model and run inference multiple times, measuring timing.
    
    Args:
        model_path: Local path to the model file
        compute_unit: Compute unit to use (CPU, GPU, etc.)
        num_runs: Number of inference runs to perform
    
    Returns:
        Dictionary with inference timing metrics
    """
    import os
    import warnings
    
    warnings.filterwarnings('ignore')
    
    # Suppress stdout and stderr from model loader (redirect to devnull)
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    
    try:
        model_loader = ModelLoader(compute_unit=compute_unit)
        
        # Load the model (not timed for inference metrics)
        model_loader.load_model(model_path, compute_unit=compute_unit)
        
        # Create sample input
        input_data = model_loader.create_sample_input()
        
        # Run inferences and collect timing
        inference_times = []
        for _ in range(num_runs):
            start_time = time.perf_counter()
            _ = model_loader.run_inference(input_data)
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            inference_times.append(inference_time_ms)
        
        # Clean up
        model_loader.cleanup()
    finally:
        # Restore stdout and stderr
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    # Calculate statistics
    times_array = np.array(inference_times)
    
    return {
        "InferenceMsMedian": float(np.median(times_array)),
        "InferenceMsMin": float(np.min(times_array)),
        "InferenceMsMax": float(np.max(times_array)),
        "InferenceMsAverage": float(np.mean(times_array)),
        "InferenceMsStdDev": float(np.std(times_array)) if len(times_array) > 1 else 0.0,
        "InferenceMsFirst": float(inference_times[0]),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run isolated benchmarking task"
    )
    parser.add_argument(
        "--task",
        required=True,
        choices=["load", "infer"],
        help="Task to run: 'load' or 'infer'"
    )
    parser.add_argument(
        "--model-path",
        required=True,
        type=str,
        help="Local path to the model file"
    )
    parser.add_argument(
        "--compute-unit",
        type=str,
        default="CPU",
        help="Compute unit to use (CPU, GPU, etc.)"
    )
    parser.add_argument(
        "--num-runs",
        type=int,
        default=10,
        help="Number of inference runs (only for 'infer' task)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.task == "load":
            metrics = run_load_task(args.model_path, args.compute_unit)
        elif args.task == "infer":
            metrics = run_infer_task(args.model_path, args.compute_unit, args.num_runs)
        else:
            sys.exit(f"Error: Unknown task '{args.task}'")
        
        # Output metrics as JSON to stdout
        print(json.dumps(metrics))
        sys.exit(0)
    
    except Exception as e:
        # Output error as JSON to stderr
        error_msg = {"error": str(e), "task": args.task}
        print(json.dumps(error_msg), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
