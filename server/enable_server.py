"""
一键启动全部 8 个 FAMS-NEPU 微服务
用法: python enable_server.py
"""
import os
import sys
import time
import threading
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
SERVICES_DIR = BASE / "services"

SERVICES = [
    ("svr_user_auth", 9910, 9911),
    ("svr_asset_core", 9920, 9921),
    ("svr_workflow", 9930, 9931),
    ("svr_repair", 9940, 9941),
    ("svr_inventory", 9950, 9951),
    ("svr_file_storage", 9960, 9961),
    ("svr_report", 9970, 9971),
    ("svr_gateway", 9900, 9901),  # 网关最后启动
]

processes = []


def reader_thread(proc, name):
    """持续读取子进程输出并打印到控制台"""
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            print(f"[{name}] {line}")


def start_service(name, http_port, grpc_port):
    svc_dir = SERVICES_DIR / name
    if not svc_dir.exists():
        print(f"[SKIP] {name}: 目录不存在 {svc_dir}")
        return None
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE)
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(svc_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    t = threading.Thread(target=reader_thread, args=(proc, name), daemon=True)
    t.start()
    print(f"[{proc.pid}] {name} 启动中...  HTTP:{http_port}  gRPC:{grpc_port}")
    return proc


def main():
    print("=" * 60)
    print("  FAMS-NEPU 微服务一键启动")
    print("=" * 60)

    for name, http_port, grpc_port in SERVICES:
        proc = start_service(name, http_port, grpc_port)
        if proc:
            processes.append((name, proc))
        time.sleep(0.5)

    print(f"\n全部 {len(processes)} 个服务已启动")
    print("按 Ctrl+C 停止所有服务\n")

    try:
        for name, proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        print("\n正在停止所有服务...")
        for name, proc in processes:
            proc.terminate()
        time.sleep(2)
        for name, proc in processes:
            if proc.poll() is None:
                proc.kill()
        print("全部服务已停止")


if __name__ == "__main__":
    main()
