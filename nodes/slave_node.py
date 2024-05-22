import json
import logging
import os
import time

import yaml

from proto import store_pb2_grpc, store_pb2


class SlaveNode(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, lock, data, slave_id):
        self.lock = lock  # Mutex
        self.data = data  # Load data from database
        self.slave_id = slave_id
        self.seconds = 0  # Delay

        # Internal params
        self.logger = self.setup_logger()
        self.temp_data = {}

    def setup_logger(self):
        # Configure and return a logger
        logger = logging.getLogger(self.__class__.__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        return logger

    # Save data to database 'node_id_data.json'
    def save_data(self):
        with open(f'db/{self.slave_id}_data.json', 'w') as f:
            json.dump(self.data, f)

    def slowDown(self, request, context):
        self.seconds = request.seconds
        return store_pb2.SlowDownResponse(success=True)

        # Restore slowdown Master

    def restore(self, request, context):
        self.seconds = 0
        return store_pb2.RestoreResponse(success=True)

    def get(self, request, context):
        # time.sleep(self.seconds)
        key = request.key
        found = False
        with self.lock:
            value = self.data.get(key)
            if value is None:
                found = True
        return store_pb2.GetResponse(value=value, found=found)

    def canCommit(self, request, context):
        # time.sleep(self.seconds)
        # Vote YES and save to local storage the initial value
        self.temp_data[request.key] = request.value
        previous_value = None
        if request.key in self.data:
            previous_value = self.data[request.key]
        return store_pb2.CanCommitResponse(vote=True, previous_value=previous_value)

    def doCommit(self, request, context):
        # If data was previously saved in temporary storage
        if request.value in self.temp_data.values():
            # Move the data from temporary to permanent storage
            with self.lock:
                self.data[request.key] = request.value
                self.save_data()
                # Restore temp data to None
                self.temp_data = {}
            return store_pb2.CommitResponse(success=True, value=self.data[request.key])
        else:
            return store_pb2.CommitResponse(success=False, value=self.data[request.key])

    def doAbort(self, request, context):
        if request.name == 'canCommit':
            # Delete temporary data
            self.temp_data = {}
            return store_pb2.DoAbortResponse(success=True)
        elif request.name == 'doCommit':

            # Delete temporary data
            if self.data.get(request.key) is not None:
                with self.lock:
                    # self.data[request.key] = request.value
                    self.save_data()
                return store_pb2.DoAbortResponse(success=True)
            return store_pb2.Empty()
