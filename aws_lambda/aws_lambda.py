# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import logging
import os
import sys
import time
from imp import load_source
from shutil import copy, copyfile
from tempfile import mkdtemp

import boto3
import pip
import yaml
from . import project_template
from .context import MockContext
from .helpers import mkdir, read, archive, timestamp


log = logging.getLogger(__name__)


def deploy(src):
    """Deploys a new function to AWS Lambda.

    :param str src:
        The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    """
    # Load and parse the config file.
    path_to_config_file = os.path.join(src, 'config.yaml')
    cfg = read(path_to_config_file, loader=yaml.load)

    # Copy all the pip dependencies required to run your code into a temporary
    # folder then add the handler file in the root of this directory.
    # Zip the contents of this folder into a single file and output to the dist
    # directory.
    path_to_zip_file = build(src)

    if function_exists(cfg, cfg.get('function_name')):
        update_function(cfg, path_to_zip_file)
    else:
        create_function(cfg, path_to_zip_file)


def _load_json(base_dir, filename, default):
    if filename is None:
        filename = default
    path = os.path.join(base_dir, filename)
    try:
        return read(path, loader=json.loads)
    except IOError:
        print("File does not exist: {}".format(path))
        # file does not exist or json is malformed
        return None
    except ValueError:
        print("Could not decode JSON object: {}".format(path))
        print("Aborting...")
        sys.exit(1)


def invoke(src, alt_event=None, alt_context=None, verbose=False):
    """Simulates a call to your function.

    :param str src:
        The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    :param str alt_event:
        An optional argument to override which event file to use.
    :param str alt_context:
        An optional argument to override which context file to use.
    :param bool verbose:
        Whether to print out verbose details.
    """
    # Load and parse the config file.
    path_to_config_file = os.path.join(src, 'config.yaml')
    cfg = read(path_to_config_file, loader=yaml.load)

    # Load and parse event file.
    event = _load_json(src, alt_event, 'event.json')
    context = _load_json(src, alt_context, 'context.json')

    handler = cfg.get('handler')
    # Inspect the handler string (<module>.<function name>) and translate it
    # into a function we can execute.
    fn = get_callable_handler_function(src, handler)

    start = time.time()
    results = fn(event, MockContext(context))
    end = time.time()

    print("{0}".format(results))
    if verbose:
        print("\nexecution time: {:.8f}s\nfunction execution "
              "timeout: {:2}s".format(end - start, cfg.get('timeout', 15)))


def init(src, minimal=False):
    """Copies template files to a given directory.

    :param str src:
        The path to output the template lambda project files.
    :param bool minimal:
        Minimal possible template files (excludes event.json).
    """

    path_to_project_template = project_template.__path__[0]
    for f in os.listdir(path_to_project_template):
        path_to_file = os.path.join(path_to_project_template, f)
        if minimal and f == 'event.json':
            continue
        if f.endswith('.pyc'):
            # We don't need the compiled files.
            continue
        copy(path_to_file, src)


def build(src):
    """Builds the file bundle.

    :param str path_to_handler_file:
       The path to handler (main execution) file.
    :param str path_to_dist:
       The path to the folder for distributable.
    :param str output_filename:
       The name of the archive file.
    """
    # Load and parse the config file.
    path_to_config_file = os.path.join(src, 'config.yaml')
    cfg = read(path_to_config_file, loader=yaml.load)

    # Get the absolute path to the output directory and create it if it doesn't
    # already exist.
    dist_directory = cfg.get('dist_directory', 'dist')
    path_to_dist = os.path.join(src, dist_directory)
    mkdir(path_to_dist)

    # Combine the name of the Lambda function with the current timestamp to use
    # for the output filename.
    function_name = cfg.get('function_name')
    output_filename = "{0}-{1}.zip".format(timestamp(), function_name)

    path_to_temp = mkdtemp(prefix='aws-lambda')
    pip_install_to_target(path_to_temp)

    # Gracefully handle whether ".zip" was included in the filename or not.
    output_filename = ('{0}.zip'.format(output_filename)
                       if not output_filename.endswith('.zip')
                       else output_filename)

    files = []
    for filename in os.listdir(src):
        if os.path.isfile(filename):
            if filename == '.DS_Store':
                continue
            if filename == 'config.yaml':
                continue
            files.append(os.path.join(src, filename))

    # "cd" into `temp_path` directory.
    os.chdir(path_to_temp)
    for f in files:
        _, filename = os.path.split(f)

        # Copy handler file into root of the packages folder.
        copyfile(f, os.path.join(path_to_temp, filename))

    # Zip them together into a single file.
    # TODO: Delete temp directory created once the archive has been compiled.
    path_to_zip_file = archive('./', path_to_dist, output_filename)
    return path_to_zip_file


