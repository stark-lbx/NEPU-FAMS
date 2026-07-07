#!/usr/bin/env python3
"""
FAMS 角色-权限绑定脚本 (独立运行)
根据需求为四个角色分配不同的权限:
- school_admin: 全部权限
- dept_admin:  用户管理(本部门)、资产管理、流程管理、文件管理
- teacher:     资产查看+盘点、借用/报废申请、报修处理、文件上传下载
- student:     仅报修申请与查看
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fams.db")

ROLE_PERM_MAP = {
    "ROLE001": [  # school_admin: 全部56条
        "PERM0001","PERM0002","PERM0003","PERM0004",
        "PERM0101","PERM0102","PERM0103","PERM0104",
        "PERM0201","PERM0202","PERM0301","PERM0302","PERM0303","PERM0401",
        "PERM010101","PERM010102","PERM010103","PERM010104","PERM010105",
        "PERM010201","PERM010202","PERM010203","PERM010204",
        "PERM010301","PERM010302","PERM010303","PERM010304","PERM010305",
        "PERM010401","PERM010402","PERM010403","PERM010404",
        "PERM020101","PERM020102","PERM020103","PERM020104","PERM020105","PERM020106",
        "PERM020201","PERM020202","PERM020203","PERM020204",
        "PERM030101","PERM030102","PERM030103","PERM030104",
        "PERM030201","PERM030202","PERM030203",
        "PERM030301","PERM030302","PERM030303",
        "PERM040101","PERM040102","PERM040103","PERM040104",
    ],
    "ROLE002": [  # dept_admin: 院系管理员
        "PERM0001","PERM0002","PERM0003","PERM0004",
        "PERM0101","PERM0201","PERM0202","PERM0301","PERM0302","PERM0303","PERM0401",
        "PERM010101","PERM010105","PERM010103",
        "PERM020101","PERM020102","PERM020103","PERM020104","PERM020105","PERM020106",
        "PERM020201",
        "PERM030101","PERM030102","PERM030103","PERM030104",
        "PERM030201","PERM030202","PERM030203",
        "PERM030301","PERM030302","PERM030303",
        "PERM040101","PERM040102","PERM040103","PERM040104",
    ],
    "ROLE003": [  # teacher: 教师
        "PERM0002","PERM0003","PERM0004",
        "PERM0201","PERM0301","PERM0302","PERM0303","PERM0401",
        "PERM020101","PERM020105","PERM020106",
        "PERM030101","PERM030103","PERM030104",
        "PERM030201","PERM030202","PERM030203",
        "PERM030301","PERM030303",
        "PERM040101","PERM040102","PERM040104",
    ],
    "ROLE004": [  # student: 学生
        "PERM0003",
        "PERM0302",
        "PERM030201","PERM030203",
    ],
}

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] 数据库不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 先清除旧绑定
    cur.execute("DELETE FROM sys_role_permission")
    print("已清除旧的role-permission绑定")

    count = 0
    for role_biz_id, perm_list in ROLE_PERM_MAP.items():
        for perm_biz_id in perm_list:
            cur.execute(
                "INSERT INTO sys_role_permission (role_biz_id, perm_biz_id) VALUES (?, ?)",
                (role_biz_id, perm_biz_id),
            )
            count += 1

    conn.commit()

    print(f"\n写入 {count} 条role-permission绑定:\n")
    for role_biz_id in ["ROLE001", "ROLE002", "ROLE003", "ROLE004"]:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM sys_role_permission WHERE role_biz_id=?", (role_biz_id,)
        ).fetchone()[0]
        role_name = cur.execute(
            "SELECT role_name FROM sys_role WHERE biz_id=?", (role_biz_id,)
        ).fetchone()[0]
        print(f"  {role_name:8s} ({role_biz_id}): {cnt} 条权限")

    conn.close()
    print("\n✅ RBAC 绑定完成!")


if __name__ == "__main__":
    main()
