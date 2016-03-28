# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import logging
from imp import load_source
from shutil import copy, copyfile
from tempfile import mkdtemp

import boto3
import pip
import yaml
from . import project_template
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

    # Get the absolute path to the output directory and create it if it doesn't
    # already exist.
    path_to_dist = os.path.join(src, 'dist')
    mkdir(path_to_dist)

    # Combine the name of the Lambda function with the current timestamp to use
    # for the output filename.
    function_name = cfg.get('function_name')
    output_filename = "{0}-{1}.zip".format(timestamp(), function_name)

    # Determine the filename and absolute path to the handler module.
    handler = cfg.get('handler')
    filename = get_handler_filename(handler)
    path_to_handler_file = os.path.join(src, filename)

    # Copy all the pip dependencies required to run your code into a temporary
    # folder then add the handler file in the root of this directory.
    # Zip the contents of this folder into a single file and output to the dist
    # directory.
    path_to_zip_file = build(path_to_handler_file, path_to_dist,
                             output_filename)

    if function_exists(cfg, cfg.get('function_name')):
        update_function(cfg, path_to_zip_file)
    else:
        create_function(cfg, path_to_zip_file)


def invoke(src):
    """Simulates a call to your function.

    :param str src:
        The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    """
    # Load and parse the config file.
    path_to_config_file = os.path.join(src, 'config.yaml')
    cfg = read(path_to_config_file, loader=yaml.load)

    # Load and parse event file.
    path_to_event_file = os.path.join(src, 'event.json')
    event = read(path_to_event_file, loader=json.loads)

    handler = cfg.get('handler')
    # Inspect the handler string (<module>.<function name>) and translate it
    # into a function we can execute.
    fn = get_callable_handler_function(src, handler)

    # TODO: look into mocking the ``context`` variable, currently being passed
    # as None.
    return fn(event, None)


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
        copy(path_to_file, src)


def build(path_to_handler_file, path_to_dist, output_filename):
    """Builds the file bundle.

    :param str path_to_handler_file:
       The path to handler (main execution) file.
    :param str path_to_dist:
       The path to the folder for distributable.
    :param str output_filename:
       The name of the archive file.
    """
    path_to_temp = mkdtemp(prefix='aws-lambda')
    pip_install_to_target(path_to_temp)

    # Gracefully handle whether ".zip" was included in the filename or not.
    output_filename = ('{0}.zip'.format(output_filename)
                       if not output_filename.endswith('.zip')
                       else output_filename)

    # "cd" into `temp_path` directory.
    os.chdir(path_to_temp)

    _, filename = os.path.split(path_to_handler_file)

    # Copy handler file into root of the packages folder.
    copyfile(path_to_handler_file, os.path.join(path_to_temp, filename))

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
        pip.main(['install', r, '-t', path, '--ignore-installed'])


def get_role_name(account_id):
    """Shortcut to insert the `account_id` into the iam string."""
    return "arn:aws:iam::{0}:role/lambda_basic_execution".format(account_id)


def get_account_id(aws_access_key_id, aws_secret_access_key):
    """Query IAM for a users' account_id"""
    client = get_client('iam', aws_access_key_id, aws_secret_access_key)
    return client.get_user()['User']['Arn'].split(':')[4]


def get_client(client, aws_access_key_id, aws_secret_access_key):
    """Shortcut for getting an initialized instance of the boto3 client."""

    return boto3.client(
        client,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )


def create_function(cfg, path_to_zip_file):
    """Register and upload a function to AWS Lambda."""

    print("Creating your new Lambda function")
    byte_stream = read(path_to_zip_file)
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')

    account_id = get_account_id(aws_access_key_id, aws_secret_access_key)
    role = get_role_name(account_id)

    client = get_client('lambda', aws_access_key_id, aws_secret_access_key)

    client.create_function(
        FunctionName=cfg.get('function_name'),
        Runtime=cfg.get('runtime'),
        Role=role,
        Handler=cfg.get('handler'),
        Code={'ZipFile': byte_stream},
        Description=cfg.get('description'),
        Timeout=cfg.get('timeout'),
        MemorySize=cfg.get('memory_size'),
        Publish=True
    )


def update_function(cfg, path_to_zip_file):
    """Updates the code of an existing Lambda function"""

    print("Updating your Lambda function")
    byte_stream = read(path_to_zip_file)
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')

    client = get_client('lambda', aws_access_key_id, aws_secret_access_key)

    client.update_function_code(
        FunctionName=cfg.get('function_name'),
        ZipFile=byte_stream,
        Publish=True
    )


def function_exists(cfg, function_name):
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')
    client = get_client('lambda', aws_access_key_id, aws_secret_access_key)
    functions = client.list_functions().get('Functions', [])
    for fn in functions:
        if fn.get('FunctionName') == function_name:
            return True
    return False
