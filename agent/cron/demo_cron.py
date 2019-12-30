#!/usr/bin/env python
# -*- coding:utf-8 -*-

import json

class DemoCron(object):
    def __init__(self):
        # TODO(user) do something init

        # attention this is really import; every alarm should belong to one type
        self.type_ = 'demo'

        self.result_ = {}
        return

    def capture_data(self):
        # TODO(user) do something capture data
        self.result_ = {
                'type': self.type_,
                'key1': 'value1',
                'key2': 'value2',
                'key3': 'value3',
                }
        return

    def get_data(self):
        return self.result_



demo_cron_obj = DemoCron()
result = demo_cron_obj.get_data()

print(json.dumps(result))
