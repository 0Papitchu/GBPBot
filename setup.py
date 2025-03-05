#!/usr/bin/env python
"""
Setup script for the GBP Bot package.
"""

from setuptools import setup, find_packages

# Read the long description from README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Core dependencies required for basic functionality
CORE_REQUIREMENTS = [
    "aiohttp>=3.8.0",
    "pydantic>=1.9.0",
    "python-dotenv>=0.19.0",
    "PyYAML>=6.0",
]

# Optional dependencies for specific blockchains
ETHEREUM_REQUIREMENTS = [
    "web3>=5.30.0",
    "eth-account>=0.5.9",
    "eth-typing>=3.0.0",
]

SOLANA_REQUIREMENTS = [
    "solana>=0.30.0",
    "solders>=0.18.0",
    "anchorpy>=0.18.0",
]

# Development dependencies
DEV_REQUIREMENTS = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.18.0",
    "black>=22.1.0",
    "isort>=5.10.0",
    "mypy>=0.931",
    "flake8>=4.0.0",
]

# All optional dependencies
EXTRAS = {
    "ethereum": ETHEREUM_REQUIREMENTS,
    "solana": SOLANA_REQUIREMENTS,
    "dev": DEV_REQUIREMENTS,
    "all": ETHEREUM_REQUIREMENTS + SOLANA_REQUIREMENTS,
    "full": ETHEREUM_REQUIREMENTS + SOLANA_REQUIREMENTS + DEV_REQUIREMENTS,
}

setup(
    name="gbpbot",
    version="0.1.0",
    author="GBP Bot Team",
    author_email="contact@example.com",
    description="A flexible and extensible blockchain client interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gbpbot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=CORE_REQUIREMENTS,
    extras_require=EXTRAS,
    entry_points={
        "console_scripts": [
            "gbpbot=gbpbot.main:main",
        ],
    },
) 