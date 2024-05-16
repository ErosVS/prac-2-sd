import grpc
from concurrent import futures
import yaml
from proto import store_pb2
from proto import store_pb2_grpc

class MasterNode(store_pb2_grpc.KeyValueStoreServicer):
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        self.master_config = config['master']
        self.slaves = config['slaves']
        self.data = {}

    def put(self, request, context):
        key, value = request.key, request.value
        # Here you would implement the 2PC logic.
        self.data[key] = value
        return store_pb2.PutResponse(success=True)

    def get(self, request, context):
        key = request.key
        value = self.data.get(key, "")
        found = key in self.data
        return store_pb2.GetResponse(value=value, found=found)

    def slowDown(self, request, context):
        # Implement slowDown logic.
        return store_pb2.SlowDownResponse(success=True)

    def restore(self, request, context):
        # Implement restore logic.
        return store_pb2.RestoreResponse(success=True)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    master_node = MasterNode('centralized_config.yaml')
    store_pb2_grpc.add_KeyValueStoreServicer_to_server(master_node, server)
    server.add_insecure_port(f"[::]:{master_node.master_config['port']}")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
