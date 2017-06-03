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

import botocore
import boto3
import pip
import yaml

from .helpers import mkdir, read, archive, timestamp


log = logging.getLogger(__name__)


def cleanup_old_versions(src, keep_last_versions):
    """Deletes old deployed versions of the function in AWS Lambda.

    Won't delete $Latest and any aliased version

    :param str src:
        The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    :param int keep_last_versions:
        The number of recent versions to keep and not delete
    """
    if keep_last_versions <= 0:
        print("Won't delete all versions. Please do this manually")
    else:
        path_to_config_file = os.path.join(src, 'config.yaml')
        cfg = read(path_to_config_file, loader=yaml.load)

        aws_access_key_id = cfg.get('aws_access_key_id')
        aws_secret_access_key = cfg.get('aws_secret_access_key')

        client = get_client('lambda', aws_access_key_id, aws_secret_access_key,
                            cfg.get('region'))

        response = client.list_versions_by_function(
            FunctionName=cfg.get("function_name")
        )
        versions = response.get("Versions")
        if len(response.get("Versions")) < keep_last_versions:
            print("Nothing to delete. (Too few versions published)")
        else:
            version_numbers = [elem.get("Version") for elem in
                               versions[1:-keep_last_versions]]
            for version_number in version_numbers:
                try:
                    client.delete_function(
                        FunctionName=cfg.get("function_name"),
                        Qualifier=version_number
                    )
                except botocore.exceptions.ClientError as e:
                    print("Skipping Version {}: {}"
                          .format(version_number, e.message))


def deploy(src, requirements=False, local_package=None):
    """Deploys a new function to AWS Lambda.

    :param str src:
        The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    :param str local_package:
        The path to a local package with should be included in the deploy as
        well (and/or is not available on PyPi)
    """
    # Load and parse the config file.
    path_to_config_file = os.path.join(src, 'config.yaml')
    cfg = read(path_to_config_file, loader=yaml.load)

    # Copy all the pip dependencies required to run your code into a temporary
    # folder then add the handler file in the root of this directory.
    # Zip the contents of this folder into a single file and output to the dist
    # directory.
    path_to_zip_file = build(src, requirements, local_package)

    if function_exists(cfg, cfg.get('function_name')):
        update_function(cfg, path_to_zip_file)
    else:
        create_function(cfg, path_to_zip_file)


def invoke(src, alt_event=None, verbose=False):
    """Simulates a call to your function.

    :param str src:
        The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    :param str alt_event:
        An optional argument to override which event file to use.
    :param bool verbose:
        Whether to print out verbose details.
    """
    # Load and parse the config file.
    path_to_config_file = os.path.join(src, 'config.yaml')
    cfg = read(path_to_config_file, loader=yaml.load)

    # Load and parse event file.
    if alt_event:
        path_to_event_file = os.path.join(src, alt_event)
    else:
        path_to_event_file = os.path.join(src, 'event.json')
    event = read(path_to_event_file, loader=json.loads)

    #Tweak to allow module to import local modules
    try:
        sys.path.index(src)
    except:
        sys.path.append(src)

    handler = cfg.get('handler')
    # Inspect the handler string (<module>.<function name>) and translate it
    # into a function we can execute.
    fn = get_callable_handler_function(src, handler)

    # TODO: look into mocking the ``context`` variable, currently being passed
    # as None.

    start = time.time()
    results = fn(event, None)
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

    templates_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "project_templates")
    for filename in os.listdir(templates_path):
        if (minimal and filename == 'event.json') or filename.endswith('.pyc'):
            continue
        dest_path = os.path.join(templates_path, filename)

        if not os.path.isdir(dest_path):
            copy(dest_path, src)


