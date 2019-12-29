#!/usr/bin/env python3
#! -*- coding:utf8 -*-

import os
now_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(now_dir)  #parent dir
activate_this = '%s/vvlinux/bin/activate_this.py' % base_dir
exec(open(activate_this).read())

import sys
sys.path.insert(0, base_dir)


import hashlib
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
from agent.cpu import CpuWatch
from agent.net import BandwidthWatch

#xnetwork-08:35:49.631-T1719:[Keyfo]-(elect_vhost.cc: HandleRumorMessage:381): original_elect_vhost_send local_node_id:010000fc609372cc194a437ae775bdbf00000000d60a7c10e9cc5f94e24cb9c63ee1fba3 chain_hash:3340835543 chain_msgid:655361 chain_msg_size:1382 send_timestamp:1573547735068 src_node_id:67000000ff7fff7fffffffffffffffff0000000032eae48d5405ad0a57173799f7490716 dest_node_id:67000000ff7fff7fffffffffffffffff0000000061d1343f82769c3eff69c5448e7b1fe5 is_root:0 broadcast:0

#xnetwork-08:35:49.631-T1719:[Keyfo]-(elect_vhost.cc: HandleRumorMessage:381): final_handle_rumor local_node_id:010000fc609372cc194a437ae775bdbf00000000d60a7c10e9cc5f94e24cb9c63ee1fba3 chain_hash:771962061 chain_msgid:655361 packet_size:608 chain_msg_size:196 hop_num:1 recv_timestamp:1573547749646 src_node_id:690000010140ff7fffffffffffffffff000000009aee88245d7e31e7abaab1ac9956d5a0 dest_node_id:690000010140ff7fffffffffffffffff0000000032eae48d5405ad0a57173799f7490716 is_root:0 broadcast:0

ALARMQ = queue.Queue(2000)
ALARMQ_HIGH = queue.Queue(2000)
gconfig = {
        'global_sample_rate': 1000,  # sample_rate%。
        'alarm_pack_num': 2,   # upload alarm size one time
        'config_update_time': 5 * 60,  # 5 min
        'grep_broadcast': {
            'start': 'true',
            'sample_rate': 200,    # 20%
            'alarm_type': 'packet',
            'network_focus_on': ['640000','650000', '660000', '670000', '680000', '690000'], # src or dest
            'network_ignore':   [],  # src or dest
            },
        'grep_point2point': {
            'start': 'false',
            'sample_rate': 5,    # 1%
            'alarm_type': 'packet',
            'network_focus_on': ['640000','650000', '660000', '670000', '680000', '690000'], # src or dest
            'network_ignore':   [],  # src or dest
            },
        'grep_networksize': {
            'start': 'true',
            'sample_rate': 50,  # 5%
            'alarm_type': 'networksize',
            },
        'system_cron': {
            'start': 'true',
            'alarm_type': 'system',
            }
        }
NodeIdMap = {} # keep all nodeid existing: key is node_id, value is timestamp (ms)
mark_down_flag = False

alarm_proxy_host = '127.0.0.1:9090'
mysession = requests.Session()
mypublic_ip_port = '127.0.0.1:800'
my_root_id = ''

def dict_cmp(a, b):
    typea = isinstance(a, dict) 
    typeb = isinstance(b, dict) 

    # normal type
    if typea != typeb:
        return False
    if not typea and not typeb:
        return operator.eq(a, b)

    for k in set(a) | set(b):
        if k not in a or k not in b:
            slog.info('dict_cmp diff k:{0}'.format(k))
            return False

        if not dict_cmp(a[k], b[k]):
            return False

    return True

