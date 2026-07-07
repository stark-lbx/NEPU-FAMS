import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import subprocess
import time
import signal

SERVICES = [
    ("用户服务", "svc_user", "python services/svc_user/main.py --listen_port 9991 --service_addr 127.0.0.1:9991"),
    ("资产服务", "svc_asset", "python services/svc_asset/main.py --listen_port 9992 --service_addr 127.0.0.1:9992"),
    ("流程服务", "svc_flow", "python services/svc_flow/main.py --listen_port 9993 --service_addr 127.0.0.1:9993"),
    ("存储服务", "svc_storage", "python services/svc_storage/main.py --listen_port 9994 --service_addr 127.0.0.1:9994"),
    ("网关服务", "svc_gateway", "python services/svc_gateway/main.py --listen_port 8080 --service_addr 127.0.0.1:8080"),
]

process_list = []


def signal_handler(signum, frame):
    print("\n正在停止所有服务...")
    for name, _, p in process_list:
        p.terminate()
        print(f"  {name} 已停止")
    exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("正在启动所有服务...")
    for name, _, cmd in SERVICES:
        print(f"  启动 {name}...")
        p = subprocess.Popen(cmd, shell=True, cwd=base_dir)
        process_list.append((name, _, p))
        time.sleep(1.5)

    print("\n✅ 所有服务启动完成")
    print("网关地址: http://127.0.0.1:8080")
    print("按 Ctrl+C 停止所有服务")

    for _, _, p in process_list:
        p.wait()