import json
import sys
import threading
import time

import grpc
from concurrent import futures
from proto import store_pb2
from proto import store_pb2_grpc
import yaml


class SlaveNode(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, config_file, slave_id):
        self.stub = store_pb2_grpc.KeyValueStoreStub(grpc.insecure_channel(f"127.0.0.1:32770"))
        self.data = {}
        self.temp_data = {}
        self.slave_id = slave_id
        self.ip = ''
        self.port = ''
        self.seconds = 0
        self.mutex = threading.Lock()
        self.load_config(config_file)
        self.load_data()

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            slave_config = next((item for item in config['slaves'] if item['id'] == self.slave_id), None)
            if slave_config:
                self.ip = slave_config['ip']
                self.port = slave_config['port']
            else:
                raise ValueError(f"No configuration found for slave ID: {self.slave_id}")

    def load_data(self):
        try:
            with open(f'db/{slave_id}_data.json', 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {}

    def save_data(self):
        with open(f'db/{slave_id}_data.json', 'w') as f:
            json.dump(self.data, f)

    def canCommit(self, request, context):
        # print("CanCommit")
        # Prepare phase: Store the data temporarily
        self.temp_data[request.key] = request.value
        return store_pb2.CommitResponse(success=True)

    def doCommit(self, request, context):
        # print("doCommit")
        # Commit phase: Move the data from temporary to permanent storage
        self.data.update(self.temp_data)
        self.temp_data = {}
        self.save_data()
        # print(self.data)
        return store_pb2.CommitResponse(success=True)

    def abort(self, request, context):
        print("doAbort")
        # Abort phase: Clear the temporary data
        self.temp_data = {}
        return store_pb2.DoAbortResponse(success=True)

    def get(self, request, context):
        time.sleep(self.seconds)
        key = request.key
        value = self.data.get(key)
        return store_pb2.GetResponse(value=value, found=True)

    def slowDown(self, request, context):
        self.seconds = request.seconds
        return store_pb2.SlowDownResponse(success=True)

    def restore(self, request, context):
        self.seconds = 0
        return store_pb2.RestoreResponse(success=True)


def serve(slave_id):
    slave_node = SlaveNode('centralized_config.yaml', slave_id)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(slave_node, server)
    server.add_insecure_port(f"{slave_node.ip}:{slave_node.port}")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise Exception("Usage: python slave_nodev2.py <slave_id>")
    slave_id = sys.argv[1]
    serve(slave_id)
