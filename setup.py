"""
Setup script for the QA Documentation Generator.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="qa-doc-generator",
    version="1.0.0",
    author="Your Organization",
    author_email="your.email@example.com",
    description="AI-Powered QA Documentation Generator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/qa-doc-generator",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "qa-doc-generator=src.main:main",
        ],
    },
) 