def build(src, requirements=False, local_package=None):
    """Builds the file bundle.

    :param str src:
       The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    :param str local_package:
        The path to a local package with should be included in the deploy as
        well (and/or is not available on PyPi)
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
    pip_install_to_target(path_to_temp,
                          requirements=requirements,
                          local_package=local_package)

    # Hack for Zope.
    if "zope" in os.listdir(path_to_temp):
        print("Zope packages detected; fixing Zope package paths to make them importable.")
        # Touch.
        with open(os.path.join(path_to_temp, "zope/__init__.py"), "wb"):
            pass

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
            print("Bundling: %r" % filename)
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


def _install_packages(path, packages):
    """Install all packages listed to the target directory.

    Ignores any package that includes Python itself and python-lambda as well
    since its only needed for deploying and not running the code

    :param str path:
        Path to copy installed pip packages to.
    :param list packages:
        A list of packages to be installed via pip.
    """
    def _filter_blacklist(package):
        blacklist = ["-i", "#", "Python==", "python-lambda=="]
        return all(package.startswith(entry) is False for entry in blacklist)
    filtered_packages = filter(_filter_blacklist, packages)
    for package in filtered_packages:
        if package.startswith('-e '):
            package = package.replace('-e ', '')

        print('Installing {package}'.format(package=package))
        pip.main(['install', package, '-t', path, '--ignore-installed'])


def pip_install_to_target(path, requirements=False, local_package=None):
    """For a given active virtualenv, gather all installed pip packages then
    copy (re-install) them to the path provided.

    :param str path:
        Path to copy installed pip packages to.
    :param bool requirements:
        If set, only the packages in the requirements.txt file are installed.
        The requirements.txt file needs to be in the same directory as the
        project which shall be deployed.
        Defaults to false and installs all pacakges found via pip freeze if
        not set.
    :param str local_package:
        The path to a local package with should be included in the deploy as
        well (and/or is not available on PyPi)
    """
    packages = []
    if not requirements:
        print('Gathering pip packages')
        packages.extend(pip.operations.freeze.freeze())
    else:
        if os.path.exists("requirements.txt"):
            print('Gathering requirement packages')
            data = read("requirements.txt")
            packages.extend(data.splitlines())

    if not packages:
        print('No dependency packages installed!')

    if local_package is not None:
        if not isinstance(local_package, (list, tuple) ):
            local_package = [local_package]
        for l_package in local_package:
            packages.append(l_package)
    _install_packages(path, packages)


def get_role_name(account_id, role):
    """Shortcut to insert the `account_id` and `role` into the iam string."""
    return "arn:aws:iam::{0}:role/{1}".format(account_id, role)


def get_account_id(aws_access_key_id, aws_secret_access_key):
    """Query STS for a users' account_id"""
    client = get_client('sts', aws_access_key_id, aws_secret_access_key)
    return client.get_caller_identity().get('Account')


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

    func_name = (
        os.environ.get('LAMBDA_FUNCTION_NAME') or cfg.get('function_name')
    )
    print('Creating lambda function with name: {}'.format(func_name))
    client.create_function(
        FunctionName=func_name,
        Runtime=cfg.get('runtime', 'python2.7'),
        Role=role,
        Handler=cfg.get('handler'),
        Code={'ZipFile': byte_stream},
        Description=cfg.get('description'),
        Timeout=cfg.get('timeout', 15),
        MemorySize=cfg.get('memory_size', 512),
        Environment={
            'Variables': {
                key.strip('LAMBDA_'): value
                for key, value in os.environ.items()
                if key.startswith('LAMBDA_')
            }
        },
        Publish=True
    )


def update_function(cfg, path_to_zip_file):
    """Updates the code of an existing Lambda function"""

    print("Updating your Lambda function")
    byte_stream = read(path_to_zip_file)
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')

    account_id = get_account_id(aws_access_key_id, aws_secret_access_key)
    role = get_role_name(account_id, cfg.get('role', 'lambda_basic_execution'))

    client = get_client('lambda', aws_access_key_id, aws_secret_access_key,
                        cfg.get('region'))

    client.update_function_code(
        FunctionName=cfg.get('function_name'),
        ZipFile=byte_stream,
        Publish=True
    )

    client.update_function_configuration(
        FunctionName=cfg.get('function_name'),
        Role=role,
        Handler=cfg.get('handler'),
        Description=cfg.get('description'),
        Timeout=cfg.get('timeout', 15),
        MemorySize=cfg.get('memory_size', 512),
        VpcConfig={
            'SubnetIds': cfg.get('subnet_ids', []),
            'SecurityGroupIds': cfg.get('security_group_ids', [])
        }
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
