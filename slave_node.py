import sys

import grpc
from concurrent import futures
from proto import store_pb2
from proto import store_pb2_grpc
import yaml


class SlaveNode(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, config_file, slave_id):
        self.data = {}
        self.slave_id = slave_id
        self.ip = ''
        self.port = ''
        self.load_config(config_file)

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            slave_config = next((item for item in config['slaves'] if item['id'] == self.slave_id), None)
            if slave_config:
                self.ip = slave_config['ip']
                self.port = slave_config['port']
            else:
                raise ValueError(f"No configuration found for slave ID: {self.slave_id}")


def serve(slave_id):
    slave_node = SlaveNode('centralized_config.yaml', slave_id)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(slave_node, server)
    server.add_insecure_port(f"{slave_node.ip}:{slave_node.port}")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise Exception("Usage: python slave_node.py <slave_id>")
    slave_id = sys.argv[1]
    serve(slave_id)
