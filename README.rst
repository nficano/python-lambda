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

The *Python-Lambda* library takes away the guest work of developing your Python-Lambda microservices by providing you tools to streamline the annoying parts.

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

From your ``my_microservice`` directory, run the following to bootstrap your project.

.. code:: bash

    (my_microservice) $ lambda init

If you look at the directory you will see four files were created: ``event.json``, ``__init__.py``, ``service.py``, and ``config.yaml``.

Let's begin by taking a look at ``config.yaml`` in your favorite text editor. For the purpose of this tutorial, the only thing required to be entered is ``aws_access_key_id`` and ``aws_secret_access_key``. You can find these by logging into the AWS management console.

Next let's open ``service.py``, in it you'll find the following function:

.. code:: python

    def handler(event, context):
        # You code goes here!
        e = event.get('e')
        pi = event.get('pi')
        print "your test handler was successfully invoked!"
        return e + pi


This is the hander function; this is what AWS Lambda will invoke in response to an event. You will notice that in the sample code provided ``e`` and ``pi`` are values looked up in a ``dict``. AWS Lambda uses the ``event`` parameter to pass in event data to the handler.

So if for example your function is responding to an http request, ``event`` will be the ``POST`` JSON data and if your function returns something, the contents will be in your http response payload.

Now let's open the ``event.json`` file. Here you'll find the values of ``e`` and ``pi`` that are being referenced in the sample code.

If you now try and run:

.. code:: bash

    (my_microservice) $ lambda invoke

"your test handler was successfully invoked!" should print out in your console.  You've probably already put together that the ``lambda invoke`` command passes the values stored in the ``event.json`` file to your function.

The ``event.json`` file should help you develop your Lambda service locally.

When you're ready to deploy your code to lambda simply run:

.. code:: bash

    (my_microservice) $ lambda deploy

The deploy script will evaluate your virtualenv and identify your project dependencies (actually just pip freeze). It will package these up along with your handler function to a zip file that it then uploads to AWS Lambda.

You can now log into the AWS Lambda management console to verify the code deployed successfully and wire it up to respond to an event.
