#!/usr/bin/env python3
#! -*- coding:utf8 -*-

import os
now_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(now_dir)  #parent dir
activate_this = '%s/vvlinux/bin/activate_this.py' % base_dir
exec(open(activate_this).read())

import sys
sys.path.insert(0, base_dir)


import queue
import time
import requests
import copy
import json
import threading
import random
import operator
import argparse
from urllib.parse import urljoin

from common.slogging import slog



alarm_proxy_host = '127.0.0.1:9090'
mysession = requests.Session()
mypublicip = '127.0.0.1'
mycommand = []


def get_command_from_remote():
    global alarm_proxy_host, mypublicip, mycommand
    url = 'http://' + alarm_proxy_host
    url = urljoin(url, '/api/command/')
    my_headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
            'Content-Type': 'application/json;charset=UTF-8',
            }
    config = {}
    try:
        #res = requests.get(url, headers = my_headers, timeout = 5)
        res = mysession.get(url, headers = my_headers, timeout = 5)
        if res.status_code == 200:
            if res.json().get('status') == 0:
                slog.info("get remote command ok, response: {0}".format(res.text))
                config = res.json().get('config')
                command = res.json().get('command')  #list
                mycommand.extend(command)
                ip = res.json().get('ip')
                if ip != None and ip.find(':') != -1:
                    mypublicip = ip
    except Exception as e:
        slog.info("exception: {0}".format(e))
        return False

    slog.info('get remote command ok: {0}'.format(json.dumps(mycommand)))
    return True

def update_command():
    global mycommand
    while True:
        time.sleep(60)
        slog.info('update remote command alive')
        get_command_from_remote()

    return

def execute_command():
    global mycommand
    while True:
        time.sleep(1)
        while mycommand:
            cmd = mycommand.pop()
            slog.debug("execute_command: {0}".format(cmd))
            os.system(cmd)

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.description='TOP-Argus Agent，拉取远程配置，报警采集并上报'
    parser.add_argument('-a', '--alarm', help='alarm proxy host, agent pull config and push alarm to this proxy host, eg: 127.0.0.1:9090', default='127.0.0.1:9090')
    args = parser.parse_args()

    if args.alarm.find(':') == -1:
        slog.error('alarm proxy host invalid')
        sys.exit()

    alarm_proxy_host = args.alarm
    start_print = 'super agent start... host:{0} \n'.format(alarm_proxy_host)

    execmd_th = threading.Thread(target = execute_command)

    update_command()


