from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dialogchain",
    version="0.1.4",  # Incremented version
    description="DialogChain - A flexible and extensible dialog processing framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "aiohttp>=3.8.0",
        "aiofiles>=23.2.1",  # Added aiofiles
        "asyncio-mqtt>=0.13.0",
        "grpcio>=1.50.0",
        "grpcio-tools>=1.50.0",
        "jinja2>=3.1.0",
    ],
    extras_require={
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mqtt>=0.5.0",
            "pytest-httpbin>=2.0.0",
            "pytest-asyncio>=0.20.0",
            "pytest-mock>=3.10.0",
            "testinfra>=6.0.0",
            "molecule>=3.5.0",
            "molecule-plugins[docker]>=21.5.0",
        ],
        "dev": [
            "black>=22.0.0",
            "isort>=5.10.0",
            "mypy>=0.910",
            "flake8>=4.0.0",
            "pylint>=2.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dialogchain=dialogchain.cli:main",
        ],
    },
    python_requires=">=3.8.1,<3.12",
    include_package_data=True,
    package_data={
        "dialogchain": ["py.typed"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
