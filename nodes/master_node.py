import json
import logging
import time
import grpc

from proto import store_pb2
from proto import store_pb2_grpc


class MasterNode(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, lock, data, slaves):
        self.lock = lock  # Mutex
        self.data = data  # Load data from database
        self.seconds = 0  # Delay
        self.slaves = slaves

        # Internal params
        self.logger = self.setup_logger()
        self.channels, self.stubs = self.setup_stubs_and_channels()

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

    def wait_for_server(self, channel, timeout=15):
        """Wait until the server is available or the timeout is reached."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                grpc.channel_ready_future(channel).result(timeout=1)
                return True
            except grpc.FutureTimeoutError:
                continue
        return False

    def setup_stubs_and_channels(self):
        """Create and return gRPC channels and stubs for the specified nodes."""
        channels = []
        stubs = []
        for slave in self.slaves:
            print(slave)
            channel_address = f"{slave['ip']}:{slave['port']}"
            channel = grpc.insecure_channel(channel_address)
            if not self.wait_for_server(channel):
                self.logger.error(f"The gRPC server ({channel_address}) is not available after the timeout.")
                raise Exception(f"Failed to connect to the gRPC server ({channel_address}).")
            channels.append(channel)
            stubs.append(store_pb2_grpc.KeyValueStoreStub(channel))
        return channels, stubs

    # Save data to database 'master_data.json'
    def save_data(self):
        with open(f'db/centralized/master_data.json', 'w') as f:
            json.dump(self.data, f)

    # Slowdown Master
    def slowDown(self, request, context):
        self.seconds = request.seconds
        return store_pb2.SlowDownResponse(success=True)

    # Restore slowdown Master
    def restore(self, request, context):
        self.seconds = 0
        return store_pb2.RestoreResponse(success=True)

    def get(self, request, context):
        time.sleep(self.seconds)
        key = request.key
        found = False
        with self.lock:
            value = self.data.get(key)
            if value is None:
                found = True
        return store_pb2.GetResponse(value=value, found=found)

    def send_request_to_slaves(self, request, method_name):
        responses = []
        for stub in self.stubs:
            method = getattr(stub, method_name)
            # with self.lock:
            response = method(request)
            responses.append(response)
        return responses

    def put(self, request, context):
        if request.key is None or request.key == "" and request.value is None or request.value == "":
            self.logger.info("Key/Value is None")
            return store_pb2.CommitResponse(success=False)

        key, value = request.key, request.value
        time.sleep(self.seconds)
        with self.lock:

            # Phase 1: Voting phase
            # CanCommit
            can_commit_request = store_pb2.CanCommitRequest(key=key, value=value)
            can_commit_responses = self.send_request_to_slaves(can_commit_request, 'canCommit')

            if any(response is None or not response.vote for response in can_commit_responses):
                print("canCommit failed. Coordinator voted NO.")
                if can_commit_responses[0].value == can_commit_responses[1].value:
                    do_abort_request = store_pb2.DoAbortRequest(key=key,
                                                                value=can_commit_responses[0].value)
                    self.send_request_to_slaves(do_abort_request, 'doAbort')
                else:
                    self.logger.error("CAN COMMIT VALUES DIFFER")
                    self.logger.info(can_commit_responses)

                return store_pb2.CommitResponse(success=False)

            # Phase 2: Commit phase
            # DoCommit
            do_commit_request = store_pb2.DoCommitRequest(key=key, value=value)
            do_commit_responses = self.send_request_to_slaves(do_commit_request, 'doCommit')

            # DoCommit OK
            if all(response is not None and response.success for response in do_commit_responses):
                # Store value in master
                # with self.lock:
                self.data[key] = value
                self.save_data()
                return store_pb2.CommitResponse(success=True)
            else:
                return store_pb2.CommitResponse(success=False)
