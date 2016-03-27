# -*- coding: utf-8 -*-
import imp
import json
import os
import shutil
import tempfile
import zipfile

from pip.operations import freeze
import boto3
import pip
import yaml


def deploy(src):
    config_file = os.path.join(src, 'config.yaml')
    dist_dir = os.path.join(src, 'dist')

    ensure_dir(dist_dir)

    cfg = yaml_loader(config_file)

    handler_file = cfg.get('handler').split('.')[0] + '.py'
    handler_file_path = os.path.join(src, handler_file)
    zipfile_name = cfg.get('function_name') + '.zip'
    build(handler_file_path, dist_dir, zipfile_name)

    with open(os.path.join(dist_dir, zipfile_name)) as fh:
        bin_data = fh.read()
        create_function(cfg, bin_data)


def invoke(src):
    os.chdir(src)
    config_file = os.path.join(src, 'config.yaml')
    event_file = os.path.join(src, 'event.json')

    event = json_loader(event_file)
    cfg = yaml_loader(config_file)
    module_name, func_name = cfg.get('handler').split('.')
    python_file_path = os.path.join(src, module_name + '.py')
    module = imp.load_source(module_name, python_file_path)
    fn = getattr(module, func_name)
    return fn(event, None)


def build(handler_file_path, dest, zip_filename):
    temp_path = mkdtemp()
    pip_install_to_target(temp_path)

    # Move to the temp directory so paths can be referred to as relative.  This
    # prevents the whole path from being archived so all files sit in archive
    # root, to not do this would cause /tmp/var/T/... subfolders to be created
    # in zip.
    os.chdir(temp_path)

    _, filename = os.path.split(handler_file_path)
    dst_file_path = os.path.join(temp_path, filename)
    shutil.copyfile(handler_file_path, dst_file_path)

    archive('./', dest, zip_filename)


def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)


def mkdtemp(prefix='python-lambda-'):
    return tempfile.mkdtemp(prefix)


def archive(src, dest, filename):
    output = os.path.join(dest, filename)
    zfh = zipfile.ZipFile(output, 'w')

    for root, dirs, files in os.walk(src):
        for file in files:
            zfh.write(os.path.join(root, file))
    zfh.close()


def pip_install_to_target(path):
    reqs = pip_freeze()
    for r in reqs:
        pip.main(['install', r, '-t', path, '--ignore-installed'])


def pip_freeze():
    return [f for f in freeze.freeze()]


def json_loader(path):
    return load_as(path, json.loads)


def yaml_loader(path):
    return load_as(path, yaml.load)


def load_as(path, parser):
    with open(path) as fh:
        return parser(fh.read())


def get_role_name(account_id):
    return "arn:aws:iam::{0}:role/lambda_basic_execution".format(account_id)


def get_account_id(aws_access_key_id, aws_secret_access_key):
    client = get_client('iam', aws_access_key_id, aws_secret_access_key)
    return client.get_user()['User']['Arn'].split(':')[4]


def get_client(client, aws_access_key_id, aws_secret_access_key):
    return boto3.client(client,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key)


def create_function(cfg, bin_data):
    account_id = get_account_id(
        cfg.get('aws_access_key_id'),
        cfg.get('aws_secret_access_key')
    )
    role = get_role_name(account_id)
    client = get_client('lambda',
                        cfg.get('aws_access_key_id'),
                        cfg.get('aws_secret_access_key'))

    client.create_function(
        FunctionName=cfg.get('function_name'),
        Runtime=cfg.get('runtime'),
        Role=role,
        Handler=cfg.get('handler'),
        Code={'ZipFile': bin_data},
        Description=cfg.get('description'),
        Timeout=cfg.get('timeout'),
        MemorySize=cfg.get('memory_size'),
        Publish=True
    )
