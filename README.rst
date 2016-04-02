========
python-λ
========

.. image:: https://img.shields.io/pypi/v/python-lambda.svg
  :alt: Pypi
  :target: https://pypi.python.org/pypi/python-lambda/

.. image:: https://img.shields.io/pypi/dm/python-lambda.svg
  :alt: Pypi downloads per month
  :target: https://pypi.python.org/pypi/python-lambda/

.. image:: https://img.shields.io/pypi/pyversions/python-lambda.svg
  :alt: Python Versions
  :target: https://pypi.python.org/pypi/python-lambda/

Python-lambda is everything you need to start developing your own microservices
using AWS Lambda.

Description
===========

AWS Lambda is a service that allows you to write Python, Java, or Node.js code that gets executed in response to events like http requests or files uploaded to S3.

Working with Lambda is relatively easy, but the process of bundling and deploying your code is not as simple as it could be.

The *Python-Lambda* library takes away the guest work of developing your Lambda microservices by providing you tools to streamline the annoying parts.

Requirements
============

* Python 2.7 (At the time of writing this, AWS Lambda only supports Python 2.7).
* Pip (~8.1.1)
* Virtualenv (~15.0.0)
* Virtualenvwrapper (~4.7.1)

Installation
============

Create a new folder for your project and create a virtualenv.

.. code:: bash

    $ mkdir my_microservice
    $ mkvirtualenv my_microservice

Next Download using pip via pypi.

.. code:: bash

    (my_microservice) $ pip install python-lambda

Getting Started
===============

The following will walk you through writing your first microservice with *Python-lambda*.
