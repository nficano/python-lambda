# -*- coding: utf-8 -*-
from __future__ import print_function

import hashlib
import json
import logging
import os
import sys
import time
from collections import defaultdict
from imp import load_source
from shutil import copy
from shutil import copyfile
from shutil import copystat
from shutil import copytree
from tempfile import mkdtemp

import boto3
import botocore
import yaml
import subprocess

from .helpers import archive
from .helpers import get_environment_variable_value
from .helpers import mkdir
from .helpers import read
from .helpers import timestamp
from .helpers import LambdaContext


ARN_PREFIXES = {
    'cn-north-1': 'aws-cn',
    'cn-northwest-1': 'aws-cn',
    'us-gov-west-1': 'aws-us-gov',
}

log = logging.getLogger(__name__)


def cleanup_old_versions(
    src, keep_last_versions,
    config_file='config.yaml', profile_name=None,
):
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
        path_to_config_file = os.path.join(src, config_file)
        cfg = read_cfg(path_to_config_file, profile_name)

        profile_name = cfg.get('profile')
        aws_access_key_id = cfg.get('aws_access_key_id')
        aws_secret_access_key = cfg.get('aws_secret_access_key')

        client = get_client(
            'lambda', profile_name, aws_access_key_id, aws_secret_access_key,
            cfg.get('region'),
        )

        response = client.list_versions_by_function(
            FunctionName=cfg.get('function_name'),
        )
        versions = response.get('Versions')
        if len(response.get('Versions')) < keep_last_versions:
            print('Nothing to delete. (Too few versions published)')
        else:
            version_numbers = [elem.get('Version') for elem in
                               versions[1:-keep_last_versions]]
            for version_number in version_numbers:
                try:
                    client.delete_function(
                        FunctionName=cfg.get('function_name'),
                        Qualifier=version_number,
                    )
                except botocore.exceptions.ClientError as e:
                    print('Skipping Version {}: {}'
                          .format(version_number, e.message))


def deploy(
        src, requirements=None, local_package=None,
        config_file='config.yaml', profile_name=None,
        preserve_vpc=False
):
    """Deploys a new function to AWS Lambda.

    :param str src:
        The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    :param str local_package:
        The path to a local package with should be included in the deploy as
        well (and/or is not available on PyPi)
    """
    # Load and parse the config file.
    path_to_config_file = os.path.join(src, config_file)
    cfg = read_cfg(path_to_config_file, profile_name)

    # Copy all the pip dependencies required to run your code into a temporary
    # folder then add the handler file in the root of this directory.
    # Zip the contents of this folder into a single file and output to the dist
    # directory.
    path_to_zip_file = build(
        src, config_file=config_file,
        requirements=requirements,
        local_package=local_package,
    )

    existing_config = get_function_config(cfg)
    if existing_config:
        update_function(cfg, path_to_zip_file, existing_config, preserve_vpc=preserve_vpc)
    else:
        create_function(cfg, path_to_zip_file)


def deploy_s3(
    src, requirements=None, local_package=None,
    config_file='config.yaml', profile_name=None,
    preserve_vpc=False
):
    """Deploys a new function via AWS S3.

    :param str src:
        The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    :param str local_package:
        The path to a local package with should be included in the deploy as
        well (and/or is not available on PyPi)
    """
    # Load and parse the config file.
    path_to_config_file = os.path.join(src, config_file)
    cfg = read_cfg(path_to_config_file, profile_name)

    # Copy all the pip dependencies required to run your code into a temporary
    # folder then add the handler file in the root of this directory.
    # Zip the contents of this folder into a single file and output to the dist
    # directory.
    path_to_zip_file = build(
        src, config_file=config_file, requirements=requirements,
        local_package=local_package,
    )

    use_s3 = True
    s3_file = upload_s3(cfg, path_to_zip_file, use_s3)
    existing_config = get_function_config(cfg)
    if existing_config:
        update_function(cfg, path_to_zip_file, existing_config, use_s3=use_s3,
                        s3_file=s3_file, preserve_vpc=preserve_vpc)
    else:
        create_function(cfg, path_to_zip_file, use_s3=use_s3, s3_file=s3_file)


