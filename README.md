<div align="center">
  <p>
  <img src="https://assets.nickficano.com/gh-pythonlambda.svg" width="221" height="227" alt="python-lambda logo" />
  </p>
  <p align="center">
	  <img src="https://img.shields.io/pypi/v/python-lambda.svg" alt="pypi" />
    <a href="https://pypi.org/project/python-lambda/"><img src="https://img.shields.io/pypi/dm/python-lambda.svg" alt="pypi"></a>
	  <a href="https://pypi.python.org/pypi/python-lambda/"><img src="https://img.shields.io/pypi/pyversions/python-lambda.svg" /></a>
  </p>
</div>

Python-lambda is a toolset for developing and deploying *serverless* Python code in AWS Lambda.

# A call for contributors
With python-lambda and pytube both continuing to gain momentum, I'm calling for
contributors to help build out new features, review pull requests, fix bugs,
and maintain overall code quality. If you're interested, please email me at
nficano[at]gmail.com.

# Description

AWS Lambda is a service that allows you to write Python, Java, or Node.js code
that gets executed in response to events like http requests or files uploaded
to S3.

Working with Lambda is relatively easy, but the process of bundling and
deploying your code is not as simple as it could be.

The *Python-Lambda* library takes away the guess work of developing your
Python-Lambda services by providing you a toolset to streamline the annoying
parts.

# Requirements

* Python 2.7, >= 3.6 (At the time of writing this, these are the Python runtimes supported by AWS Lambda).
* Pip (\~8.1.1)
* Virtualenv (\~15.0.0)
* Virtualenvwrapper (\~4.7.1)


# Getting Started

First, you must create an IAM Role on your AWS account called
``lambda_basic_execution`` with the ``LambdaBasicExecution`` policy attached.

On your computer, create a new virtualenv and project folder.

```bash
$ mkvirtualenv pylambda
(pylambda) $ mkdir pylambda
```

Next, download *Python-Lambda* using pip via pypi.

```bash
(pylambda) $ pip install python-lambda
```

From your ``pylambda`` directory, run the following to bootstrap your project.

```bash
(pylambda) $ lambda init
```

This will create the following files: ``event.json``, ``__init__.py``,
``service.py``, and ``config.yaml``.

Let's begin by opening ``config.yaml`` in the text editor of your choice. For
the purpose of this tutorial, the only required information is
``aws_access_key_id`` and ``aws_secret_access_key``. You can find these by
logging into the AWS management console.

Next let's open ``service.py``, in here you'll find the following function:

```python
def handler(event, context):
    # Your code goes here!
    e = event.get('e')
    pi = event.get('pi')
    return e + pi
```

This is the handler function; this is the function AWS Lambda will invoke in
response to an event. You will notice that in the sample code ``e`` and ``pi``
are values in a ``dict``. AWS Lambda uses the ``event`` parameter to pass in
event data to the handler.

So if, for example, your function is responding to an http request, ``event``
will be the ``POST`` JSON data and if your function returns something, the
contents will be in your http response payload.

Next let's open the ``event.json`` file:

```json
{
  "pi": 3.14,
  "e": 2.718
}
```
Here you'll find the values of ``e`` and ``pi`` that are being referenced in
the sample code.

If you now try and run:

```bash
(pylambda) $ lambda invoke -v
```

You will get:
```bash
# 5.858
# execution time: 0.00000310s
# function execution timeout: 15s
```

As you probably put together, the ``lambda invoke`` command grabs the values
stored in the ``event.json`` file and passes them to your function.

The ``event.json`` file should help you develop your Lambda service locally.
You can specify an alternate ``event.json`` file by passing the
``--event-file=<filename>.json`` argument to ``lambda invoke``.

When you're ready to deploy your code to Lambda simply run:

```bash
(pylambda) $ lambda deploy
```

The deploy script will evaluate your virtualenv and identify your project
dependencies. It will package these up along with your handler function to a
zip file that it then uploads to AWS Lambda.

You can now log into the
[AWS Lambda management console](https://console.aws.amazon.com/lambda/) to
verify the code deployed successfully.

### Wiring to an API endpoint

If you're looking to develop a simple microservice you can easily wire your
function up to an http endpoint.

Begin by navigating to your [AWS Lambda management console](https://console.aws.amazon.com/lambda/) and
clicking on your function. Click the API Endpoints tab and click "Add API endpoint".

Under API endpoint type select "API Gateway".

Next change Method to ``POST`` and Security to "Open" and click submit (NOTE:
you should secure this for use in production, open security is used for demo
purposes).

At last you need to change the return value of the function to comply with the
standard defined for the API Gateway endpoint, the function should now look
like this:

```
def handler(event, context):
    # Your code goes here!
    e = event.get('e')
    pi = event.get('pi')
    return {
        "statusCode": 200,
        "headers": { "Content-Type": "application/json"},
        "body": e + pi
    }
```

Now try and run:

```bash
$ curl --header "Content-Type:application/json" \
       --request POST \
       --data '{"pi": 3.14, "e": 2.718}' \
       https://<API endpoint URL>
# 5.8580000000000005
```

### Environment Variables
Lambda functions support environment variables. In order to set environment
variables for your deployed code to use, you can configure them in
``config.yaml``.  To load the value for the environment variable at the time of
deployment (instead of hard coding them in your configuration file), you can
use local environment values (see 'env3' in example code below).

```yaml
environment_variables:
  env1: foo
  env2: baz
  env3: ${LOCAL_ENVIRONMENT_VARIABLE_NAME}
```

This would create environment variables in the lambda instance upon deploy. If
your functions don't need environment variables, simply leave this section out
of your config.

### Uploading to S3
You may find that you do not need the toolkit to fully
deploy your Lambda or that your code bundle is too large to upload via the API.
You can use the ``upload`` command to send the bundle to an S3 bucket of your
choosing.  Before doing this, you will need to set the following variables in
``config.yaml``:

```yaml
role: basic_s3_upload
bucket_name: 'example-bucket'
s3_key_prefix: 'path/to/file/'
```
Your role must have ``s3:PutObject`` permission on the bucket/key that you
specify for the upload to work properly. Once you have that set, you can
execute ``lambda upload`` to initiate the transfer.

### Deploying via S3
You can also choose to use S3 as your source for Lambda deployments.  This can
be done by issuing ``lambda deploy_s3`` with the same variables/AWS permissions
you'd set for executing the ``upload`` command.

## Development
Development of "python-lambda" is facilitated exclusively on GitHub.
Contributions in the form of patches, tests and feature creation and/or
requests are very welcome and highly encouraged. Please open an issue if this
tool does not function as you'd expect.

### Environment Setup
1. [Install pipenv](https://github.com/pypa/pipenv)
2. [Install direnv](https://direnv.net/)
3. [Install Precommit](https://pre-commit.com/#install) (optional but preferred)
4. ``cd`` into the project and enter "direnv allow" when prompted. This will begin
   installing all the development dependancies.
5. If you installed pre-commit, run ``pre-commit install`` inside the project
   directory to setup the githooks.

### Releasing to Pypi
Once you pushed your chances to master, run **one** of the following:

 ```sh
 # If you're installing a major release:
 make deploy-major

 # If you're installing a minor release:
 make deploy-minor

# If you're installing a patch release:
make deploy-patch
 ```