def update_config_from_remote():
    global gconfig, alarm_proxy_host, mypublic_ip_port 
    url = 'http://' + alarm_proxy_host
    url = urljoin(url, '/api/config/')
    my_headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
            'Content-Type': 'application/json;charset=UTF-8',
            }
    config = {}
    try:
        res = requests.get(url, headers = my_headers, timeout = 5)
        if res.status_code == 200:
            if res.json().get('status') == 0:
                slog.info("get remote config ok, response: {0}".format(res.text))
                config = res.json().get('config')
    except Exception as e:
        slog.info("exception: {0}".format(e))
        return False

    if not config:
        slog.info("get remote config fail")
        return False

    if dict_cmp(config, gconfig):
        slog.info("get remote config same as default, no need udpate")
        return False

    # TODO(smaug) do something check for config
    gconfig = copy.deepcopy(config)
    slog.info('get remote config ok: {0}'.format(json.dumps(gconfig)))
    return True

def update_config():
    global gconfig
    while True:
        time_step = gconfig.get('config_update_time')
        if not time_step:
            time_step = 5 * 60
        time.sleep(time_step)
        slog.info('update remote config alive, update_step:{0} s'.format(time_step))
        update_config_from_remote()

    return

def clear_queue():
    global ALARMQ, ALARMQ_HIGH 
    while not ALARMQ.empty():
        ALARMQ.get()
    while not ALARMQ_HIGH.empty():
        ALARMQ_HIGH.get()
    slog.info("clear alarmqueue/alarm_high_queue")

def print_queue():
    global ALARMQ, ALARMQ_HIGH 
    slog.info("alarmqueue.size = {0}, alarm_queue_high.size = {1}".format(ALARMQ.qsize(), ALARMQ_HIGH.qsize()))

def put_alarmq(alarm_payload):
    global ALARMQ 
    try:
        ALARMQ.put(alarm_payload, block=True, timeout =2)
        slog.info("put send_queue:{0} size:{1}, item:{2}".format(ALARMQ, ALARMQ.qsize(),json.dumps(alarm_payload)))
    except Exception as e:
        slog.info("queue full, drop alarm_payload")
        return False
    return True

# with high priority and reliable
def put_alarmq_high(alarm_payload):
    global ALARMQ_HIGH
    try:
        ALARMQ_HIGH.put(alarm_payload, block=True, timeout =2)
        slog.info("put alarm_queue_high:{0} size:{1} item:{2}".format(ALARMQ_HIGH, ALARMQ_HIGH.qsize(),json.dumps(alarm_payload)))
    except Exception as e:
        slog.info("queue full, drop alarm_payload")
        return False
    return True
    
