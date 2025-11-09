"""
Dumont - Setup Configuration
Packaging configuration for worker agent distribution.
"""

from setuptools import setup, find_packages

# Read version
version = "1.0.0"

# Base requirements (cross-platform)
base_requirements = [
    "psutil>=5.9.0",
    "numpy>=1.24.0,<2.0",
    "requests>=2.31.0",
    "redis>=5.0.0",
]

# Platform-specific requirements
macos_requirements = [
    "coremltools>=8.0,<9.0",
    "Pillow>=10.0.0",
]

windows_requirements = [
    "onnxruntime-directml>=1.16.0",  # DirectML for Windows GPU
]

# Universal ONNX (always include)
universal_requirements = [
    "onnxruntime>=1.16.0",
]

setup(
    name="cyclops-worker",
    version=version,
    description="sark Distributed Benchmarking Worker Agent",
    long_description_content_type="text/markdown",
    author="exitflynn and AI",
    url="https://github.com/exitflynn/dumont",
    
    # Package discovery
    packages=find_packages(include=['worker', 'worker.*', 'core']),
    
    # Include non-Python files
    include_package_data=True,
    package_data={
        '': ['*.json', '*.md'],
    },
    
    # Dependencies
    install_requires=base_requirements + universal_requirements,
    
    # Optional platform-specific dependencies
    extras_require={
        'macos': macos_requirements,
        'windows': windows_requirements,
        'dev': [
            'pytest>=7.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
        ],
    },
    
    # Python version requirement
    python_requires='>=3.8',
    
    # Entry points - creates CLI commands
    entry_points={
        'console_scripts': [
            'cyclops-worker=worker.cli:main',
        ],
    },
    
    # Classification
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Benchmark",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
)
