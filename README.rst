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

Python-lambda is a toolset for developing and deploying *serverless* Python code in AWS Lambda.

Description
===========

AWS Lambda is a service that allows you to write Python, Java, or Node.js code that gets executed in response to events like http requests or files uploaded to S3.

Working with Lambda is relatively easy, but the process of bundling and deploying your code is not as simple as it could be.

The *Python-Lambda* library takes away the guest work of developing your Python-Lambda services by providing you a toolset to streamline the annoying parts.

Requirements
============

* Python 2.7 (At the time of writing this, AWS Lambda only supports Python 2.7).
* Pip (~8.1.1)
* Virtualenv (~15.0.0)
* Virtualenvwrapper (~4.7.1)

Getting Started
===============

Begin by creating a new virtualenv and project folder.

.. code:: bash

    $ mkvirtualenv lambduh
    (lambduh) $ mkdir lambduh

Next, download *Python-Lambda* using pip via pypi.

.. code:: bash

    (lambduh) $ pip install python-lambda

From your ``lambduh`` directory, run the following to bootstrap your project.

.. code:: bash

    (lambduh) $ lambda init

This will create the following files: ``event.json``, ``__init__.py``, ``service.py``, and ``config.yaml``.

Let's begin by opening ``config.yaml`` in the text editor of your choice. For the purpose of this tutorial, the only required information is ``aws_access_key_id`` and ``aws_secret_access_key``. You can find these by logging into the AWS management console.

Next let's open ``service.py``, in here you'll find the following function:

.. code:: python

    def handler(event, context):
        # You code goes here!
        e = event.get('e')
        pi = event.get('pi')
        return e + pi


This is the handler function; this is the function AWS Lambda will invoke in response to an event. You will notice that in the sample code ``e`` and ``pi`` are values in a ``dict``. AWS Lambda uses the ``event`` parameter to pass in event data to the handler.

So if for example your function is responding to an http request, ``event`` will be the ``POST`` JSON data and if your function returns something, the contents will be in your http response payload.

Next let's open the ``event.json`` file. Here you'll find the values of ``e`` and ``pi`` that are being referenced in the sample code.

If you now try and run:

.. code:: bash

    (lambduh) $ lambda invoke -v
    # 5.858

    # execution time: 0.00000310s
    # function execution timeout: 15s

As you probably put together, the ``lambda invoke`` command grabs the values stored in the ``event.json`` file and passes them to your function.

The ``event.json`` file should help you develop your Lambda service locally. You can specify an alternate ``event.json`` file by passing the ``--event-file=<filename>.json`` argument to ``lambda invoke``.

When you're ready to deploy your code to Lambda simply run:

.. code:: bash

    (lambduh) $ lambda deploy

The deploy script will evaluate your virtualenv and identify your project dependencies. It will package these up along with your handler function to a zip file that it then uploads to AWS Lambda.

You can now log into the `AWS Lambda management console <https://console.aws.amazon.com/lambda/>`_ to verify the code deployed successfully.

Wiring to an API endpoint
=========================

If you're looking to develop a simple microservice you can easily wire your function up to an http endpoint.

Begin by navigating to your `AWS Lambda management console <https://console.aws.amazon.com/lambda/>`_ and clicking on your function. Click the API Endpoints tab and click "Add API endpoint".

Under API endpoint type select "API Gateway".

Next change Method to ``POST`` and Security to "Open" and click submit (NOTE: you should secure this for use in production, open security is use for demo purposes).

Now try and run:

.. code:: bash

    $ curl -H "Content-Type: application/json" -X POST -d '{"pi": 3.14, "e": 2.718}' https://<API endpoint URL>
    # 5.8580000000000005
