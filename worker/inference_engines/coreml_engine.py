"""
Apple CoreML inference engine.
Supports neural engine and GPU acceleration on macOS/iOS via Apple CoreML framework.
"""

import os
from typing import Optional, Tuple, Any, List
import numpy as np

try:
    import coremltools as ct
except ImportError:
    ct = None

from .base import InferenceEngine


class CoreMLEngine(InferenceEngine):
    """
    Apple CoreML inference engine.
    
    Supports:
    - CPU (all devices)
    - GPU (Apple Silicon)
    - Neural Engine (Apple Silicon)
    
    Note: This engine only works on macOS/iOS systems with Apple CoreML.framework support.
    """
    
    def __init__(self):
        """Initialize CoreML engine."""
        self.model: Optional[Any] = None
        self.model_path: Optional[str] = None
        self._input_shape: Optional[Tuple] = None
        self._spec: Optional[Any] = None
    
    @property
    def name(self) -> str:
        return "CoreML"
    
    @property
    def supported_formats(self) -> List[str]:
        return ['.mlmodel']
    
    def is_available(self) -> bool:
        """Check if CoreML is available on this system."""
        if ct is None:
            return False
        
        import platform
        if platform.system() != "Darwin":
            return False
        
        return True
    
    def load_model(self, model_path: str) -> None:
        """Load CoreML model."""
        if not model_path.lower().endswith('.mlmodel'):
            raise ValueError(f"Expected .mlmodel file, got {model_path}")
        
        if ct is None:
            raise RuntimeError(
                "coremltools is required to load .mlmodel files. "
                "Install with: pip install coremltools"
            )
        
        self.model_path = model_path
        
        try:
            print(f"Loading CoreML model from {model_path}...")
            self.model = ct.models.MLModel(model_path)
            
            # Get model spec for input/output information
            self._spec = self._get_model_spec()
            
            # Verify CoreML.framework is available by attempting a test prediction
            try:
                test_input = self._create_test_input()
                input_name = self._get_input_name()
                _ = self.model.predict({input_name: test_input})
                print(f"CoreML model loaded successfully with neural engine support")
            except Exception as framework_error:
                if "Unable to load CoreML.framework" in str(framework_error):
                    raise RuntimeError(
                        "CoreML.framework native bindings are not available. "
                        "Ensure you're on a compatible macOS version."
                    )
                else:
                    print(f"CoreML model loaded (warning during test: {framework_error})")
        
        except Exception as e:
            raise RuntimeError(f"Failed to load CoreML model: {e}")
    
    def _get_model_spec(self) -> Any:
        """Get the model specification."""
        if hasattr(self.model, 'get_spec'):
            return self.model.get_spec()
        elif hasattr(self.model, '_spec'):
            return self.model._spec
        return None
    
    def _get_input_name(self) -> str:
        """Get the first input name from the model."""
        if self._spec and hasattr(self._spec, 'description'):
            inputs = self._spec.description.input
            if len(inputs) > 0:
                return inputs[0].name
        return 'input'
    
    def _create_test_input(self) -> np.ndarray:
        """Create a test input for model verification."""
        shape = self.get_input_shape()
        return np.random.rand(*shape).astype(np.float32)
    
    def get_input_shape(self) -> Tuple:
        """Get input shape from CoreML model spec."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        try:
            spec = self._get_model_spec()
            if spec and hasattr(spec, 'description'):
                inputs = spec.description.input
                if len(inputs) > 0:
                    inp = inputs[0]
                    t = getattr(inp, 'type', None)
                    
                    if t is not None:
                        # Check for imageType inputs (e.g., vision models)
                        if hasattr(t, 'imageType'):
                            img_type = t.imageType
                            h = img_type.height if img_type.height > 0 else 224
                            w = img_type.width if img_type.width > 0 else 224
                            return (1, h, w, 3)
                        
                        # Check for multiArrayType inputs
                        elif hasattr(t, 'multiArrayType'):
                            shape_vals = t.multiArrayType.shape
                            shape = []
                            for d in shape_vals:
                                if isinstance(d, int) and d > 0:
                                    shape.append(d)
                                else:
                                    shape.append(1)
                            if shape:
                                return tuple(shape)
        except Exception as e:
            print(f"Warning: Failed to extract shape from CoreML spec: {e}")
        
        # Fallback default
        return (1, 3, 224, 224)
    
    def create_sample_input(self) -> Any:
        """
        Create a sample input for the model.
        
        For imageType inputs, returns a PIL Image.
        For other inputs, returns a NumPy array.
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        try:
            spec = self._get_model_spec()
            if spec and hasattr(spec, 'description'):
                inputs = spec.description.input
                if len(inputs) > 0:
                    inp = inputs[0]
                    t = getattr(inp, 'type', None)
                    
                    if t and hasattr(t, 'imageType'):
                        # Create PIL Image for imageType inputs
                        try:
                            from PIL import Image
                            img_type = t.imageType
                            h = img_type.height if img_type.height > 0 else 224
                            w = img_type.width if img_type.width > 0 else 224
                            # Create random RGB image
                            img_array = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
                            return Image.fromarray(img_array)
                        except ImportError:
                            pass
        except Exception:
            pass
        
        # Fallback to numpy array
        shape = self.get_input_shape()
        return np.random.rand(*shape).astype(np.float32)
    
    def run_inference(self, input_data: Any) -> Any:
        """Run inference on the model."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        try:
            input_name = self._get_input_name()
            result = self.model.predict({input_name: input_data})
            return result
        except Exception as e:
            raise RuntimeError(f"CoreML inference failed: {e}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.model is not None:
                del self.model
        except Exception:
            pass
        
        self.model = None
        self._spec = None