def upload(
        src, requirements=None, local_package=None,
        config_file='config.yaml', profile_name=None,
):
    """Uploads a new function to AWS S3.

    :param str src:
        The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    :param str local_package:
        The path to a local package with should be included in the deploy as
        well (and/or is not available on PyPi)
    """
    # Load and parse the config file.
    path_to_config_file = os.path.join(src, config_file)
    cfg = read_cfg(path_to_config_file, profile_name)

    # Copy all the pip dependencies required to run your code into a temporary
    # folder then add the handler file in the root of this directory.
    # Zip the contents of this folder into a single file and output to the dist
    # directory.
    path_to_zip_file = build(
        src, config_file=config_file, requirements=requirements,
        local_package=local_package,
    )

    upload_s3(cfg, path_to_zip_file)


def invoke(
    src, event_file='event.json',
    config_file='config.yaml', profile_name=None,
    verbose=False,
):
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
    path_to_config_file = os.path.join(src, config_file)
    cfg = read_cfg(path_to_config_file, profile_name)

    # Set AWS_PROFILE environment variable based on `--profile` option.
    if profile_name:
        os.environ['AWS_PROFILE'] = profile_name

    # Load environment variables from the config file into the actual
    # environment.
    env_vars = cfg.get('environment_variables')
    if env_vars:
        for key, value in env_vars.items():
            os.environ[key] = get_environment_variable_value(value)

    # Load and parse event file.
    path_to_event_file = os.path.join(src, event_file)
    event = read(path_to_event_file, loader=json.loads)

    # Tweak to allow module to import local modules
    try:
        sys.path.index(src)
    except ValueError:
        sys.path.append(src)

    handler = cfg.get('handler')
    # Inspect the handler string (<module>.<function name>) and translate it
    # into a function we can execute.
    fn = get_callable_handler_function(src, handler)

    timeout = cfg.get('timeout')
    if timeout:
        context = LambdaContext(cfg.get('function_name'),timeout)
    else:
        context = LambdaContext(cfg.get('function_name'))

    start = time.time()
    results = fn(event, context)
    end = time.time()

    print('{0}'.format(results))
    if verbose:
        print('\nexecution time: {:.8f}s\nfunction execution '
              'timeout: {:2}s'.format(end - start, cfg.get('timeout', 15)))


def init(src, minimal=False):
    """Copies template files to a given directory.

    :param str src:
        The path to output the template lambda project files.
    :param bool minimal:
        Minimal possible template files (excludes event.json).
    """

    templates_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'project_templates',
    )
    for filename in os.listdir(templates_path):
        if (minimal and filename == 'event.json') or filename.endswith('.pyc'):
            continue
        dest_path = os.path.join(templates_path, filename)

        if not os.path.isdir(dest_path):
            copy(dest_path, src)


