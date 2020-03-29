#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

from setuptools import find_packages
from setuptools import setup

with open("README.md") as readme_file:
    readme = readme_file.read()

requirements = [
    "boto3",
    "click",
    "PyYAML",
]

# Only install futures package if using a Python version <= 2.7
if sys.version_info < (3, 0):
    requirements.append("futures")

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name="python-lambda",
    version="5.0.0",
    description="The bare minimum for a Python app running on Amazon Lambda.",
    long_description=readme,
    author="Nick Ficano",
    author_email="nficano@gmail.com",
    url="https://github.com/nficano/python-lambda",
    packages=find_packages(),
    package_data={
        "aws_lambda": ["project_templates/*"],
        "": ["*.json"],
    },  # noqa
    include_package_data=True,
    scripts=["scripts/lambda"],
    install_requires=requirements,
    license="ISCL",
    zip_safe=False,
    keywords="python-lambda",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    test_suite="tests",
    tests_require=test_requirements,
)
