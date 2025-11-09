"""
ONNX Runtime inference engine.
Supports CPU and various hardware accelerators via ONNX Runtime providers.
"""

import os
import tempfile
import urllib.request
import urllib.parse
from typing import Optional, Tuple, Any, List
import numpy as np
import onnxruntime as ort

from .base import InferenceEngine


class ONNXEngine(InferenceEngine):
    """
    ONNX Runtime inference engine.
    
    Supports:
    - CPU (cross-platform)
    - CUDA (NVIDIA GPUs)
    - DML (Windows GPU/NPU)
    - OpenVINO (Intel acceleration)
    """
    
    def __init__(self, compute_unit: str = 'CPU'):
        """
        Initialize ONNX engine.
        
        Args:
            compute_unit: Compute unit to use ('CPU', 'CUDA', 'DML', 'OpenVINO;CPU', etc.)
        """
        self.compute_unit = compute_unit
        self.session: Optional[ort.InferenceSession] = None
        self.model_path: Optional[str] = None
        self._input_shape: Optional[Tuple] = None
    
    @property
    def name(self) -> str:
        return "ONNX"
    
    @property
    def supported_formats(self) -> List[str]:
        return ['.onnx']
    
    def is_available(self) -> bool:
        """Check if ONNX Runtime is available."""
        try:
            import onnxruntime
            return True
        except ImportError:
            return False
    
    def _get_providers(self) -> List[str]:
        """Get ONNX Runtime execution providers based on compute unit."""
        providers = []
        
        if self.compute_unit == 'CPU':
            providers = ['CPUExecutionProvider']
        elif self.compute_unit == 'CUDA':
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        elif self.compute_unit == 'DML':
            providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
        elif self.compute_unit.startswith('OpenVINO'):
            providers = ['OpenVINOExecutionProvider', 'CPUExecutionProvider']
        else:
            providers = ['CPUExecutionProvider']
        
        available_providers = ort.get_available_providers()
        return [p for p in providers if p in available_providers]
    
    def download_model(self, model_url: str, download_dir: Optional[str] = None) -> str:
        """
        Download model from URL or use local file path.
        
        Args:
            model_url: URL to download the model from, or local file path
            download_dir: Directory to save the model (default: temp directory)
            
        Returns:
            Path to model file
        """

        if os.path.exists(model_url):
            print(f"Using local model file: {model_url}")
            return model_url
        
        if download_dir is None:
            download_dir = tempfile.gettempdir()
        
        parsed_url = urllib.parse.urlparse(model_url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            filename = 'model.onnx'
        
        model_path = os.path.join(download_dir, filename)
        
        print(f"Downloading ONNX model from {model_url}...")
        urllib.request.urlretrieve(model_url, model_path)
        print(f"ONNX model downloaded to {model_path}")
        
        return model_path
    
    def load_model(self, model_path: str) -> None:
        """Load ONNX model into inference session."""
        if not model_path.lower().endswith('.onnx'):
            raise ValueError(f"Expected .onnx file, got {model_path}")
        
        self.model_path = model_path
        providers = self._get_providers()
        
        print(f"Loading ONNX model with providers: {providers}")
        self.session = ort.InferenceSession(model_path, providers=providers)
        print(f"ONNX model loaded successfully. Input shape: {self.get_input_shape()}")
    
    def get_input_shape(self) -> Tuple:
        """Get input shape from ONNX model."""
        if self.session is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        input_meta = self.session.get_inputs()[0]
        shape = input_meta.shape
        
        # Replace dynamic dimensions with 1
        shape = [s if isinstance(s, int) else 1 for s in shape]
        return tuple(shape)
    
    def create_sample_input(self) -> np.ndarray:
        """Create a sample input for the model."""
        if self.session is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        shape = self.get_input_shape()
        dtype = np.float32
        
        # Try to get dtype from model input metadata
        try:
            input_meta = self.session.get_inputs()[0]
            if hasattr(input_meta, 'type'):
                if 'float' in str(input_meta.type):
                    dtype = np.float32
                elif 'int' in str(input_meta.type):
                    dtype = np.int32
        except:
            pass
        
        return np.random.rand(*shape).astype(dtype)
    
    def run_inference(self, input_data: np.ndarray) -> Any:
        """Run inference on the model."""
        if self.session is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: input_data})
        return outputs
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.session = None