# grep broadcast log
def grep_log_broadcast(line):
    global ALARMQ, ALARMQ_HIGH, gconfig, mypublic_ip_port 
    grep_broadcast = gconfig.get('grep_broadcast')

    '''
    # something like: 
    'grep_broadcast': {
        'start': 'true',
        'sample_rate': 1000,
        'network_focus_on': ['660000', '680000', '690000'], # src or dest
        'network_ignore':   ['670000'],  # src or dest
        }
    '''
    try:
        if grep_broadcast.get('start') != 'true':
            return False

        #slog.info('line: {0}'.format(line))
        send_flag = False if (line.find('alarm elect_vhost_original_send') == -1) else True
        recv_flag = False if (line.find('alarm elect_vhost_final_recv') == -1) else True
        if not send_flag and not recv_flag:
            return False

        if line.find('broadcast:1') == -1:
            slog.info('grep_broadcast found point2point')
            return False

        # do something filtering
        network_ignore = grep_broadcast.get('network_ignore')
        for ni in network_ignore:
            if line.find(ni) != -1:
                slog.info('grep_broadcast network_ignore {0}'.format(ni))
                return False
        network_focus_on = grep_broadcast.get('network_focus_on')
        nf_ret = False
        for nf in network_focus_on:
            if line.find(nf) != -1:
                nf_ret = True
                break
        if not nf_ret:
            slog.info('grep_broadcast network_focus_on get nothing')
            return False

        global_sample_rate = gconfig.get('global_sample_rate')
        sample_rate = grep_broadcast.get('sample_rate')
        if global_sample_rate < sample_rate:
            sample_rate = global_sample_rate

        packet_info = {}
        local_node_id_index  = line.find('local_node_id') 
        line = line[local_node_id_index:]
        sp_line = line.split()
        for item in sp_line:
            sp_item = item.split(':')
            key = sp_item[0]
            value = sp_item[1]
            packet_info[key] = value

        chain_hash = int(packet_info.get('chain_hash'))
        #uniq_key = '{0}_{1}_{2}'.format(chain_hash, packet_info.get('src_node_id')[-10:], packet_info.get('dest_node_id')[-10:]) # TODO(smaug) for 01000 broadcast, dest_node_id maybe changed
        uniq_key = '{0}_{1}_{2}'.format(chain_hash, packet_info.get('src_node_id')[-10:], packet_info.get('chain_msgid'))
        uniq_chain_hash = int(hashlib.sha256(uniq_key.encode('utf-8')).hexdigest(),16)  % ( 10 ** 19)
        packet_info['uniq_chain_hash'] = uniq_chain_hash
        rn = uniq_chain_hash % 1000 + 1  # [1,1000]
        if rn > sample_rate:
            slog.info('grep_broadcast final sample_rate:{0} rn:{1} return'.format(sample_rate, rn))
            return False
        slog.info('grep_broadcast final sample_rate:{0} rn:{1} go-on'.format(sample_rate, rn))

        packet_info['public_ip'] = mypublic_ip_port.split(':')[0] 
        #slog.info(packet_info)
        alarm_payload = {
                'alarm_type': grep_broadcast.get('alarm_type'),
                'alarm_content': packet_info,
                }

        put_alarmq(alarm_payload)
    except Exception as e:
        slog.info("grep_log exception: {0} line:{1}".format(e, line))
        return False
    return True

