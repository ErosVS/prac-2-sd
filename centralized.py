import os
import subprocess
import sys
import time

import grpc
from concurrent import futures
import yaml
from proto import store_pb2
from proto import store_pb2_grpc


class MasterNode(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, config_file):
        self.data = {}
        self.slaves = []
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        self.ip = config['master']['ip']
        self.port = config['master']['port']

    def put(self, request, context):
        key, value = request.key, request.value
        print("Key: " + key + "\nValue: " + value)

        response = store_pb2.PutResponse(
            success=True
        )
        return response


def start_slave_nodes():
    server_script_path = './slave_node.py'
    subprocess.Popen([sys.executable, server_script_path, 'slave_1'])
    subprocess.Popen([sys.executable, server_script_path, 'slave_2'])


def serve():
    config_file = 'centralized_config.yaml'
    master_node = MasterNode(config_file)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(master_node, server)
    server.add_insecure_port(f"{master_node.ip}:{master_node.port}")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    start_slave_nodes()
    serve()
