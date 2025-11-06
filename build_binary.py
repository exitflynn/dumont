#!/usr/bin/env python3
"""
Build script for creating CycleOPS Worker standalone binaries.
Supports macOS, Windows, and Linux.
"""

import sys
import os
import platform
import subprocess
import shutil
from pathlib import Path


def print_section(text):
    """Print formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def run_command(cmd, shell=False):
    """Run command and return success status."""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            check=True,
            capture_output=True,
            text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def main():
    """Main build process."""
    print_section("CycleOPS Worker - Binary Builder")
    
    # Detect platform
    system = platform.system()
    machine = platform.machine()
    
    print(f"Platform: {system} {machine}")
    print(f"Python: {platform.python_version()}")
    
    # Check PyInstaller
    print("\n▶ Checking PyInstaller...")
    success, _ = run_command([sys.executable, "-m", "pip", "show", "pyinstaller"])
    if not success:
        print("  Installing PyInstaller...")
        success, _ = run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])
        if not success:
            print("  ✗ Failed to install PyInstaller")
            return 1
    print("  ✓ PyInstaller available")
    
    # Clean previous builds
    print("\n▶ Cleaning previous builds...")
    for path in ['build', 'dist_binary']:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"  ✓ Removed {path}/")
    
    # Build PyInstaller spec
    print("\n▶ Building binary...")
    
    # Platform-specific options
    binary_name = "cyclops-worker"
    if system == "Windows":
        binary_name = "cyclops-worker.exe"
    
    # PyInstaller command
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "cyclops-worker",
        "--onefile",  # Single executable
        "--console",  # Console application
        "--clean",
        
        # Add all necessary modules
        "--hidden-import", "worker",
        "--hidden-import", "worker.worker_agent",
        "--hidden-import", "worker.legacy.benchmark",
        "--hidden-import", "worker.legacy.model_loader",
        "--hidden-import", "worker.legacy.device_info",
        "--hidden-import", "core.redis_client",
        "--hidden-import", "core.job_dispatcher",
        
        # Hidden imports for dependencies
        "--hidden-import", "psutil",
        "--hidden-import", "numpy",
        "--hidden-import", "requests",
        "--hidden-import", "redis",
        "--hidden-import", "onnxruntime",
    ]
    
    # Platform-specific hidden imports
    if system == "Darwin":
        pyinstaller_args.extend([
            "--hidden-import", "coremltools",
            "--hidden-import", "PIL",
        ])
    
    # Add paths
    pyinstaller_args.extend([
        "--paths", str(Path.cwd()),
        "--paths", str(Path.cwd() / "worker"),
        "--paths", str(Path.cwd() / "core"),
    ])
    
    # Entry point
    pyinstaller_args.append("worker/cli.py")
    
    print(f"  Running: pyinstaller {' '.join(pyinstaller_args[3:])}")
    success, output = run_command(pyinstaller_args)
    
    if not success:
        print(f"  ✗ Build failed: {output}")
        return 1
    
    print("  ✓ Binary built successfully")
    
    # Move to dist_binary
    print("\n▶ Organizing output...")
    dist_binary = Path("dist_binary")
    dist_binary.mkdir(exist_ok=True)
    
    binary_path = Path("dist") / binary_name
    if binary_path.exists():
        target_path = dist_binary / binary_name
        shutil.copy2(binary_path, target_path)
        print(f"  ✓ Binary: {target_path}")
        
        # Get size
        size_mb = target_path.stat().st_size / (1024 * 1024)
        print(f"  ✓ Size: {size_mb:.1f} MB")
    else:
        print(f"  ✗ Binary not found at {binary_path}")
        return 1
    
    # Test the binary
    print("\n▶ Testing binary...")
    test_args = [str(target_path), "--help"]
    success, output = run_command(test_args)
    
    if success:
        print("  ✓ Binary is executable")
    else:
        print("  ⚠ Warning: Binary test failed")
    
    # Success
    print_section("Build Complete!")
    print(f"Binary location: {target_path.absolute()}")
    print(f"\nTo test:")
    print(f"  {target_path} info")
    print(f"  {target_path} validate")
    print(f"\nTo distribute:")
    print(f"  Just copy the '{binary_name}' file to target machines!")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
