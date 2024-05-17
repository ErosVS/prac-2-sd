import json
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
        self.delay = 0
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        self.ip = config['master']['ip']
        self.port = config['master']['port']
        self.slaves = config['slaves']
        self.load_data()

    def _send_to_all_slaves(self, method, request):
        responses = []
        for slave in self.slaves:
            with grpc.insecure_channel(f'localhost:{slave["port"]}') as channel:
                stub = store_pb2_grpc.KeyValueStoreStub(channel)
                response = getattr(stub, method)(request)
                responses.append(response)
        return responses

    def load_data(self):
        try:
            with open(f'db/master_data.json', 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {}

    def save_data(self):
        with open(f'db/master_data.json', 'w') as f:
            json.dump(self.data, f)

    def put(self, request, context):
        key, value = request.key, request.value
        time.sleep(self.delay)

        # Phase 1: Prepare phase
        can_commit_request = store_pb2.CanCommitRequest(key=key, value=value)
        can_commit_response = self._send_to_all_slaves('canCommit', can_commit_request)
        # Case: Abort
        if not all(response.success for response in can_commit_response):
            print("Aborting in master after canCommit")
            abort_request = store_pb2.DoAbortRequest()
            self._send_to_all_slaves('doAbort', abort_request)
            return store_pb2.CommitResponse(success=False)

        # Phase 2: Commit phase
        print("Start Commit")
        do_commit_request = store_pb2.DoCommitRequest(key=key, value=value)
        do_commit_responses = self._send_to_all_slaves('doCommit', do_commit_request)
        if all(response.success for response in do_commit_responses):
            # Store value in master
            self.data[key] = value
            self.save_data()
            return store_pb2.CommitResponse(success=True)
        else:
            print("Aborting in master after doCommit")
            abort_request = store_pb2.DoAbortRequest()
            self._send_to_all_slaves('abort', abort_request)
            return store_pb2.CommitResponse(success=False)

    def get(self, request, context):
        key = request.key
        time.sleep(self.delay)
        value = self.data.get(key)
        return store_pb2.GetResponse(value=value, found=True)

    def slowDown(self, request, context):
        self.delay = request.delay
        return store_pb2.SlowdownResponse(success=True)

    def restore(self, request, context):
        self.delay = 0
        return store_pb2.RestoreResponse(success=True)


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