# grep network nodes size log
def grep_log_networksize(line):
    global ALARMQ, ALARMQ_HIGH, gconfig, NodeIdMap, mypublic_ip_port, my_root_id
    grep_networksize= gconfig.get('grep_networksize')

    '''
    # something like: 
    'grep_networksize': {
        'start': 'true',
        'sample_rate': 1000,
        'alarm_type': 'networksize',
        }
    '''

    '''
    xnetwork-13:34:56.282-T26368:[Keyfo]-(): <bluert 670000..01f2ed> [67000000ff7fff7fffffffffffffffff00000000d2912dd96c4eced1f2d603506601f2ed][9079116111273787495][103][0][255][127][255][31][1] has nodes_ size(nodes size):128,set_size:128,ip:192.168.0.99,port:9000,heart_size:128,all_ips:[192.168.0.100:9000,192.168.0.101:9000,
    '''
    try:
        if grep_networksize.get('start') != 'true':
            return False

        #slog.info('line: {0}'.format(line))
        flag = (line.find('nodes_ size') != -1) and (line.find('set_size:') != -1)
        if not flag:
            return False

        sample_rate = grep_networksize.get('sample_rate')

        #node_id_index = line.find('bluert') + 24
        node_id_index = line.find('> [')
        if node_id_index == -1:
            return False
        node_id_index += 3
        node_id = line[node_id_index:node_id_index + 72]  # hex node_id size is 72

        ip_index = line.find('ip:') + 3
        ip_end_index = line.find(',port')
        ip = line[ip_index:ip_end_index]   # 192.168.0.99
        port_index = line.find('port:') + 5
        port_end_index = line.find(',heart_size')
        port = line[port_index:port_end_index]  # 9000
        if int(port) <= 0:
            return False

        if ip != mypublic_ip_port.split(':')[0]:
            mypublic_ip_port = '{0}:{1}'.format(ip, port)
            slog.info('local update public_ip:{0}'.format(mypublic_ip_port))
        if not my_root_id and node_id.startswith('010000'):
            my_root_id = node_id
            slog.info('local update root_id:{0}'.format(my_root_id))

        net_size_index = line.find('set_size:')
        net_size_end_index = line.find(',ip')
        net_size = line[net_size_index+9:net_size_end_index]

        now = int(time.time())
        tmp_remove = []
        for (k,v) in NodeIdMap.items():
            if k == node_id:
                NodeIdMap[k] = now
            if (now - v) > 60: # 60s count, node_id(k) maybe unregister
                tmp_remove.append(k)

        node_id_status = 'normal'  # normal, add, remove, dead

        # attention: handle not exist node, not limit by sample rate
        for rm_node_id in tmp_remove:
            if rm_node_id.startswith('0100'):
                node_id_status = 'dead'
            else:
                node_id_status = 'remove'
            content = {
                    'node_id': rm_node_id,
                    'node_ip': ip+":"+port,
                    'node_id_status': node_id_status,
                    'send_timestamp': int(time.time() * 1000)
                    }
            alarm_payload = {
                    'alarm_type': grep_networksize.get('alarm_type'),
                    'alarm_content': content,
                    }
            slog.info('grep_networksize remove node_id alarm_payload: {0}'.format(json.dumps(alarm_payload)))
            put_alarmq_high(alarm_payload)
            NodeIdMap.pop(rm_node_id)

        node_id_status = 'normal'  # normal, add, remove, dead
        if node_id not in NodeIdMap:
            node_id_status = 'add'
            NodeIdMap[node_id] = now

        if node_id_status == 'normal':
            rn = random.randint(0,100000000) % 1000 + 1  # [1,1000]
            if rn > sample_rate and node_id_status == 'normal':
                slog.info('grep_networksize final sample_rate:{0} rn:{1} return'.format(sample_rate, rn))
                return False
            slog.info('grep_networksize final sample_rate:{0} rn:{1} go-on'.format(sample_rate, rn))

        content = {
                'node_id': node_id,
                'node_ip': ip+":"+port,
                'node_id_status': node_id_status,
                }
        alarm_payload = {
                'alarm_type': grep_networksize.get('alarm_type'),
                'alarm_content': content,
                }
        slog.info('grep_networksize alarm_payload: {0}'.format(json.dumps(alarm_payload)))
        put_alarmq(alarm_payload)
    except Exception as e:
        slog.info("grep_log_networksize exception: {0} line:{1}".format(e, line))
        return False
    return True


# grep point2point log
def grep_log_point2point(line):
    global ALARMQ, ALARMQ_HIGH, gconfig, mypublic_ip_port 
    grep_point2point = gconfig.get('grep_point2point')

    '''
    # something like: 
    'grep_point2point': {
        'start': 'false',
        'sample_rate': 1000,
        'network_focus_on': ['660000', '680000', '690000'], # src or dest
        'network_ignore':   ['670000'],  # src or dest
        },
    '''
    try:
        if grep_point2point.get('start') != 'true':
            return False

        #slog.info('line: {0}'.format(line))
        send_flag = False if (line.find('alarm elect_vhost_original_send') == -1) else True
        recv_flag = False if (line.find('alarm elect_vhost_final_recv') == -1) else True
        if not send_flag and not recv_flag:
            return False

        if line.find('broadcast:0') == -1:
            slog.info('grep_point2point found broadcast')
            return False

        # do something filtering
        network_ignore = grep_point2point.get('network_ignore')
        for ni in network_ignore:
            if line.find(ni) != -1:
                slog.info('grep_point2point network_ignore {0}'.format(ni))
                return False
        network_focus_on = grep_point2point.get('network_focus_on')
        nf_ret = False
        for nf in network_focus_on:
            if line.find(nf) != -1:
                nf_ret = True
                break
        if not nf_ret:
            slog.info('grep_point2point network_focus_on get nothing')
            return False

        global_sample_rate = gconfig.get('global_sample_rate')
        sample_rate = grep_point2point.get('sample_rate')
        if global_sample_rate < sample_rate:
            sample_rate = global_sample_rate

        packet_info = {}
        local_node_id_index  = line.find('local_node_id') 
        line = line[local_node_id_index:]
        sp_line = line.split()
        for item in sp_line:
            sp_item = item.split(':')
            key = sp_item[0]
            value = sp_item[1]
            packet_info[key] = value


        chain_hash = int(packet_info.get('chain_hash'))
        uniq_key = '{0}_{1}_{2}'.format(chain_hash, packet_info.get('src_node_id')[-10:], packet_info.get('dest_node_id')[-10:])
        uniq_chain_hash = int(hashlib.sha256(uniq_key.encode('utf-8')).hexdigest(),16)  % ( 10 ** 19)
        packet_info['uniq_chain_hash'] = uniq_chain_hash
        rn = uniq_chain_hash % 1000 + 1  # [1,1000]
        if rn > sample_rate:
            slog.info('grep_point2point final sample_rate:{0} rn:{1} return'.format(sample_rate, rn))
            return False
        slog.info('grep_point2point final sample_rate:{0} rn:{1} go-on'.format(sample_rate, rn))
        #slog.info(packet_info)

        packet_info['public_ip'] = mypublic_ip_port.split(':')[0]
        alarm_payload = {
                'alarm_type': grep_point2point.get('alarm_type'),
                'alarm_content': packet_info,
                }
        put_alarmq(alarm_payload)

    except Exception as e:
        slog.info("grep_log exception: {0} line:{1}".format(e, line))
        return False
    return True

