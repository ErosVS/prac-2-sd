import grpc
from proto import store_pb2
from proto import store_pb2_grpc
import time

# Create stub
stub = store_pb2_grpc.KeyValueStoreStub(grpc.insecure_channel(f"127.0.0.1:32770"))

# PutRequest Test
put_request = store_pb2.PutRequest(
    key="1",
    value="hola"
)
put_response = stub.put(put_request)
time.sleep(1)
print(put_response.success)

# GetRequest Test
get_request = store_pb2.GetRequest(
    key="1"
)
get_response = stub.get(get_request)
print(get_response.value)

