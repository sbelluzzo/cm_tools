#!/usr/bin/env python
"""
Cloudman CLI Launcher

Usage: cloudman-launcher.py [options]

Options:
    --access_key=key
    --secret_key=key
    --cluster_name=name         Set the cluster name
    --cluster_type=type         Specify cluster type (Test/Data/Galaxy/Shared_cluster)
    --default_bucket_url=url    Set default_bucket_url (priority over bucket_default)
    --image_id=image_id         Set image id to use
    --instance_type=type        Set instance type
    --password=passwd           Set password [default: random]
    --key_name=key_name         SSH Key to use
    --zone=zone                 Specify an availability zone
"""

DEFAULT_CLUSTER_NAME = "cls-"

import string, os, sys
from time import sleep
from collections import defaultdict
import webbrowser as wb
from docopt import docopt

from boto import config as boto_config
from bioblend.cloudman import CloudManConfig, CloudManInstance, CloudManLauncher, VMLaunchException
from bioblend.util import Bunch


def process_args(config, cli_args):
    if cli_args.get('--password') == 'random':
        del cli_args['--password']
    config.update({k.lstrip('--'): v for k, v in cli_args.iteritems()
        if v is not None})
    return config
# make keys consistent, then update, starting at lowest priority to highest

def process_env(config):
    access_key = os.environ.get('AWS_ACCESS_KEY', None) or os.environ.get('EC2_ACCESS_KEY', None)
    if access_key:
        config['access_key'] = access_key
    secret_key = os.environ.get('AWS_SECRET_KEY', None) or os.environ.get('EC2_SECRET_KEY', None)
    if secret_key:
        config['secret_key'] = secret_key
    password = os.environ.get('CM_PASSWORD', None)
    if password:
        config['password'] = password
    return config

def process_cfg_file():
    pass

def process_configuration(cli_args):
    config = defaultdict(lambda: None)
    process_env(config)
    process_args(config, cli_args)
    if not config['access_key'] or not config['secret_key']:
        raise RuntimeError("No credentials")
    return config


def create_cloud_config():
    cloud_config = Bunch(
        name='nectar',
        cloud_type='openstack',
        bucket_default='cloudman-os',
        region_name='melbourne',
        region_endpoint='nova.rc.nectar.org.au',
        ec2_port=8773,
        ec2_conn_path='/services/Cloud',
        cidr_range='',      # ips that can access (sec groups)
        is_secure=True,
        s3_host='swift.rc.nectar.org.au',
        s3_port=8888,
        s3_conn_path='/')
    return cloud_config

def create_cloudman_config(cloud_config, config):
    cfg = CloudManConfig(access_key=config['access_key'],
                         secret_key=config['secret_key'],
                         cluster_name=config['cluster_name'] or DEFAULT_CLUSTER_NAME + mkpasswd(5),
                         image_id=config['image_id'],
                         instance_type=config['instance_type'],
                         password=config['password'] or mkpasswd(),
                         placement=config['zone'],
                         key_name=config['key_name'],
                         cloud_metadata=cloud_config,
                         block_until_ready=True)
    return cfg

def mkpasswd(length=20):
# https://stackoverflow.com/questions/7479442/high-quality-simple-random-password-generator
    chars = string.ascii_uppercase + string.digits + string.ascii_lowercase
    password = ''
    for i in range(length):
        password += chars[ord(os.urandom(1)) % len(chars)]
    return password

def launch_master(cm_cfg, **kwargs):
    launcher = CloudManLauncher(cm_cfg.access_key, cm_cfg.secret_key, cm_cfg.cloud_metadata)
    result = launcher.launch(cm_cfg.cluster_name, cm_cfg.image_id, cm_cfg.instance_type,
        cm_cfg.password, cm_cfg.kernel_id, cm_cfg.ramdisk_id, cm_cfg.key_name,
        cm_cfg.security_groups, cm_cfg.placement, **kwargs)
    if (result['error'] is not None):
        raise VMLaunchException("Error launching cloudman instance: {0}".format(result['error']))
    return CloudManInstance(None, None, launcher=launcher, launch_result=result,
            cloudman_config=cm_cfg)

def cm_launch(cloud, config):
    # build cloudman config
    cm_cfg = create_cloudman_config(cloud, config)
    # launch instance
    #instance = CloudManInstance.launch_instance(cm_cfg)
    instance = launch_master(cm_cfg, default_bucket_url=config['default_bucket_url'])
    print("Starting cluster: {1}. Please wait.".format(config['cluster_name']))
    state = instance.get_machine_status()
    while state['instance_state'] not in {'running', 'error'}:
        sleep(10)
        state = instance.get_machine_status()
        sys.stderr.write("\r{0}".format(state['instance_state']))
        sys.stderr.flush()
    print()
    if state['instance_state'] == 'running':
        print("IP: {0}, Password: {1}".format(state['public_ip'], cm_cfg.password))
        #print(instance.get_static_state()) # nginx wants a user, bioblend doesn't provide
        wb.open_new_tab("http://{0}/cloud".format(state['public_ip']))

def cm_launch_from_cli():
    if len(sys.argv[1:]) == 0:
        print("No arguments provided. Quitting.")
        sys.exit(1)
    args = docopt(__doc__, version='Galaxy Docker Launcher 0.0.1a1')
    # process args, combine with boto/bioblend config
    config = process_configuration(args)
    # build cloud config
    cloud = create_cloud_config()
    cm_launch(cloud, config)
