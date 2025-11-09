"""
Inference engines module - Support for multiple ML inference frameworks.
Provides pluggable architecture for adding new inference engines.
"""

from .base import InferenceEngine
from .onnx_engine import ONNXEngine
from .coreml_engine import CoreMLEngine

__all__ = [
    'InferenceEngine',
    'ONNXEngine',
    'CoreMLEngine',
]
