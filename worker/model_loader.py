"""
Unified model loader supporting multiple inference engines.
Automatically selects the appropriate engine based on model format and availability.
"""

import os
from typing import Optional, Dict
import numpy as np

from .inference_engines import InferenceEngine, ONNXEngine, CoreMLEngine


class ModelLoader:
    
    ENGINES: Dict[str, type] = {
        'onnx': ONNXEngine,
        'coreml': CoreMLEngine,
    }
    
    def __init__(self, compute_unit: str = 'CPU'):
        self.engine: Optional[InferenceEngine] = None
        self.model_path: Optional[str] = None
        self.default_compute_unit = compute_unit
    
    def _get_engine_for_model(self, model_path: str) -> Optional[type]:
        _, ext = os.path.splitext(model_path)
        ext = ext.lower()
        
        for engine_class in self.ENGINES.values():
            engine_instance = engine_class() if engine_class.__name__ != 'ONNXEngine' else None
            if engine_class.__name__ == 'ONNXEngine':
                engine_instance = engine_class()
            
            if hasattr(engine_instance, 'supported_formats') and ext in engine_instance.supported_formats:
                if engine_instance.is_available():
                    return engine_class
        
        return None
    
    def download_model(self, model_url: str, download_dir: Optional[str] = None) -> str:
        if os.path.exists(model_url):
            print(f"Using local model file: {model_url}")
            return model_url
        
        import tempfile
        import urllib.request
        import urllib.parse
        
        if download_dir is None:
            download_dir = tempfile.gettempdir()
        
        parsed_url = urllib.parse.urlparse(model_url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            filename = 'model.onnx'
        
        model_path = os.path.join(download_dir, filename)
        
        print(f"Downloading model from {model_url}...")
        
        try:
            urllib.request.urlretrieve(model_url, model_path)
            
            if not os.path.exists(model_path):
                raise ValueError(f"Download failed: file not created at {model_path}")
            
            file_size = os.path.getsize(model_path)
            if file_size == 0:
                raise ValueError(f"Download failed: file is empty")
            
            
            print(f"Model downloaded to {model_path} ({file_size / (1024**2):.2f} MB)")
            
        except Exception as e:
            if os.path.exists(model_path):
                os.remove(model_path)
            raise ValueError(f"Failed to download model from {model_url}: {str(e)}")
        
        return model_path
    
    def load_model(self, model_path: str, compute_unit: Optional[str] = None) -> None:
        if not os.path.exists(model_path):
            raise ValueError(f"Model file not found: {model_path}")
        
        if compute_unit is None:
            compute_unit = self.default_compute_unit
        
        engine_class = self._get_engine_for_model(model_path)
        if engine_class is None:
            raise ValueError(
                f"No suitable inference engine found for {model_path}. "
                f"Supported formats: {', '.join(self._get_all_supported_formats())}"
            )
        
        if engine_class.__name__ == 'ONNXEngine':
            self.engine = engine_class(compute_unit=compute_unit)
        else:
            self.engine = engine_class()
        
        print(f"Using {self.engine.name} engine for {os.path.basename(model_path)}")
        
        self.engine.load_model(model_path)
        self.model_path = model_path
    
    def get_input_shape(self):
        if self.engine is None:
            raise RuntimeError("No model loaded. Call load_model() first.")
        return self.engine.get_input_shape()
    
    def create_sample_input(self):
        if self.engine is None:
            raise RuntimeError("No model loaded. Call load_model() first.")
        return self.engine.create_sample_input()
    
    def run_inference(self, input_data):
        if self.engine is None:
            raise RuntimeError("No model loaded. Call load_model() first.")
        return self.engine.run_inference(input_data)
    
    def cleanup(self):
        if self.engine is not None:
            self.engine.cleanup()
        self.engine = None
        self.model_path = None
    
    @staticmethod
    def _get_all_supported_formats():
        formats = set()
        for engine_class in ModelLoader.ENGINES.values():
            if engine_class.__name__ == 'ONNXEngine':
                engine = engine_class()
            else:
                engine = engine_class()
            formats.update(engine.supported_formats)
        return sorted(formats)
    
    @staticmethod
    def get_available_engines():
        available = []
        for name, engine_class in ModelLoader.ENGINES.items():
            if engine_class.__name__ == 'ONNXEngine':
                engine = engine_class()
            else:
                engine = engine_class()
            if engine.is_available():
                available.append(name)
        return available
