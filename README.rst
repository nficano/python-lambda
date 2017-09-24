========
python-λ
========

.. image:: https://img.shields.io/pypi/v/python-lambda.svg
  :alt: Pypi
  :target: https://pypi.python.org/pypi/python-lambda/

.. image:: https://img.shields.io/pypi/pyversions/python-lambda.svg
  :alt: Python Versions
  :target: https://pypi.python.org/pypi/python-lambda/

Python-lambda is a toolset for developing and deploying *serverless* Python code in AWS Lambda.

A call for contributors
=======================
With python-lambda and `pytube <https://github.com/nficano/pytube/>`_ both continuing to gain momentum, I'm calling for contributors to help build out new features, review pull requests, fix bugs, and maintain overall code quality. If you're interested, please email me at nficano[at]gmail.com.

Description
===========

AWS Lambda is a service that allows you to write Python, Java, or Node.js code that gets executed in response to events like http requests or files uploaded to S3.

Working with Lambda is relatively easy, but the process of bundling and deploying your code is not as simple as it could be.

The *Python-Lambda* library takes away the guess work of developing your Python-Lambda services by providing you a toolset to streamline the annoying parts.

Requirements
============

* Python 2.7 & 3.6 (At the time of writing this, AWS Lambda only supports Python 2.7/3.6).
* Pip (~8.1.1)
* Virtualenv (~15.0.0)
* Virtualenvwrapper (~4.7.1)

Getting Started
===============

First, you must create an IAM Role on your AWS account called `lambda_basic_execution` with the `LambdaBasicExecution` policy attached.

On your computer, create a new virtualenv and project folder.

.. code:: bash

    $ mkvirtualenv pylambda
    (pylambda) $ mkdir pylambda

Next, download *Python-Lambda* using pip via pypi.

.. code:: bash

    (pylambda) $ pip install python-lambda

From your ``pylambda`` directory, run the following to bootstrap your project.

.. code:: bash

    (pylambda) $ lambda init

This will create the following files: ``event.json``, ``__init__.py``, ``service.py``, and ``config.yaml``.

Let's begin by opening ``config.yaml`` in the text editor of your choice. For the purpose of this tutorial, the only required information is ``aws_access_key_id`` and ``aws_secret_access_key``. You can find these by logging into the AWS management console.

Next let's open ``service.py``, in here you'll find the following function:

.. code:: python

    def handler(event, context):
        # Your code goes here!
        e = event.get('e')
        pi = event.get('pi')
        return e + pi


This is the handler function; this is the function AWS Lambda will invoke in response to an event. You will notice that in the sample code ``e`` and ``pi`` are values in a ``dict``. AWS Lambda uses the ``event`` parameter to pass in event data to the handler.

So if, for example, your function is responding to an http request, ``event`` will be the ``POST`` JSON data and if your function returns something, the contents will be in your http response payload.

Next let's open the ``event.json`` file:

.. code:: json

    {
      "pi": 3.14,
      "e": 2.718
    }

Here you'll find the values of ``e`` and ``pi`` that are being referenced in the sample code.

If you now try and run:

.. code:: bash

    (pylambda) $ lambda invoke -v

You will get:

.. code:: bash

    # 5.858

    # execution time: 0.00000310s
    # function execution timeout: 15s

As you probably put together, the ``lambda invoke`` command grabs the values stored in the ``event.json`` file and passes them to your function.

The ``event.json`` file should help you develop your Lambda service locally. You can specify an alternate ``event.json`` file by passing the ``--event-file=<filename>.json`` argument to ``lambda invoke``.

When you're ready to deploy your code to Lambda simply run:

.. code:: bash

    (pylambda) $ lambda deploy

The deploy script will evaluate your virtualenv and identify your project dependencies. It will package these up along with your handler function to a zip file that it then uploads to AWS Lambda.

You can now log into the `AWS Lambda management console <https://console.aws.amazon.com/lambda/>`_ to verify the code deployed successfully.

Wiring to an API endpoint
=========================

If you're looking to develop a simple microservice you can easily wire your function up to an http endpoint.

Begin by navigating to your `AWS Lambda management console <https://console.aws.amazon.com/lambda/>`_ and clicking on your function. Click the API Endpoints tab and click "Add API endpoint".

Under API endpoint type select "API Gateway".

Next change Method to ``POST`` and Security to "Open" and click submit (NOTE: you should secure this for use in production, open security is used for demo purposes).

At last you need to change the return value of the function to comply with the standard defined for the API Gateway endpoint, the function should now look like this:

.. code:: python

    def handler(event, context):
        # Your code goes here!
        e = event.get('e')
        pi = event.get('pi')
        return {
            "statusCode": 200,
            "headers": { "Content-Type": "application/json"},
            "body": e + pi
        }

Now try and run:

.. code:: bash

    $ curl --header "Content-Type:application/json" \
           --request POST \
           --data '{"pi": 3.14, "e": 2.718}' \
           https://<API endpoint URL>
    # 5.8580000000000005

Environment Variables
=====================
Lambda functions support environment variables. In order to set environment variables for your deployed code to use, you can configure them in ``config.yaml``.  To load the
value for the environment variable at the time of deployment (instead of hard coding them in your configuration file), you can use local environment values (see 'env3' in example code below).

.. code:: yaml

  environment_variables:
    env1: foo
    env2: baz
    env3: ${LOCAL_ENVIRONMENT_VARIABLE_NAME}

This would create environment variables in the lambda instance upon deploy. If your functions don't need environment variables, simply leave this section out of your config.

Uploading to S3
===============
You may find that you do not need the toolkit to fully deploy your Lambda or that your code bundle is too large to upload via the API.  You can use the ``upload`` command to send the bundle to an S3 bucket of your choosing.
Before doing this, you will need to set the following variables in ``config.yaml`:

.. code:: yaml

role: basic_s3_upload
bucket_name: 'example-bucket'
s3_key_prefix: 'path/to/file/'

Your role must have ``s3:PutObject`` permission on the bucket/key that you specify for the upload to work properly. Once you have that set, you can execute ``lambda upload`` to initiate the transfer.

Deploying via S3
===============
You can also choose to use S3 as your source for Lambda deployments.  This can be done by issuing ``lambda deploy_s3`` with the same variables/AWS permissions you'd set for executing the ``upload`` command.

Development
===========

Development of this happens on GitHub, patches including tests, documentation are very welcome, as well as bug reports and feature contributions are welcome! Also please open an issue if this tool does not function as you'd expect.

How to release updates
----------------------

If this is the first time you're releasing to pypi, you'll need to run: ``pip install -r tests/dev_requirements.txt``.

Once complete, execute the following commands:

.. code:: bash

   $ git checkout master
   $ bumpversion [major|minor|patch]
   $
   $ python setup.py sdist bdist_wheel upload
   $
   $ bumpversion --no-tag patch
   $ git push origin master --tags
