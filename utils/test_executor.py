import subprocess
import sys

server_script_path = "/home/erosvs/PycharmProjects/prac-2-sd/eval/decentralized_system_tests.py"
for _ in range(10):
    server_process = subprocess.Popen([sys.executable, server_script_path])
    print(_)
