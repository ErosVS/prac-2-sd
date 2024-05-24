import json
import time
import logging
import grpc

from proto import store_pb2
from proto import store_pb2_grpc

QUORUM_READ = 2
QUORUM_WRITE = 3


class QuorumServer(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, node_id, node_weight, data, self_peer, peers):
        self.node_id = node_id
        self.node_weight = node_weight
        self.self_peer = self_peer
        self.peers = peers
        self.seconds = 0  # Delay
        self.data = data
        # Logger
        self.logger = self.setup_logger()

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

    def slowDown(self, request, context):
        self.seconds = request.seconds
        return store_pb2.SlowDownResponse(success=True)

    # Restore slowdown Master
    def restore(self, request, context):
        self.seconds = 0
        return store_pb2.RestoreResponse(success=True)

    def get(self, request, context):
        key = request.key
        time.sleep(self.seconds)
        value = self.data.get(key)
        vote_count = self.node_weight
        quorum_reached = False

        for peer in self.peers:
            if peer != self.self_peer:
                with grpc.insecure_channel(peer) as channel:
                    stub = store_pb2_grpc.KeyValueStoreStub(channel)
                    vote_request = store_pb2.VoteRequest(key=key, value=value)
                    vote_response = stub.vote(vote_request)
                    vote_count += vote_response.weight
                    if vote_count >= QUORUM_WRITE:
                        quorum_reached = True
                        break

        if quorum_reached:
            return store_pb2.GetResponse(value=value, found=True)
        else:
            return store_pb2.GetResponse(value="", found=False)

    # Save data to database
    def save_data(self):
        with open(f'db/decentralized/{self.node_id}_data.json', 'w') as f:
            json.dump(self.data, f)

    def vote(self, request, context):
        return store_pb2.VoteResponse(weight=self.node_weight)

    def doCommit(self, request, context):
        key, value = request.key, request.value
        self.data[key] = value
        self.save_data()
        return store_pb2.CommitResponse(success=True)

    def put(self, request, context):
        key, value = request.key, request.value
        time.sleep(self.seconds)
        vote_count = self.node_weight
        quorum_reached = False
        for peer in self.peers:
            if peer != self.self_peer:
                with grpc.insecure_channel(peer) as channel:
                    stub = store_pb2_grpc.KeyValueStoreStub(channel)
                    vote_request = store_pb2.VoteRequest(key=key, value=value)
                    vote_response = stub.vote(vote_request)
                    vote_count += vote_response.weight
                    if vote_count >= QUORUM_WRITE:
                        quorum_reached = True
                        break

        # Quorum higher or equal than QUORUM_WRITE value
        if quorum_reached:
            # Save to actual node new value
            self.data[key] = value
            self.save_data()
            for peer in self.peers:
                if peer != self.self_peer:
                    with grpc.insecure_channel(peer) as channel:
                        stub = store_pb2_grpc.KeyValueStoreStub(channel)
                        commit_request = store_pb2.DoCommitRequest(key=key, value=value)
                        stub.doCommit(commit_request)
            return store_pb2.PutResponse(success=True)
        else:
            return store_pb2.PutResponse(success=False)

