#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    "boto3==1.3.0",
    "click==6.4",
    "PyYAML==3.11",
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='python-aws-lambda',
    version='0.1.0',
    description="The bare minimum for a Python app running on Amazon Lambda.",
    long_description=readme + '\n\n' + history,
    author="Nick Ficano",
    author_email='nficano@gmail.com',
    url='https://github.com/nficano/python-lambda',
    packages=[
        'aws_lambda',
    ],
    package_dir={
        'aws_lambda': 'aws_lambda'
    },
    package_data={'aws_lambda': ['templates/*']},
    scripts=['scripts/lambda'],
    include_package_data=True,
    install_requires=requirements,
    license="ISCL",
    zip_safe=False,
    keywords='python-lambda',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
