#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
import copy
import time
import datetime
import os

class BandwidthWatch(object):
    def __init__(self, time_step):
        self.netfile_ = '/proc/net/dev'
        self.watch_time_step_ = time_step  # 60 s
        self.interface_name_ = 'eth0'  # by default

        return

    def read_net(self, pid = None):
        band_info = {}
        netfile = self.netfile_
        if pid:
            netfile = '/proc/{0}/net/dev'.format(pid)

        ifstat = open(netfile).readlines()
        sp =  []
        for i in range(2, len(ifstat) - 1):
            interface = ifstat[i]
            sp = interface.split()
            if len(sp) < 10:
                continue
            interface_name = sp[0][:-1]   #eth0 
            if interface_name ==  'lo':
                # 127.0.0.1
                continue
            self.interface_name_ = interface_name
            # found eth0 or something like eth0
            print('found interface:{0}'.format(self.interface_name_))
            break

        if not sp:
            return None 
        print(sp)
        status = {
                'recv_bytes': int(sp[1]),
                'recv_packet': int(sp[2]),
                'send_bytes': int(sp[9]),
                'send_packet': int(sp[10])
                }
        if pid == None:
            band_info[self.interface_name_] = status
        else:
            band_info[pid] = status
        return band_info

    def get_avg_bandwidth(self, band_info_old, band_info):
        if not band_info_old or not band_info:
            return None
        result = {}
        if set(band_info.keys()) != set(band_info_old.keys()):
            return None
        for k in list(band_info.keys()):
            # step
            step_recv_bytes  = band_info.get(k).get('recv_bytes')  - band_info_old.get(k).get('recv_bytes')
            step_recv_packet = band_info.get(k).get('recv_packet') - band_info_old.get(k).get('recv_packet')
            step_send_bytes  = band_info.get(k).get('send_bytes')  - band_info_old.get(k).get('send_bytes')
            step_send_packet = band_info.get(k).get('send_packet') - band_info_old.get(k).get('send_packet')
    
            recv_bandwidth = int(float(step_recv_bytes * 8) / 1000 / self.watch_time_step_)  # Kb/s
            send_bandwidth = int(float(step_send_bytes * 8) / 1000 / self.watch_time_step_)  # Kb/s 
            recv_qps = int(step_recv_packet / self.watch_time_step_)
            send_qps = int(step_send_packet / self.watch_time_step_)

            result[k] = {
                    'recv_bandwidth': recv_bandwidth,
                    'send_bandwidth': send_bandwidth,
                    'recv_packet': recv_qps,
                    'send_packet': send_qps
                    }

        return result
    
    def run(self, pid = None):
        band_info_old = {}
        while True:
            if not band_info_old:
                band_info_old = self.read_net(pid = pid)
            time.sleep(self.watch_time_step_)
            band_info = self.read_net(pid = pid)
            result = self.get_avg_bandwidth(band_info_old, band_info)

            now = datetime.datetime.now()
            nowstr = '{0}:{1}:{2}.{3}'.format(now.hour, now.minute, now.second, now.microsecond/1000)
            for k,v in result.items():
                line1 = "\n{0}:############\n".format(k)
                line2 = "{0}:{1} Recv: {2} Kb/s; {3} qps\n".format(k, nowstr, v.get('recv_bandwidth'), v.get('recv_packet'))
                line3 = "{0}:{1} Send: {2} Kb/s; {3} qps\n".format(k, nowstr, v.get('send_bandwidth'), v.get('send_packet'))
                line4 = "{0}:#############\n".format(k)
                print(line1)
                print(line2)
                print(line3)
                print(line4)

            band_info_old = copy.deepcopy(band_info)
    

if __name__ == '__main__':
    pid = None
    if len(sys.argv) == 2:
        pid = int(sys.argv[1])

    band_watcher = BandwidthWatch(time_step = 5)
    band_watcher.run(pid)