def build(
    src, requirements=None, local_package=None,
    config_file='config.yaml', profile_name=None,
):
    """Builds the file bundle.

    :param str src:
       The path to your Lambda ready project (folder must contain a valid
        config.yaml and handler module (e.g.: service.py).
    :param str local_package:
        The path to a local package with should be included in the deploy as
        well (and/or is not available on PyPi)
    """
    # Load and parse the config file.
    path_to_config_file = os.path.join(src, config_file)
    cfg = read_cfg(path_to_config_file, profile_name)

    # Get the absolute path to the output directory and create it if it doesn't
    # already exist.
    dist_directory = cfg.get('dist_directory', 'dist')
    path_to_dist = os.path.join(src, dist_directory)
    mkdir(path_to_dist)

    # Combine the name of the Lambda function with the current timestamp to use
    # for the output filename.
    function_name = cfg.get('function_name')
    output_filename = '{0}-{1}.zip'.format(timestamp(), function_name)

    path_to_temp = mkdtemp(prefix='aws-lambda')
    pip_install_to_target(
        path_to_temp,
        requirements=requirements,
        local_package=local_package,
    )

    # Hack for Zope.
    if 'zope' in os.listdir(path_to_temp):
        print(
            'Zope packages detected; fixing Zope package paths to '
            'make them importable.',
        )
        # Touch.
        with open(os.path.join(path_to_temp, 'zope/__init__.py'), 'wb'):
            pass

    # Gracefully handle whether ".zip" was included in the filename or not.
    output_filename = (
        '{0}.zip'.format(output_filename)
        if not output_filename.endswith('.zip')
        else output_filename
    )

    # Allow definition of source code directories we want to build into our
    # zipped package.
    build_config = defaultdict(**cfg.get('build', {}))
    build_source_directories = build_config.get('source_directories', '')
    build_source_directories = (
        build_source_directories
        if build_source_directories is not None
        else ''
    )
    source_directories = [
        d.strip() for d in build_source_directories.split(',')
    ]

    files = []
    for filename in os.listdir(src):
        abs_filename = os.path.join(src, filename)
        if os.path.isfile(abs_filename):
            if filename == '.DS_Store':
                continue
            if filename == config_file:
                continue
            print('Bundling: %r' % filename)
            files.append(abs_filename)
        elif os.path.isdir(filename) and filename in source_directories:
            print('Bundling directory: %r' % filename)
            files.append(abs_filename)

    # "cd" into `temp_path` directory.
    os.chdir(path_to_temp)
    for f in files:
        if os.path.isfile(f):
            _, filename = os.path.split(f)

            # Copy handler file into root of the packages folder.
            copyfile(f, os.path.join(path_to_temp, filename))
            copystat(f, os.path.join(path_to_temp, filename))
        elif os.path.isdir(f):
            destination_folder = os.path.join(path_to_temp, f[len(src) + 1:])
            copytree(f, destination_folder)

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
        blacklist = ['-i', '#', 'Python==', 'python-lambda==']
        return all(package.startswith(entry) is False for entry in blacklist)
    filtered_packages = filter(_filter_blacklist, packages)
    for package in filtered_packages:
        if package.startswith('-e '):
            package = package.replace('-e ', '')

        print('Installing {package}'.format(package=package))
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '-t', path, '--ignore-installed'])
    print ('Install directory contents are now: {directory}'.format(directory=os.listdir(path)))


def pip_install_to_target(path, requirements=None, local_package=None):
    """For a given active virtualenv, gather all installed pip packages then
    copy (re-install) them to the path provided.

    :param str path:
        Path to copy installed pip packages to.
    :param str requirements:
        If set, only the packages in the supplied requirements file are
        installed.
        If not set then installs all packages found via pip freeze.
    :param str local_package:
        The path to a local package with should be included in the deploy as
        well (and/or is not available on PyPi)
    """
    packages = []
    if not requirements:
        print('Gathering pip packages')
        pkgStr = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
        packages.extend(pkgStr.decode('utf-8').splitlines())
    else:
        if os.path.exists(requirements):
            print('Gathering requirement packages')
            data = read(requirements)
            packages.extend(data.splitlines())

    if not packages:
        print('No dependency packages installed!')

    if local_package is not None:
        if not isinstance(local_package, (list, tuple)):
            local_package = [local_package]
        for l_package in local_package:
            packages.append(l_package)
    _install_packages(path, packages)


def get_role_name(region, account_id, role):
    """Shortcut to insert the `account_id` and `role` into the iam string."""
    prefix = ARN_PREFIXES.get(region, 'aws')
    return 'arn:{0}:iam::{1}:role/{2}'.format(prefix, account_id, role)


def get_account_id(
    profile_name, aws_access_key_id, aws_secret_access_key,
    region=None,
):
    """Query STS for a users' account_id"""
    client = get_client(
        'sts', profile_name, aws_access_key_id, aws_secret_access_key,
        region,
    )
    return client.get_caller_identity().get('Account')


def get_client(
    client, profile_name, aws_access_key_id, aws_secret_access_key,
    region=None,
):
    """Shortcut for getting an initialized instance of the boto3 client."""

    boto3.setup_default_session(
        profile_name=profile_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region,
    )
    return boto3.client(client)


