"""
补丁脚本：为学生角色追加借用资产权限
运行方式：python __scripts/patch_student_borrow.py
幂等：重复执行不会产生重复数据
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fams.db")


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 获取学生角色 biz_id
    cur.execute("SELECT biz_id FROM sys_role WHERE role_code = 'student'")
    row = cur.fetchone()
    if not row:
        print("[ERROR] 找不到 student 角色")
        conn.close()
        return
    student_role_biz = row[0]

    # 学生需要追加的权限（菜单 + 按钮）
    # PERM0301 借用流程菜单、PERM030101 借用申请、PERM030103 借用记录查询、PERM030104 归还确认
    new_perms = ["PERM0301", "PERM030101", "PERM030103", "PERM030104"]

    # 收集需要插入的 ID
    added = 0
    skipped = 0

    for perm_biz_id in new_perms:
        # 验证权限是否存在
        cur.execute("SELECT perm_name FROM sys_permission WHERE biz_id = ? AND is_delete = 0", (perm_biz_id,))
        perm = cur.fetchone()
        if not perm:
            print(f"[WARN] 权限 {perm_biz_id} 不存在，跳过")
            continue

        # 检查是否已存在绑定
        cur.execute(
            "SELECT id FROM sys_role_permission WHERE role_biz_id = ? AND perm_biz_id = ?",
            (student_role_biz, perm_biz_id),
        )
        if cur.fetchone():
            print(f"[SKIP] 权限 {perm_biz_id}（{perm[0]}）已绑定")
            skipped += 1
            continue

        cur.execute(
            "INSERT INTO sys_role_permission (role_biz_id, perm_biz_id) VALUES (?, ?)",
            (student_role_biz, perm_biz_id),
        )
        print(f"[OK] 追加权限 {perm_biz_id}（{perm[0]}）")
        added += 1

    conn.commit()

    # 输出结果
    cur.execute("""
        SELECT p.biz_id, p.perm_name, p.perm_url, p.perm_type
        FROM sys_role_permission rp
        JOIN sys_permission p ON p.biz_id = rp.perm_biz_id AND p.is_delete = 0
        WHERE rp.role_biz_id = ?
        ORDER BY p.perm_type, p.biz_id
    """, (student_role_biz,))
    rows = cur.fetchall()

    print(f"\n===== 补丁完成 =====")
    print(f"新增 {added} 条，跳过 {skipped} 条（已存在）")
    print(f"\n学生当前权限 ({len(rows)} 条):")
    for r in rows:
        t = "菜单" if r[3] == 1 else "按钮"
        print(f"  {r[0]:<15} | {r[1]:<12} | {r[2]:<40} | [{t}]")

    conn.close()


if __name__ == "__main__":
    main()