def check_progress(filename):
    global  gconfig, mark_down_flag, mypublic_ip_port, my_root_id
    if mark_down_flag:
        return False
    cmd = 'ps -ef |grep xtopchain |grep -v grep'
    #cmd = 'lsof {0} |grep xtopchain'.format(filename)
    result = os.popen(cmd).readlines()
    if result:
        return False
    slog.warn('xtopchain down!! xtopchain down!! xtopchain down!! filename:{0}'.format(filename))

    mark_down_flag = True
    alarm_payload = {
            'alarm_type': gconfig.get('grep_networksize').get('alarm_type'),
            'alarm_content': {
                'node_ip': mypublic_ip_port,
                'node_id': my_root_id,
                'node_id_status': 'dead',
                'send_timestamp': int(time.time() * 1000),
                'info': 'xtopchain down!'
                },
            }
    put_alarmq_high(alarm_payload)
    return True


def grep_log(line):
    global mark_down_flag
    mark_down_flag = False  # TODO(smaug) using a better way to handle xtopchain down flag
    # TODO(smaug) better performance(reduce find)
    ret1 = grep_log_broadcast(line)
    ret2 = grep_log_point2point(line)
    ret3 = grep_log_networksize(line)



    if ret1 or ret2 or ret3:
        print_queue()
    return ALARMQ.qsize(), ALARMQ_HIGH.qsize()

def watchlog(filename, offset = 0):
    try:
        #log_handle = open(filename, 'r',encoding="utf-8", errors='replace')
        #log_handle = open(filename, 'r',encoding="utf-8")
        log_handle = open(filename, 'r',encoding="latin-1")
    except Exception as e:
        slog.info("open file exception: {0}".format(e))
        return offset

    wait_num = 0
    #log_handle.seek(0, 2)   # go to end
    log_handle.seek(offset, 0)   # go to offset from head
    cur_pos = log_handle.tell()
    while True:
        cur_pos = log_handle.tell()
        try:
            line = log_handle.readline()
        except Exception as e:
            slog.info("readline exception:{0}, cur_pos:{1}".format(e, cur_pos))
            continue
        if not line:
            wait_num += 1
            log_handle.seek(cur_pos)  # go to cur_pos from head
            time.sleep(1)
            slog.info("sleep 1 s, cur_pos: {0}".format(cur_pos))
            print_queue()
            if wait_num > 4:
                slog.info("file: {0} done watch, size: {1}".format(filename, cur_pos))
                break
        else:
            send_size, recv_size = grep_log(line)
            wait_num = 0

    # judge new file "$filename" created
    if not os.path.exists(filename):
        return cur_pos
    try:
        new_log_handle = open(filename, 'r',encoding="latin-1")
    except Exception as e:
        return cur_pos

    new_log_handle.seek(0, 2)   # go to end
    new_size = new_log_handle.tell()
    if new_size > cur_pos:
        return cur_pos
    if new_size == cur_pos:
        slog.info('logfile:{0} maybe stopped'.format(filename))
        check_progress(filename)
        return cur_pos

    # new file "$filename" created
    slog.info("new file: {0} created".format(filename))
    return 0

