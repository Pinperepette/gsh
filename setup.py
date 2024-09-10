#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="gsh",
    version="0.2",
    author="pinperepette",
    author_email="pinperepette@gmail.com",
    description="A GPT-powered shell assistant for executing commands and suggesting code.",
    packages=find_packages(),
    install_requires=[
        "openai",
        "rich",
        "cryptography",
    ],
    entry_points={
        'console_scripts': [
            'gsh=gsh.main:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
