import json
import time

import grpc
from proto import store_pb2
from proto import store_pb2_grpc
import yaml


class SlaveNode(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, config_file, slave_id, lock, slave_data):
        self.stub = store_pb2_grpc.KeyValueStoreStub(grpc.insecure_channel(f"127.0.0.1:32770"))
        self.data = slave_data    # Load data from database
        self.temp_data = {}
        self.slave_id = slave_id
        self.ip = ''
        self.port = ''
        self.seconds = 0
        self.lock = lock
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

    def save_data(self):
        with open(f'db/{self.slave_id}_data.json', 'w') as f:
            json.dump(self.data, f)

    def canCommit(self, request, context):
        # Vote YES and save to local storage the initial value
        self.temp_data[request.key] = request.value
        return store_pb2.CanCommitResponse(vote=True)

    def canCommitFailed(self, request, context):
        # Delete temporary data
        self.temp_data = {}
        return store_pb2.DoAbortResponse(success=True)

    def doCommit(self, request, context):

        # If data was previously saved in temporary storage
            if request.value in self.temp_data.values():
                # Move the data from temporary to permanent storage
                with self.lock:
                    self.data.update(self.temp_data)
                    self.save_data()

                # Restore temp data to None
                self.temp_data = {}

                return store_pb2.CommitResponse(success=True)
            else:
                return store_pb2.CommitResponse(success=False)

    def doCommitFailed(self, request, context):
        # Delete temporary data
        if self.data.get(request.key) is not None:
            with self.lock:
                del self.data[request.key]
                self.save_data()
            return store_pb2.DoAbortResponse(success=True)
        return store_pb2.Empty()

    def abort(self, request, context):
        print("doAbort")
        # Abort phase: Clear the temporary data
        self.temp_data = {}
        return store_pb2.DoAbortResponse(success=True)

    def get(self, request, context):
        time.sleep(self.seconds)
        key = request.key
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
