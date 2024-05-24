import json
import os
import time
from concurrent import futures

import grpc
import yaml

from nodes.quorum_server import QuorumServer
from proto import store_pb2_grpc


def load_config():
    """Load configuration from a YAML file."""
    config_path = os.path.join('decentralized_config.yaml')
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        raise


def load_data(node_id):
    try:
        with open(f'db/decentralized/{node_id}_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Failed to load data for {node_id}: {e}")
        return {}


if __name__ == '__main__':
    try:
        config = load_config()  # YAML config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        exit(1)

    peers = []
    servers = []
    for node in config['nodes']:
        node_id = node['id']
        node_weight = node['weight']
        peer = f"{node['ip']}:{node['port']}"
        data = load_data(node_id)
        quorum_node = QuorumServer(node_id, node_weight, data, peer, peers)

        # Config servers and servicers
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        store_pb2_grpc.add_KeyValueStoreServicer_to_server(quorum_node, server)
        server.add_insecure_port(peer)
        peers.append(peer)
        servers.append(server)

    # Start servers
    for i, server in enumerate(servers):
        print(f"Starting server: {i + 1}")
        server.start()
        time.sleep(1)

    # Block until all servers are terminated
    for server in servers:
        server.wait_for_termination()
