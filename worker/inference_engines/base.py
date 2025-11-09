"""
Base class for inference engines.
All inference engines should inherit from this and implement required methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any, List
import numpy as np


class InferenceEngine(ABC):
    """
    Abstract base class for inference engines.
    
    Each inference engine (ONNX, CoreML, TensorFlow Lite, etc.) should inherit
    from this class and implement the required methods.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the inference engine (e.g., 'ONNX', 'CoreML')"""
        pass
    
    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """List of supported model file extensions (e.g., ['.onnx'])"""
        pass
    
    @abstractmethod
    def load_model(self, model_path: str) -> None:
        """
        Load a model from file.
        
        Args:
            model_path: Path to the model file
            
        Raises:
            RuntimeError: If model cannot be loaded
        """
        pass
    
    @abstractmethod
    def get_input_shape(self) -> Tuple:
        """
        Get the input shape of the model.
        
        Returns:
            Tuple representing input shape
        """
        pass
    
    @abstractmethod
    def create_sample_input(self) -> Any:
        """
        Create a sample input for the model.
        
        Returns:
            Sample input (numpy array, PIL Image, or engine-specific format)
        """
        pass
    
    @abstractmethod
    def run_inference(self, input_data: Any) -> Any:
        """
        Run inference on the model.
        
        Args:
            input_data: Input data in the format expected by the engine
            
        Returns:
            Inference output
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up resources used by the engine.
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the engine is available on this system.
        
        Returns:
            True if the engine can be used, False otherwise
        """
        pass