def create_function(cfg, path_to_zip_file, use_s3=False, s3_file=None):
    """Register and upload a function to AWS Lambda."""

    print('Creating your new Lambda function')
    byte_stream = read(path_to_zip_file, binary_file=True)
    profile_name = cfg.get('profile')
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')

    account_id = get_account_id(
        profile_name, aws_access_key_id, aws_secret_access_key, cfg.get(
            'region',
        ),
    )
    role = get_role_name(
        cfg.get('region'), account_id,
        cfg.get('role', 'lambda_basic_execution'),
    )

    client = get_client(
        'lambda', profile_name, aws_access_key_id, aws_secret_access_key,
        cfg.get('region'),
    )

    # Do we prefer development variable over config?
    buck_name = (
        os.environ.get('S3_BUCKET_NAME') or cfg.get('bucket_name')
    )
    func_name = (
        os.environ.get('LAMBDA_FUNCTION_NAME') or cfg.get('function_name')
    )
    print('Creating lambda function with name: {}'.format(func_name))

    if use_s3:
        kwargs = {
            'FunctionName': func_name,
            'Runtime': cfg.get('runtime', 'python2.7'),
            'Role': role,
            'Handler': cfg.get('handler'),
            'Code': {
                'S3Bucket': '{}'.format(buck_name),
                'S3Key': '{}'.format(s3_file),
            },
            'Description': cfg.get('description', ''),
            'Timeout': cfg.get('timeout', 15),
            'MemorySize': cfg.get('memory_size', 512),
            'VpcConfig': {
                'SubnetIds': cfg.get('subnet_ids', []),
                'SecurityGroupIds': cfg.get('security_group_ids', []),
            },
            'Publish': True,
        }
    else:
        kwargs = {
            'FunctionName': func_name,
            'Runtime': cfg.get('runtime', 'python2.7'),
            'Role': role,
            'Handler': cfg.get('handler'),
            'Code': {'ZipFile': byte_stream},
            'Description': cfg.get('description', ''),
            'Timeout': cfg.get('timeout', 15),
            'MemorySize': cfg.get('memory_size', 512),
            'VpcConfig': {
                'SubnetIds': cfg.get('subnet_ids', []),
                'SecurityGroupIds': cfg.get('security_group_ids', []),
            },
            'Publish': True,
        }

    if 'tags' in cfg:
        kwargs.update(
            Tags={
                key: str(value)
                for key, value in cfg.get('tags').items()
            }
        )

    if 'environment_variables' in cfg:
        kwargs.update(
            Environment={
                'Variables': {
                    key: get_environment_variable_value(value)
                    for key, value
                    in cfg.get('environment_variables').items()
                },
            },
        )

    client.create_function(**kwargs)

    concurrency = get_concurrency(cfg)
    if concurrency > 0:
        client.put_function_concurrency(FunctionName=func_name, ReservedConcurrentExecutions=concurrency)


