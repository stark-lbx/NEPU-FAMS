import os
import signal

def kill_all():
    # 查找所有相关Python进程并杀死
    keywords = ["svc_user/main.py", "svc_asset/main.py", "svc_flow/main.py",
                "svc_storage/main.py", "svc_gateway/main.py"]
    for kw in keywords:
        os.system(f"pkill -f '{kw}'")
    print("所有服务已停止")

if __name__ == "__main__":
    kill_all()