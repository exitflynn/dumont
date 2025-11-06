# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CycleOPS Worker
This creates a single-file executable with all dependencies bundled.
"""

import sys
import platform

# Detect platform
IS_MACOS = platform.system() == 'Darwin'
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

# Hidden imports - modules not detected by PyInstaller
hiddenimports = [
    # Worker modules
    'worker',
    'worker.cli',
    'worker.worker_agent',
    'worker.legacy',
    'worker.legacy.benchmark',
    'worker.legacy.model_loader',
    'worker.legacy.device_info',
    
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
    
    # Third-party dependencies
    'psutil',
    'numpy',
    'numpy.core',
    'requests',
    'redis',
    'onnxruntime',
    'onnxruntime.capi',
]

# Platform-specific imports
if IS_MACOS:
    hiddenimports.extend([
        'coremltools',
        'coremltools.models',
        'coremltools.models.model',
        'coremltools.libcoremlpython',
        'coremltools.libmilstoragepython',
        'PIL',
        'PIL.Image',
    ])

if IS_WINDOWS:
    hiddenimports.extend([
        'onnxruntime.providers.dml',
    ])

# Data files to include
datas = []

# Binaries - include CoreML native libraries on macOS
binaries = []

if IS_MACOS:
    try:
        # Find coremltools and include its native libraries
        import coremltools
        from pathlib import Path
        
        coremltools_path = Path(coremltools.__file__).parent
        
        # Add all .so and .dylib files from coremltools
        for lib_file in coremltools_path.rglob('*.so'):
            binaries.append((str(lib_file), str(lib_file.parent.relative_to(coremltools_path.parent))))
        
        for lib_file in coremltools_path.rglob('*.dylib'):
            binaries.append((str(lib_file), str(lib_file.parent.relative_to(coremltools_path.parent))))
        
        print(f"Found {len(binaries)} CoreML native libraries")
    except ImportError:
        print("CoreML not available, skipping native library collection")

a = Analysis(
    ['worker/cli.py'],
    pathex=['.', 'worker', 'core'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],  # Add custom hooks directory
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # Exclude if not needed
        'tkinter',     # Exclude GUI
        'pytest',      # Exclude test framework
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
    console=True,  # Console application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add .ico file here if you have one
)
