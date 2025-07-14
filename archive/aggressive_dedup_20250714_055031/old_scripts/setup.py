"""
Editorial Assistant - Professional Journal Referee Management System
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="editorial-assistant",
    version="1.0.0",
    author="Editorial Assistant Team",
    description="Professional system for managing journal referee extractions and analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/editorial-assistant",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "selenium>=4.0.0",
        "undetected-chromedriver>=3.5.0",
        "beautifulsoup4>=4.12.0",
        "requests>=2.31.0",
        "pydantic>=2.0.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "google-api-python-client>=2.100.0",
        "google-auth-httplib2>=0.1.0",
        "google-auth-oauthlib>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "sphinx>=6.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "editorial-assistant=editorial_assistant.cli.main:cli",
            "ea=editorial_assistant.cli.main:cli",  # Short alias
        ],
    },
    include_package_data=True,
    package_data={
        "editorial_assistant": ["config/*.yaml", "config/*.example"],
    },
)