def run_watch(filename = './xtop.log'):
    global ALARMQ,ALARMQ_HIGH 
    clear_queue()
    offset = 0
    while True:
        time.sleep(1)
        offset = watchlog(filename, offset)
        slog.info("grep_log finish, alarmqueue.size = {0} alarmq_high.size = {1}, offset = {2}".format(ALARMQ.qsize(), ALARMQ_HIGH.qsize(), offset))

def do_alarm(alarm_list):
    global alarm_proxy_host
    url = 'http://' + alarm_proxy_host
    url = urljoin(url, '/api/alarm/')
    my_headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
            'Content-Type': 'application/json;charset=UTF-8',
            }
    #my_data = json.dumps(alarm_list)
    my_data = {
            'token': 'testtoken',
            'data': []
            }
    my_data['data'] = alarm_list
    my_data = json.dumps(my_data)
    slog.info("do_alarm: {0}".format(my_data))
    try:
        #res = requests.post(url, headers = my_headers,data = my_data, timeout = 5)
        res = mysession.post(url, headers = my_headers,data = my_data, timeout = 5)
        if res.status_code == 200:
            if res.json().get('status') == 0:
                slog.info("send alarm ok, response: {0}".format(res.text))
                return True
            else:
                slog.info("send alarm fail, response: {0}".format(res.text))
        else:
            slog.info('send alarm fail: {0}'.format(res.text))
    except Exception as e:
        slog.info("exception: {0}".format(e))

    return False

def system_cron_job():
    global ALARMQ, ALARMQ_HIGH, gconfig, mypublic_ip_port
    time_step = 2 * 60
    pid = None
    band_watcher = BandwidthWatch(time_step = time_step)
    cpu_watcher  = CpuWatch(time_step = time_step)
    
    alarm_content = {
            'cpu':0,
            'recv_bandwidth':0,
            'send_bandwidth':0,
            'recv_packet':0,
            'send_packet':0,
            }
    alarm_type = gconfig.get('system_cron').get('alarm_type')
    cpu_info_old = {}
    band_info_old = {}
    while True:
        if mypublic_ip_port == '127.0.0.1:800':
            time.sleep(1)
            continue

        if not cpu_info_old:
            cpu_info_old = cpu_watcher.read_cpu()
        if not band_info_old:
            band_info_old = band_watcher.read_net(pid = pid)
        time.sleep(time_step)

        now = int(int(time.time()) / time_step) * time_step  # belong time

        if gconfig.get('system_cron').get('start') != 'true':
            continue

        # watch cpu
        cpu_info = cpu_watcher.read_cpu()
        cpu_result = cpu_watcher.get_avg_cpu(cpu_info_old, cpu_info)
        cpu_info_old = copy.deepcopy(cpu_info)

        # watch bandwidth
        band_info = band_watcher.read_net(pid = pid)
        net_results = band_watcher.get_avg_bandwidth(band_info_old, band_info)
        net_result = {}
        for k,v in net_results.items():
            net_result = v
        band_info_old = copy.deepcopy(band_info)

        alarm_content['cpu'] = 100 - cpu_result.get('cpu_idle')
        alarm_content['recv_bandwidth'] = net_result.get('recv_bandwidth')
        alarm_content['send_bandwidth'] = net_result.get('send_bandwidth')
        alarm_content['recv_packet']    = net_result.get('recv_packet')
        alarm_content['send_packet']    = net_result.get('send_packet')
        alarm_content['send_timestamp'] = int(now * 1000)
        alarm_content['public_ip_port'] = mypublic_ip_port

        alarm_payload = {
                'alarm_type': alarm_type,
                'alarm_content': alarm_content,
                }

        slog.debug('run system_cron_job ok:{0}'.format(json.dumps(alarm_payload)))
        put_alarmq(alarm_payload)
    return

 

