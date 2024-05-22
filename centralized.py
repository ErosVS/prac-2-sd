import os
import threading
import json
import time

import grpc
from concurrent import futures
import yaml
from proto import store_pb2_grpc
from nodes.master_node import MasterNode
from nodes.slave_node import SlaveNode


def load_config():
    """Load configuration from a YAML file."""
    config_path = os.path.join('centralized_config.yaml')
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        raise


def load_data(node_id):
    try:
        with open(f'db/{node_id}_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Failed to load data for {node_id}: {e}")
        return {}


if __name__ == '__main__':
    lock = threading.Lock()  # Mutex for all nodes
    try:
        config = load_config()  # YAML config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        exit(1)

    # Set Up Slaves
    slave_servers = []
    for slave_config in config['slaves']:
        try:
            slave_data = load_data(slave_config['id'])
            slave_node = SlaveNode(lock, slave_data, slave_config['id'])

            # Start slave servers
            slave_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            store_pb2_grpc.add_KeyValueStoreServicer_to_server(slave_node, slave_server)
            slave_server.add_insecure_port(f"{slave_config['ip']}:{slave_config['port']}")
            slave_servers.append(slave_server)
        except Exception as e:
            print(f"Error setting up slave server {slave_config['id']}: {e}")
            continue

    # Start slave servers concurrently
    for server in slave_servers:
        try:
            server.start()
            time.sleep(2)
        except Exception as e:
            print(f"Error starting server: {e}")

    # Set Up Master
    master_server = None
    try:
        master_config = config['master']
        master_data = load_data('master')
        master_node = MasterNode(lock, master_data, config['slaves'])

        # Start master server
        master_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        store_pb2_grpc.add_KeyValueStoreServicer_to_server(master_node, master_server)
        master_server.add_insecure_port(f"{master_config['ip']}:{master_config['port']}")
    except Exception as e:
        print(f"Error setting up master server: {e}")
        exit(1)

    # Start master server
    master_server.start()

    # Block until all servers are terminated
    for server in slave_servers:
        server.wait_for_termination()

    master_server.wait_for_termination()
