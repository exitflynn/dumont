import platform
import psutil
import sys
import uuid
import subprocess
from typing import Dict, Optional


def get_device_udid() -> str:
    """
    Get unique device identifier (UDID).
    
    For macOS: Uses hardware UUID
    For Linux: Uses machine ID or generates from hostname
    For Windows: Uses UUID from registry or generates
    
    Returns:
        Unique device identifier string
    """
    system = platform.system()
    
    # macOS: Get hardware UUID
    if system == "Darwin":
        try:
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Hardware UUID' in line:
                        udid = line.split(':')[-1].strip()
                        if udid:
                            return udid
        except:
            pass
        
        # Fallback: Try ioreg
        try:
            result = subprocess.run(
                ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and 'IOPlatformUUID' in result.stdout:
                for line in result.stdout.split('\n'):
                    if 'IOPlatformUUID' in line:
                        udid = line.split('=')[-1].strip().strip('"')
                        if udid:
                            return udid
        except:
            pass
    
    # Linux: Get machine ID
    elif system == "Linux":
        try:
            with open('/etc/machine-id', 'r') as f:
                udid = f.read().strip()
                if udid:
                    return udid
        except:
            pass
    
    try:
        hostname = platform.node()
        mac_address = uuid.getnode()
        udid = f"{hostname}_{mac_address}"
        return udid
    except:
        pass
    
    return str(uuid.uuid4())


def get_device_info() -> Dict[str, Optional[str]]:
    system = platform.system()
    os_version = platform.version()
    
    processor = platform.processor()
    
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    
    cpu_info = processor
    if hasattr(platform, 'mac_ver'):
        # macOS
        try:
            import subprocess
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                cpu_info = result.stdout.strip()
        except Exception as e:
            print(f"Failed to get CPU brand: {e}")
            pass
    
    discrete_gpu = None
    vram = None
    
    if system == "Darwin":
        try:
            import subprocess
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and "Chipset Model" in result.stdout:
                # Extract GPU info if available
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if "Chipset Model" in line:
                        discrete_gpu = line.split(':')[-1].strip() if ':' in line else None
                        break
        except Exception as e:
            print(f"[DEBUG] Failed to get GPU info: {e}")
            pass
    
    # Device name (hostname)
    device_name = platform.node()
    
    # Try to get model name on macOS
    if system == "Darwin":
        try:
            import subprocess
            result = subprocess.run(['sysctl', '-n', 'hw.model'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                device_name = result.stdout.strip()
        except Exception as e:
            print(f"[DEBUG] Failed to get device model: {e}")
            pass
    
    # Device year (not easily detectable, will be None)
    device_year = None
    
    # Get device UDID
    device_udid = get_device_udid()
    
    return {
        'DeviceName': device_name,
        'DeviceYear': device_year,
        'Soc': cpu_info,
        'Ram': str(int((ram_gb))),
        'DiscreteGpu': discrete_gpu,
        'VRam': vram,
        'DeviceOs': system,
        'DeviceOsVersion': os_version,
        'UDID': device_udid,
    }


def get_compute_units() -> list:
    """
    Get available compute units and inference engines for this device.
    
    Returns:
        List of available compute unit strings in format: "COMPUTE_UNIT (INFERENCE_ENGINE)"
        Examples: ['CPU (ONNX)', 'Neural Engine (CoreML)', 'GPU (ONNX)']
    """
    units = []
    system = platform.system()
    
    # Check ONNX Runtime availability and providers
    try:
        import onnxruntime as ort
        available_providers = ort.get_available_providers()
        
        # CPU is always available via ONNX
        units.append('CPU (ONNX)')
        
        # Check for CUDA GPU support
        if 'CUDAExecutionProvider' in available_providers:
            units.append('GPU (ONNX)')
        
        # Check for Windows DML
        if 'DmlExecutionProvider' in available_providers:
            units.append('DirectML (ONNX)')
        
        # Check for OpenVINO
        if 'OpenVINOExecutionProvider' in available_providers:
            units.append('OpenVINO (ONNX)')
    
    except ImportError:
        # ONNX Runtime not available, add CPU as fallback
        units.append('CPU')
    
    # Check for CoreML and Apple Silicon on macOS
    if system == "Darwin":
        try:
            import coremltools
            
            # Check for Apple Silicon
            try:
                result = subprocess.run(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    capture_output=True, text=True, timeout=2
                )
                cpu_info = result.stdout.strip() if result.returncode == 0 else ""
                
                # Apple Silicon detection
                if 'Apple' in cpu_info:
                    # GPU (via Metal)
                    if 'GPU (CoreML)' not in units:
                        units.append('GPU (CoreML)')
                    
                    # Neural Engine
                    if 'Neural Engine (CoreML)' not in units:
                        units.append('Neural Engine (CoreML)')
            except Exception:
                pass
        
        except ImportError:
            pass
    
    return units

