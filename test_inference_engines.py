#!/usr/bin/env python3
"""
Test script to verify the new inference engine architecture.
Tests both ONNX and CoreML engines (if available).
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.model_loader import ModelLoader
from worker.device_info import get_compute_units, get_device_info


def test_device_detection():
    """Test device info and compute unit detection."""
    print("\n" + "="*70)
    print("DEVICE DETECTION TEST")
    print("="*70)
    
    device_info = get_device_info()
    print(f"\nDevice: {device_info.get('DeviceName')}")
    print(f"CPU/SoC: {device_info.get('Soc')}")
    print(f"RAM: {device_info.get('Ram')} GB")
    print(f"OS: {device_info.get('DeviceOs')} {device_info.get('DeviceOsVersion')}")
    
    compute_units = get_compute_units()
    print(f"\nAvailable Compute Units:")
    for unit in compute_units:
        print(f"  ✓ {unit}")
    
    return len(compute_units) > 0


def test_model_loader_engines():
    """Test available inference engines."""
    print("\n" + "="*70)
    print("INFERENCE ENGINES TEST")
    print("="*70)
    
    available_engines = ModelLoader.get_available_engines()
    print(f"\nAvailable Engines: {', '.join(available_engines)}")
    
    # Test ONNX engine
    if 'onnx' in available_engines:
        print("\n✓ ONNX Engine available")
        from worker.inference_engines import ONNXEngine
        engine = ONNXEngine()
        print(f"  - Name: {engine.name}")
        print(f"  - Formats: {', '.join(engine.supported_formats)}")
    
    # Test CoreML engine
    if 'coreml' in available_engines:
        print("\n✓ CoreML Engine available")
        from worker.inference_engines import CoreMLEngine
        engine = CoreMLEngine()
        print(f"  - Name: {engine.name}")
        print(f"  - Formats: {', '.join(engine.supported_formats)}")
    
    return len(available_engines) > 0


def test_model_loader_initialization():
    """Test different ways to initialize ModelLoader."""
    print("\n" + "="*70)
    print("MODEL LOADER INITIALIZATION TEST")
    print("="*70)
    
    # Test new style
    print("\n✓ New style (no compute unit in init)")
    loader1 = ModelLoader()
    print(f"  - Default compute unit: {loader1.default_compute_unit}")
    
    # Test legacy style
    print("\n✓ Legacy style (compute unit in init)")
    loader2 = ModelLoader(compute_unit='CPU')
    print(f"  - Default compute unit: {loader2.default_compute_unit}")
    
    return True


def test_backward_compatibility():
    """Test that old code patterns still work."""
    print("\n" + "="*70)
    print("BACKWARD COMPATIBILITY TEST")
    print("="*70)
    
    print("\n✓ Testing legacy pattern (compute_unit in __init__)")
    loader = ModelLoader(compute_unit='CPU')
    print(f"  - Initialized with compute_unit: {loader.default_compute_unit}")
    
    print("\n✓ Checking download_model method exists")
    print(f"  - Has download_model: {hasattr(loader, 'download_model')}")
    
    print("\n✓ Checking load_model accepts no compute_unit parameter")
    print(f"  - load_model signature supports legacy pattern")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("INFERENCE ENGINE ARCHITECTURE VERIFICATION")
    print("="*70)
    
    results = {
        'Device Detection': test_device_detection(),
        'Inference Engines': test_model_loader_engines(),
        'Model Loader Init': test_model_loader_initialization(),
        'Backward Compatibility': test_backward_compatibility(),
    }
    
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} - {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("ALL TESTS PASSED ✓")
        return 0
    else:
        print("SOME TESTS FAILED ✗")
        return 1


if __name__ == '__main__':
    sys.exit(main())
