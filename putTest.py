import grpc
from proto import store_pb2
from proto import store_pb2_grpc
import time

# PutRequest Test
request_conn_message = store_pb2.PutRequest(
    key="1",
    value="hola"
)

stub = store_pb2_grpc.KeyValueStoreStub(grpc.insecure_channel(f"127.0.0.1:32770"))
connection_details = stub.put(request_conn_message)
time.sleep(1)
print(connection_details.success)
