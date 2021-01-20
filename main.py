#!/usr/bin/env python3
#! -*- coding:utf8 -*-

import sys
if sys.version_info.major != 3:
    print("Python2 not supported, Please use python3 run again.")
    sys.exit(1)

import argparse
import setproctitle

import os
project_path = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(project_path, "log/topargus-agent.log")
os.environ['LOG_PATH'] =  log_path 
from common.slogging import slog

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.description='TOP-Argus Agent，拉取远程配置，报警采集并上报'
    parser.add_argument('-a', '--alarm', help='alarm proxy host, agent pull config and push alarm to this proxy host, eg: 127.0.0.1:9090', default='127.0.0.1:9090')
    parser.add_argument('-f', '--file', help="log file for agent to watch, eg: ./xtop.log", default='./xtop.log')
    args = parser.parse_args()

    # set process title
    setproctitle.setproctitle('topargus-agent')

    from agent import argus_agent
    r = argus_agent.run(args)
    sys.exit(r)
