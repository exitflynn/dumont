# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CycleOPS Worker - Linux (ONNX with CPU/CUDA support)
This creates a binary with ONNX Runtime support for CPU and optionally GPU.
"""

import sys
import platform

# Hidden imports - modules not detected by PyInstaller
hiddenimports = [
    # Worker modules
    'worker',
    'worker.cli',
    'worker.worker_agent',
    'worker.benchmark',
    'worker.model_loader',
    'worker.device_info',
    
    # Core modules
    'core',
    'core.redis_client',
    'core.job_dispatcher',
    
    # Standard library
    'json',
    'threading',
    'logging',
    'argparse',
    'importlib',
    'socket',
    'uuid',
    'time',
    'pathlib',
    'urllib',
    'urllib.parse',
    
    # Third-party dependencies
    'psutil',
    'numpy',
    'numpy.core',
    'requests',
    'redis',
    'onnxruntime',
    'onnxruntime.capi',
]

# NOTE: Excluding CoreML due to native binding issues with PyInstaller
# Use Python package distribution for CoreML support

# Data files to include
datas = []

# Binaries
binaries = []

a = Analysis(
    ['worker/cli.py'],
    pathex=['.', 'worker', 'core'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],  # No custom hooks needed for ONNX-only
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'coremltools',     # Exclude CoreML (won't work in binary anyway)
        'PIL',             # Not needed for ONNX
        'matplotlib',
        'tkinter',
        'pytest',
        'torch',           # Exclude PyTorch
        'tensorflow',      # Exclude TensorFlow
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='cyclops-worker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
