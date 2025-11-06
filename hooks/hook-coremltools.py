"""
PyInstaller hook for coremltools
Ensures native libraries are properly bundled
"""

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

# Collect all submodules
hiddenimports = collect_submodules('coremltools')

# Collect dynamic libraries (.so, .dylib)
binaries = collect_dynamic_libs('coremltools')

# Collect data files if needed
datas = []
