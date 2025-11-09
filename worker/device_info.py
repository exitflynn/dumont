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
    
    device_name = platform.node()
    
    if system == "Darwin":
        try:
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                model_name = None
                model_id = None
                
                for line in lines:
                    if 'Model Name:' in line:
                        model_name = line.split(':', 1)[-1].strip()
                    elif 'Model Identifier:' in line:
                        model_id = line.split(':', 1)[-1].strip()
                
                if model_name and model_id:
                    device_name = f"{model_name} ({model_id})"
                elif model_name:
                    device_name = model_name
        except Exception as e:
            pass
    
    elif system == "Linux":
        try:
            board_name = None
            board_vendor = None
            
            try:
                with open('/sys/devices/virtual/dmi/id/board_name', 'r') as f:
                    board_name = f.read().strip()
            except:
                pass
            
            try:
                with open('/sys/devices/virtual/dmi/id/sys_vendor', 'r') as f:
                    board_vendor = f.read().strip()
            except:
                pass
            
            if board_name and board_vendor:
                device_name = f"{board_vendor} {board_name}"
            elif board_name:
                device_name = board_name
            elif board_vendor:
                device_name = board_vendor
        except Exception as e:
            print(f"[DEBUG] Failed to get Linux device model: {e}")
    
    elif system == "Windows":
        # Windows: Try wmic first, then fallback to hostname_mac
        wmic_success = False
        
        try:
            result = subprocess.run(
                ['wmic', 'computersystem', 'get', 'model'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                print(f"[DEBUG] wmic output lines: {lines}")
                # skip header and empty lines, find first non-empty model name (inconsistent wmic behaviour)
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    print(f"[DEBUG] Line {i}: '{stripped}'")
                    if stripped and i > 0 and stripped != 'Model':
                        device_name = stripped
                        print(f"[DEBUG] Successfully set device_name from wmic line {i}: '{device_name}'")
                        wmic_success = True
                        break
                if not wmic_success:
                    print(f"[DEBUG] wmic returned no valid model name in lines")
        except Exception as e:
            print(f"[DEBUG] Exception during wmic: {type(e).__name__}: {e}")
        
        if not wmic_success:
            try:
                hostname = platform.node()
                mac_address = uuid.getnode()
                fallback_name = f"{hostname}_{mac_address}"
                print(f"[DEBUG] fallback_name: '{fallback_name}'")
                if fallback_name and fallback_name != "_0":
                    device_name = fallback_name
                else:
                    print(f"[DEBUG] Fallback produced invalid name: '{fallback_name}'")
            except Exception as e:
                print(f"[DEBUG] Exception during fallback: {type(e).__name__}: {e}")
    
    # Device year (not easily detectable, will be None)
    device_year = None
    
    # Get device UDID
    device_udid = get_device_udid()
    
    # Safety check: ensure device_name is never empty
    if not device_name or device_name.strip() == "":
        print(f"[DEBUG] WARNING: device_name is empty after all detection methods, using fallback")
        try:
            hostname = platform.node()
            mac_address = uuid.getnode()
            device_name = f"{hostname}_{mac_address}"
            print(f"[DEBUG] Safety fallback set device_name to: '{device_name}'")
        except Exception as e:
            device_name = f"unknown_{uuid.uuid4()}"
            print(f"[DEBUG] Safety fallback exception, using UUID: '{device_name}'")
    
    print(f"[DEBUG] get_device_info() returning device_name: '{device_name}'")
    
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
    
    try:
        import onnxruntime as ort
        available_providers = ort.get_available_providers()
        
        units.append('CPU (ONNX)')
        
        if 'CUDAExecutionProvider' in available_providers:
            units.append('GPU (ONNX)')
        
        if 'DmlExecutionProvider' in available_providers:
            units.append('DirectML (ONNX)')
        
        if 'OpenVINOExecutionProvider' in available_providers:
            units.append('OpenVINO (ONNX)')
    
    except ImportError:
        units.append('CPU')
    
    if system == "Darwin":
        try:
            import coremltools
            
            try:
                result = subprocess.run(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    capture_output=True, text=True, timeout=2
                )
                cpu_info = result.stdout.strip() if result.returncode == 0 else ""
                
                if 'Apple' in cpu_info:
                    if 'GPU (CoreML)' not in units:
                        units.append('GPU (CoreML)')
                    
                    if 'Neural Engine (CoreML)' not in units:
                        units.append('Neural Engine (CoreML)')
            except Exception:
                pass
        
        except ImportError:
            pass
    
    return units