def update_function(
        cfg, path_to_zip_file, existing_cfg, use_s3=False, s3_file=None, preserve_vpc=False
):
    """Updates the code of an existing Lambda function"""

    print('Updating your Lambda function')
    byte_stream = read(path_to_zip_file, binary_file=True)
    profile_name = cfg.get('profile')
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')

    account_id = get_account_id(
        profile_name, aws_access_key_id, aws_secret_access_key, cfg.get(
            'region',
        ),
    )
    role = get_role_name(
        cfg.get('region'), account_id,
        cfg.get('role', 'lambda_basic_execution'),
    )

    client = get_client(
        'lambda', profile_name, aws_access_key_id, aws_secret_access_key,
        cfg.get('region'),
    )

    # Do we prefer development variable over config?
    buck_name = (
        os.environ.get('S3_BUCKET_NAME') or cfg.get('bucket_name')
    )

    if use_s3:
        client.update_function_code(
            FunctionName=cfg.get('function_name'),
            S3Bucket='{}'.format(buck_name),
            S3Key='{}'.format(s3_file),
            Publish=True,
        )
    else:
        client.update_function_code(
            FunctionName=cfg.get('function_name'),
            ZipFile=byte_stream,
            Publish=True,
        )

    kwargs = {
        'FunctionName': cfg.get('function_name'),
        'Role': role,
        'Runtime': cfg.get('runtime'),
        'Handler': cfg.get('handler'),
        'Description': cfg.get('description', ''),
        'Timeout': cfg.get('timeout', 15),
        'MemorySize': cfg.get('memory_size', 512),
    }

    if preserve_vpc:
        kwargs['VpcConfig'] = existing_cfg.get('Configuration', {}).get('VpcConfig')
        if kwargs['VpcConfig'] is None:
            kwargs['VpcConfig'] = {
                'SubnetIds': cfg.get('subnet_ids', []),
                'SecurityGroupIds': cfg.get('security_group_ids', []),
            }
        else:
            del kwargs['VpcConfig']['VpcId']
    else:
        kwargs['VpcConfig'] = {
            'SubnetIds': cfg.get('subnet_ids', []),
            'SecurityGroupIds': cfg.get('security_group_ids', []),
        }

    if 'environment_variables' in cfg:
        kwargs.update(
            Environment={
                'Variables': {
                    key: str(get_environment_variable_value(value))
                    for key, value
                    in cfg.get('environment_variables').items()
                },
            },
        )

    ret = client.update_function_configuration(**kwargs)

    concurrency = get_concurrency(cfg)
    if concurrency > 0:
        client.put_function_concurrency(FunctionName=cfg.get('function_name'), ReservedConcurrentExecutions=concurrency)
    elif 'Concurrency' in existing_cfg:
        client.delete_function_concurrency(FunctionName=cfg.get('function_name'))

    if 'tags' in cfg:
        tags = {
            key: str(value)
            for key, value in cfg.get('tags').items()
        }
        if tags != existing_cfg.get('Tags'):
            if existing_cfg.get('Tags'):
                client.untag_resource(Resource=ret['FunctionArn'],
                                      TagKeys=list(existing_cfg['Tags'].keys()))
            client.tag_resource(Resource=ret['FunctionArn'], Tags=tags)


def upload_s3(cfg, path_to_zip_file, *use_s3):
    """Upload a function to AWS S3."""

    print('Uploading your new Lambda function')
    profile_name = cfg.get('profile')
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')
    client = get_client(
        's3', profile_name, aws_access_key_id, aws_secret_access_key,
        cfg.get('region'),
    )
    byte_stream = b''
    with open(path_to_zip_file, mode='rb') as fh:
        byte_stream = fh.read()
    s3_key_prefix = cfg.get('s3_key_prefix', '/dist')
    checksum = hashlib.new('md5', byte_stream).hexdigest()
    timestamp = str(time.time())
    filename = '{prefix}{checksum}-{ts}.zip'.format(
        prefix=s3_key_prefix, checksum=checksum, ts=timestamp,
    )

    # Do we prefer development variable over config?
    buck_name = (
        os.environ.get('S3_BUCKET_NAME') or cfg.get('bucket_name')
    )
    func_name = (
        os.environ.get('LAMBDA_FUNCTION_NAME') or cfg.get('function_name')
    )
    kwargs = {
        'Bucket': '{}'.format(buck_name),
        'Key': '{}'.format(filename),
        'Body': byte_stream,
    }

    client.put_object(**kwargs)
    print('Finished uploading {} to S3 bucket {}'.format(func_name, buck_name))
    if use_s3:
        return filename


def get_function_config(cfg):
    """Check whether a function exists or not and return its config"""

    function_name = cfg.get('function_name')
    profile_name = cfg.get('profile')
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')
    client = get_client(
        'lambda', profile_name, aws_access_key_id, aws_secret_access_key,
        cfg.get('region'),
    )

    try:
        return client.get_function(FunctionName=function_name)
    except client.exceptions.ResourceNotFoundException as e:
        if 'Function not found' in str(e):
            return False


def get_concurrency(cfg):
    """Return the Reserved Concurrent Executions if present in the config"""
    concurrency = int(cfg.get('concurrency', 0))
    return max(0, concurrency)


def read_cfg(path_to_config_file, profile_name):
    cfg = read(path_to_config_file, loader=yaml.full_load)
    if profile_name is not None:
        cfg['profile'] = profile_name
    elif 'AWS_PROFILE' in os.environ:
        cfg['profile'] = os.environ['AWS_PROFILE']
    return cfg
