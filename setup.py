#!/usr/bin/env python
"""Bootstrapper for docker's ENTRYPOINT executable.

Since using setup.py is no longer std convention,
all install information is located in pyproject.toml
"""
import setuptools

# needed to install a blank pkg & redirect to newer pkg on PyPI
setuptools.setup(
    name="cpp-linter-deprecated",
    version="0.0.0",
    install_requires=["cpp-linter==1.4.9"],
    py_modules=[""],
)
