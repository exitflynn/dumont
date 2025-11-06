#!/usr/bin/env python3
"""
Local CoreML benchmarking with simulated inference.

Since CoreML.framework is not available on this system (missing native bindings),
we'll simulate the inference with realistic dummy outputs to test the benchmarking
pipeline end-to-end locally.
"""
import sys
sys.path.insert(0, '/Users/akshittyagi/projects/lops')
sys.path.insert(0, '/Users/akshittyagi/projects/dumont')
sys.path.insert(0, '/Users/akshittyagi/projects/dumont/worker/legacy')

import numpy as np
import coremltools as ct
import time
from benchmark import Benchmark
from model_loader import ModelLoader

class CoreMLSimulator:
    """Wrapper to simulate CoreML inference when framework is unavailable."""
    
    def __init__(self, real_model):
        self.real_model = real_model
        self.spec = real_model.get_spec()
    
    def get_spec(self):
        return self.spec
    
    def predict(self, inputs):
        """Simulate CoreML inference with realistic dummy outputs."""
        # Get output names from spec
        outputs = self.spec.description.output
        result = {}
        
        for out in outputs:
            # Create dummy output matching expected shape
            # For yolov8s: confidence and coordinates are variable-length
            # Simulate typical detection model outputs
            if out.name == 'confidence':
                # Simulate 100 detected objects with confidence scores
                result[out.name] = np.random.rand(100).astype(np.float32)
            elif out.name == 'coordinates':
                # Simulate 100 objects with 4 coordinates each
                result[out.name] = np.random.rand(100, 4).astype(np.float32)
            else:
                # Generic output - create array
                result[out.name] = np.random.rand(10, 10).astype(np.float32)
        
        return result


def test_benchmark_coreml():
    """Test the full benchmarking pipeline with CoreML model."""
    model_path = '/tmp/yolov8s.mlmodel'
    
    print(f"\n{'='*70}")
    print(f"Testing CoreML Benchmarking Pipeline")
    print(f"{'='*70}\n")
    
    # 1. Load the model
    print("Step 1: Loading CoreML model...")
    try:
        model = ct.models.MLModel(model_path)
        print("   ✅ Model loaded\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # 2. Create ModelLoader (should detect CoreML format)
    print("Step 2: Creating ModelLoader instance...")
    try:
        loader = ModelLoader(compute_unit='CoreML')
        # Manually set up the model (would normally be done in load_model)
        loader.model_path = model_path
        loader.session = model  # Reuse the loaded model as "session"
        loader.framework = 'coreml'
        loader.coreml_model = model
        print("   ✅ ModelLoader created\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # 3. Wrap with simulator
    print("Step 3: Wrapping model with inference simulator...")
    try:
        loader.coreml_model = CoreMLSimulator(model)
        loader.session = loader.coreml_model  # Update session too
        print("   ✅ Simulator attached\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # 4. Test create_input
    print("Step 4: Testing input creation...")
    try:
        input_data = loader.create_input()
        print(f"   ✅ Input created: shape={input_data.shape}, dtype={input_data.dtype}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # 5. Test inference
    print("Step 5: Testing inference (simulated)...")
    try:
        result = loader.run_inference(input_data)
        print(f"   ✅ Inference succeeded")
        print(f"   Result type: {type(result)}")
        if isinstance(result, dict):
            print(f"   Output keys: {list(result.keys())}\n")
        else:
            print()
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # 6. Run full benchmark
    print("Step 6: Running full benchmark (5 inference runs)...")
    try:
        benchmark = Benchmark()
        metrics = benchmark.run_full_benchmark(
            loader,
            model_path,
            num_inference_runs=5
        )
        print(f"   ✅ Benchmark completed!")
        print(f"\n   Metrics:")
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"     {key}: {value:.4f}")
            else:
                print(f"     {key}: {value}")
        print()
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = test_benchmark_coreml()
    
    print(f"{'='*70}")
    if success:
        print("✅ CoreML benchmarking pipeline works locally!")
        print("\nNote: This test uses simulated inference since CoreML.framework")
        print("is not available on this system. On a proper macOS machine with")
        print("Xcode, real CoreML inference would run instead.")
    else:
        print("❌ Benchmarking pipeline failed")
    print(f"{'='*70}\n")
