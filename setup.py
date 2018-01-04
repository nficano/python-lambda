#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pip
import sys
from setuptools import find_packages
from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

requirements = pip.req.parse_requirements(
    'requirements.txt', session=pip.download.PipSession(),
)

# Only install futures package if using a Python version <= 2.7
if sys.version_info[0] == 2:
    pip_requirements = [str(r.req) for r in requirements]
else:
    pip_requirements = [str(r.req) for r in requirements if 'futures' not in str(r.req)]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='python-lambda',
    version='3.0.0',
    description='The bare minimum for a Python app running on Amazon Lambda.',
    long_description=readme,
    author='Nick Ficano',
    author_email='nficano@gmail.com',
    url='https://github.com/nficano/python-lambda',
    packages=find_packages(),
    package_data={
        'aws_lambda': ['project_templates/*'],
        '': ['*.json'],
    },
    include_package_data=True,
    scripts=['scripts/lambda'],
    install_requires=pip_requirements,
    license='ISCL',
    zip_safe=False,
    keywords='python-lambda',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_requirements,
)