def get_callable_handler_function(src, handler):
    """Tranlate a string of the form "module.function" into a callable
    function.

    :param str src:
      The path to your Lambda project containing a valid handler file.
    :param str handler:
      A dot delimited string representing the `<module>.<function name>`.
    """

    # "cd" into `src` directory.
    os.chdir(src)

    module_name, function_name = handler.split('.')
    filename = get_handler_filename(handler)

    path_to_module_file = os.path.join(src, filename)
    module = load_source(module_name, path_to_module_file)
    return getattr(module, function_name)


def get_handler_filename(handler):
    """Shortcut to get the filename from the handler string.

    :param str handler:
      A dot delimited string representing the `<module>.<function name>`.
    """
    module_name, _ = handler.split('.')
    return '{0}.py'.format(module_name)


def pip_install_to_target(path):
    """For a given active virtualenv, gather all installed pip packages then
    copy (re-install) them to the path provided.

    :param str path:
        Path to copy installed pip packages to.
    """
    print('Gathering pip packages')
    for r in pip.operations.freeze.freeze():
        if r.startswith('Python=='):
            # For some reason Python is coming up in pip freeze.
            continue
        pip.main(['install', r, '-t', path, '--ignore-installed'])


def get_role_name(account_id, role):
    """Shortcut to insert the `account_id` and `role` into the iam string."""
    return "arn:aws:iam::{0}:role/{1}".format(account_id, role)


def get_account_id(aws_access_key_id, aws_secret_access_key):
    """Query IAM for a users' account_id"""
    client = get_client('iam', aws_access_key_id, aws_secret_access_key)
    return client.get_user()['User']['Arn'].split(':')[4]


def get_client(client, aws_access_key_id, aws_secret_access_key, region=None):
    """Shortcut for getting an initialized instance of the boto3 client."""

    return boto3.client(
        client,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region
    )


def create_function(cfg, path_to_zip_file):
    """Register and upload a function to AWS Lambda."""

    print("Creating your new Lambda function")
    byte_stream = read(path_to_zip_file)
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')

    account_id = get_account_id(aws_access_key_id, aws_secret_access_key)
    role = get_role_name(account_id, cfg.get('role', 'lambda_basic_execution'))

    client = get_client('lambda', aws_access_key_id, aws_secret_access_key,
                        cfg.get('region'))

    client.create_function(
        FunctionName=cfg.get('function_name'),
        Runtime=cfg.get('runtime', 'python2.7'),
        Role=role,
        Handler=cfg.get('handler'),
        Code={'ZipFile': byte_stream},
        Description=cfg.get('description'),
        Timeout=cfg.get('timeout', 15),
        MemorySize=cfg.get('memory_size', 512),
        Publish=True
    )


def update_function(cfg, path_to_zip_file):
    """Updates the code of an existing Lambda function"""

    print("Updating your Lambda function")
    byte_stream = read(path_to_zip_file)
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')

    client = get_client('lambda', aws_access_key_id, aws_secret_access_key,
                        cfg.get('region'))

    client.update_function_code(
        FunctionName=cfg.get('function_name'),
        ZipFile=byte_stream,
        Publish=True
    )


def function_exists(cfg, function_name):
    """Check whether a function exists or not"""

    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')
    client = get_client('lambda', aws_access_key_id, aws_secret_access_key,
                        cfg.get('region'))
    functions = client.list_functions().get('Functions', [])
    for fn in functions:
        if fn.get('FunctionName') == function_name:
            return True
    return False
