import grpc
import json
import os
import sys
import time
from enum import Enum
import threading
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import grpclib.xrpc_pb2 as xpb
import grpclib.xrpc_pb2_grpc as xgrpc


def get_sync_overview(dst) :
    with grpc.insecure_channel(dst) as channel:
        stub = xgrpc.xrpc_serviceStub(channel)
        action = "get_sync_overview"
        body = {
        "action": 'get_sync_overview'
        }
        print('[get_sync_overview] >> %s' % json.dumps(body))
        response = stub.call(xpb.xrpc_request(action=action, body=json.dumps(body)))
    try:
        rb = json.loads(response.body)
        print("[get_sync_overview response] << %s" % rb)
        return rb
    except Exception as e:
        print(e)
        return None

def get_sync_detail(dst) :
    with grpc.insecure_channel(dst) as channel:
        stub = xgrpc.xrpc_serviceStub(channel)
        action = "get_sync_detail"
        body = {
        "action": 'get_sync_detail'
        }
        print('[get_sync_detail] >> %s' % json.dumps(body))
        response = stub.call(xpb.xrpc_request(action=action, body=json.dumps(body)))
    try:
        rb = json.loads(response.body)
        print("[get_sync_detail response] << %s" % rb)
        return rb
    except Exception as e:
        print(e)
        return None

if __name__ == "__main__":
    pass