def consumer_alarm():
    global ALARMQ, ALARMQ_HIGH, gconfig
    alarm_pack_num = gconfig.get('alarm_pack_num')
    th_name = threading.current_thread().name
    alarm_list = []
    while True:
        try:
            slog.info("consumer thread:{0} send_queue:{1} size:{2}".format(th_name, ALARMQ, ALARMQ.qsize()))
            while not ALARMQ.empty():
                alarm_payload = ALARMQ.get()
                alarm_list.append(alarm_payload)

                if len(alarm_list) >= alarm_pack_num:
                    slog.info("alarm do_alarm")
                    do_alarm(alarm_list)
                    alarm_list.clear()

            time.sleep(1)
        except Exception as e:
            pass

def consumer_alarm_high():
    global ALARMQ, ALARMQ_HIGH, gconfig
    th_name = threading.current_thread().name
    alarm_pack_num = gconfig.get('alarm_pack_num')
    alarm_pack_num = 1
    alarm_list = []
    while True:
        try:
            slog.info("consumer thread:{0} recv_queue:{1} size:{2}".format(th_name, ALARMQ_HIGH, ALARMQ_HIGH.qsize()))
            while not ALARMQ_HIGH.empty():
                alarm_payload = ALARMQ_HIGH.get()
                alarm_list.append(alarm_payload)

                if len(alarm_list) >= alarm_pack_num:
                    slog.info("alarm_high do_alarm")
                    if not do_alarm(alarm_list):
                        slog.warn("alarm_high send failed, put in queue again")
                        for item in alarm_list:
                            put_alarmq_high(item)
                    alarm_list.clear()

            time.sleep(1)
        except Exception as e:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.description='TOP-Argus Agent，拉取远程配置，报警采集并上报'
    parser.add_argument('-a', '--alarm', help='alarm proxy host, agent pull config and push alarm to this proxy host, eg: 127.0.0.1:9090', default='127.0.0.1:9090')
    parser.add_argument('-f', '--file', help="log file for agent to watch, eg: ./xtop.log", default='./xtop.log')
    args = parser.parse_args()

    if args.alarm.find(':') == -1:
        slog.error('alarm proxy host invalid')
        sys.exit()

    alarm_proxy_host = args.alarm
    alarm_filename = args.file
    start_print = 'agent start... host:{0} file:{1}\n'.format(alarm_proxy_host, alarm_filename)
    slog.info(start_print)
    print(start_print)

    if update_config_from_remote():
        slog.warn('using remote config to start: {0}'.format(json.dumps(gconfig)))
    else:
        slog.error('using local config to start: {0}'.format(json.dumps(gconfig)))


    #run_watch(alarm_filename)

    update_config_th = threading.Thread(target = update_config)
    update_config_th.start()
    slog.info('start update config from remote thread')

    watchlog_th = threading.Thread(target = run_watch, args = (alarm_filename, ))
    watchlog_th.start()
    slog.info("start watchlog thread")

    sys_cron_th = threading.Thread(target = system_cron_job)
    sys_cron_th.start()
    slog.info("start system_cron_job thread")


    con_send_th = threading.Thread(target = consumer_alarm)
    con_send_th.start()
    slog.info("start consumer_alarm thread")


    con_recv_th = threading.Thread(target = consumer_alarm_high)
    con_recv_th.start()
    slog.info("start consumer_alarm_high thread")

    slog.info('main thread wait...')
    watchlog_th.join()
    con_send_th.join()
    con_recv_th.join()
