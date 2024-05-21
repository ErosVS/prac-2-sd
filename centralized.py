import json
import threading
import time

import grpc
from concurrent import futures
import yaml
from proto import store_pb2
from proto import store_pb2_grpc
from slave_node import SlaveNode


class MasterNode(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, config_file, lock):
        self.data = {}
        self.seconds = 0
        self.lock = lock
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        self.ip = config['master']['ip']
        self.port = config['master']['port']
        self.slaves = config['slaves']
        self.load_data()

    def _send_to_all_slaves(self, method, request, timeout=30):
        responses = []
        for slave in self.slaves:
            with grpc.insecure_channel(f'localhost:{slave["port"]}') as channel:
                stub = store_pb2_grpc.KeyValueStoreStub(channel)
                try:
                    response = getattr(stub, method)(request, timeout=timeout)
                    responses.append(response)
                except grpc.RpcError as e:
                    print(f"Timeout! Error contacting participant: {e}")
                    responses.append(None)
        return responses

    # Load data from database 'master_data.json'
    def load_data(self):
        try:
            with open(f'db/master_data.json', 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {}

    # Save data to database 'master_data.json'
    def save_data(self):
        with open(f'db/master_data.json', 'w') as f:
            json.dump(self.data, f)

    def put(self, request, context):
        time.sleep(self.seconds)
        key, value = request.key, request.value

        # Phase 1: Voting phase
        # CanCommit
        # TODO: Master can commit? if not, return CommitResponse False
        can_commit_request = store_pb2.CanCommitRequest(key=key, value=value)
        can_commit_response = self._send_to_all_slaves('canCommit', can_commit_request)

        # If there are failures or any vote is False
        if any(response is None or not response.vote for response in can_commit_response):
            print("canCommit failed. Coordinator voted NO.")
            self._send_to_all_slaves('canCommitFailed', store_pb2.DoAbortRequest(key=key, value=value))
            return store_pb2.CommitResponse(success=False)

        # Phase 2: Commit phase
        # DoCommit
        do_commit_request = store_pb2.DoCommitRequest(key=key, value=value)
        do_commit_responses = self._send_to_all_slaves('doCommit', do_commit_request)
        # DoCommit OK
        if all(response is not None and response.success for response in do_commit_responses):
            # Store value in master
            with self.lock:
                self.data[key] = value
                self.save_data()
            return store_pb2.CommitResponse(success=True)
        else:
            # print("DoCommit failed. Rolling back...")
            do_abort_response = False
            # Force rollback
            while not do_abort_response:
                do_abort_responses = self._send_to_all_slaves('doCommitFailed',
                                                              store_pb2.DoAbortRequest(key=key, value=value))
                if any(response is None or not response.success for response in do_abort_responses):
                    do_abort_response = True
            return store_pb2.CommitResponse(success=False)

    def get(self, request, context):
        key = request.key
        time.sleep(self.seconds)
        found = False
        with self.lock:
            value = self.data.get(key)
            if value is None:
                found = True
        return store_pb2.GetResponse(value=value, found=found)

    def slowDown(self, request, context):
        self.seconds = request.seconds
        return store_pb2.SlowDownResponse(success=True)

    def restore(self, request, context):
        self.seconds = 0
        return store_pb2.RestoreResponse(success=True)


def start_slave_nodes(lock):
    slave1_thread = threading.Thread(target=serve_slave, args=('slave_1', lock))
    slave2_thread = threading.Thread(target=serve_slave, args=('slave_2', lock))

    slave1_thread.start()
    slave2_thread.start()

    slave1_thread.join()
    slave2_thread.join()


def serve_slave(slave_id, lock):
    slave_node = SlaveNode('centralized_config.yaml', slave_id, lock)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(slave_node, server)
    server.add_insecure_port(f"{slave_node.ip}:{slave_node.port}")
    server.start()
    server.wait_for_termination()


def serve():
    config_file = 'centralized_config.yaml'
    lock = threading.Lock()
    master_node = MasterNode(config_file, lock)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(master_node, server)
    server.add_insecure_port(f"{master_node.ip}:{master_node.port}")
    server.start()
    start_slave_nodes(lock)
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
