#!/usr/bin/env python3
"""
FAMS 角色-权限绑定 + 示例数据 脚本
功能:
  1. 为四个角色绑定权限 (sys_role_permission)
  2. 补充字典数据 (asset_type)
  3. 插入示例资产数据 (fams_asset)
"""

import sqlite3
import os
import uuid
import random
from datetime import date, datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fams.db")

# ============================================================
# 1. 权限绑定定义
# ============================================================

# school_admin (ROLE001): 全部权限
SCHOOL_ADMIN_PERMS = [
    # 菜单
    "PERM0001", "PERM0002", "PERM0003", "PERM0004",
    "PERM0101", "PERM0102", "PERM0103", "PERM0104",
    "PERM0201", "PERM0202", "PERM0301", "PERM0302", "PERM0303", "PERM0401",
    # 系统管理-用户
    "PERM010101", "PERM010102", "PERM010103", "PERM010104", "PERM010105",
    # 系统管理-部门
    "PERM010201", "PERM010202", "PERM010203", "PERM010204",
    # 系统管理-角色
    "PERM010301", "PERM010302", "PERM010303", "PERM010304", "PERM010305",
    # 系统管理-字典
    "PERM010401", "PERM010402", "PERM010403", "PERM010404",
    # 资产管理
    "PERM020101", "PERM020102", "PERM020103", "PERM020104", "PERM020105", "PERM020106",
    # 资产分类
    "PERM020201", "PERM020202", "PERM020203", "PERM020204",
    # 借用
    "PERM030101", "PERM030102", "PERM030103", "PERM030104",
    # 报修
    "PERM030201", "PERM030202", "PERM030203",
    # 报废
    "PERM030301", "PERM030302", "PERM030303",
    # 文件
    "PERM040101", "PERM040102", "PERM040103", "PERM040104",
]

# dept_admin (ROLE002): 院系管理员 — 用户管理(本部门)、资产管理、流程管理、文件管理
DEPT_ADMIN_PERMS = [
    # 菜单
    "PERM0001", "PERM0002", "PERM0003", "PERM0004",
    "PERM0101", "PERM0201", "PERM0202", "PERM0301", "PERM0302", "PERM0303", "PERM0401",
    # 用户: 列表/详情/编辑 (不可新增/删除)
    "PERM010101", "PERM010105", "PERM010103",
    # 资产管理-全部
    "PERM020101", "PERM020102", "PERM020103", "PERM020104", "PERM020105", "PERM020106",
    # 资产分类-列表
    "PERM020201",
    # 借用-全部
    "PERM030101", "PERM030102", "PERM030103", "PERM030104",
    # 报修-全部
    "PERM030201", "PERM030202", "PERM030203",
    # 报废-全部
    "PERM030301", "PERM030302", "PERM030303",
    # 文件-全部
    "PERM040101", "PERM040102", "PERM040103", "PERM040104",
]

# teacher (ROLE003): 教师 — 资产查看+盘点、借用申请/归还、报修处理、报废申请
TEACHER_PERMS = [
    # 菜单
    "PERM0002", "PERM0003", "PERM0004",
    "PERM0201", "PERM0301", "PERM0302", "PERM0303", "PERM0401",
    # 资产: 列表/详情/盘点
    "PERM020101", "PERM020105", "PERM020106",
    # 借用: 申请/记录/归还 (不可审批)
    "PERM030101", "PERM030103", "PERM030104",
    # 报修: 处理/记录 (不可申请？不对，老师也可以报修)
    "PERM030201", "PERM030202", "PERM030203",
    # 报废: 申请/记录 (不可审批)
    "PERM030301", "PERM030303",
    # 文件: 上传/下载/列表
    "PERM040101", "PERM040102", "PERM040104",
]

# student (ROLE004): 学生 — 仅报修
STUDENT_PERMS = [
    # 菜单
    "PERM0003",
    "PERM0302",
    # 报修: 申请/记录
    "PERM030201", "PERM030203",
]

ROLE_PERM_MAP = {
    "ROLE001": SCHOOL_ADMIN_PERMS,
    "ROLE002": DEPT_ADMIN_PERMS,
    "ROLE003": TEACHER_PERMS,
    "ROLE004": STUDENT_PERMS,
}

# ============================================================
# 2. 资产类型字典
# ============================================================
ASSET_TYPES = [
    ("教学设备", "TEACH_EQUIP"),
    ("办公设备", "OFFICE_EQUIP"),
    ("家具", "FURNITURE"),
    ("图书资料", "BOOKS"),
    ("交通工具", "VEHICLE"),
    ("实验仪器", "LAB_EQUIP"),
    ("软件", "SOFTWARE"),
    ("其他", "OTHER"),
]

# ============================================================
# 3. 示例资产数据
# ============================================================
# 各院系部门 biz_id (type=2 的学院)
COLLEGE_DEPTS = [
    "DEPT2001", "DEPT2002", "DEPT2003", "DEPT2004", "DEPT2005",
    "DEPT2006", "DEPT2007", "DEPT2008", "DEPT2009", "DEPT2010",
    "DEPT2011", "DEPT2012", "DEPT2013", "DEPT2014",
]
ADMIN_DEPTS = ["DEPT1001", "DEPT1002", "DEPT1003", "DEPT1010", "DEPT1013", "DEPT1017", "DEPT1019"]

ASSET_NAMES = {
    "TEACH_EQUIP": [
        ("多媒体投影仪", "EPSON-CB-L630U", 28500.00),
        ("交互式电子白板", "SMART-SB680", 16800.00),
        ("多媒体讲台", "富可士-S600F", 8500.00),
        ("无线麦克风系统", "舒尔-BLX288/PG58", 4200.00),
        ("教学音响功放", "雅马哈-RX-V485", 5600.00),
        ("高清实物展台", "鸿合-HZ-V670", 7200.00),
        ("智慧黑板", "希沃-BV86EV", 32000.00),
    ],
    "OFFICE_EQUIP": [
        ("台式计算机", "联想-启天M4600", 5600.00),
        ("A4黑白激光打印机", "惠普-LaserJet Pro M404dn", 3200.00),
        ("A3彩色复印机", "佳能-iR-ADV C3530", 28000.00),
        ("高速扫描仪", "富士通-fi-7160", 8500.00),
        ("笔记本电脑", "ThinkPad-X1 Carbon", 12800.00),
        ("壁挂式空调", "格力-KFR-35GW", 4200.00),
        ("立式空调", "格力-KFR-72LW", 8500.00),
    ],
    "FURNITURE": [
        ("办公桌", "1400*700*750mm", 1800.00),
        ("会议桌", "4800*1800*760mm", 6800.00),
        ("钢制文件柜", "1850*900*400mm", 1200.00),
        ("人体工学椅", "可升降-网布", 980.00),
        ("沙发组合", "3+1+1 皮质", 5200.00),
        ("书架", "2000*1000*300mm 6层", 1500.00),
    ],
    "BOOKS": [
        ("《高等数学》(第七版)", "ISBN 978-7-04-039663-8", 56.00),
        ("《大学物理》(第四版)", "ISBN 978-7-04-046377-4", 62.00),
        ("《C程序设计语言》(第2版)", "ISBN 978-7-111-19626-0", 38.00),
    ],
    "VEHICLE": [
        ("公务轿车", "大众-帕萨特 2024款", 189800.00),
        ("通勤中巴", "宇通-ZK6729D", 320000.00),
    ],
    "LAB_EQUIP": [
        ("气相色谱仪", "安捷伦-7890B", 185000.00),
        ("紫外可见分光光度计", "岛津-UV-2600i", 78000.00),
        ("电子天平", "梅特勒-XPR205", 32000.00),
        ("恒温培养箱", "宾德-KB720", 45000.00),
        ("超声波清洗器", "昆山舒美-KQ-800DE", 6800.00),
        ("离心机", "艾本德-5424R", 28000.00),
    ],
    "SOFTWARE": [
        ("MATLAB校园版许可", "R2024a 50用户", 98000.00),
        ("ANSYS仿真软件", "Academic Research 2024", 120000.00),
        ("SPSS统计分析", "Campus Edition 28.0", 45000.00),
    ],
    "OTHER": [
        ("消防器材套装", "4kg干粉灭火器*2+消防栓", 2800.00),
        ("安防监控摄像头", "海康威视-DS-2CD2T47G2-L", 1200.00),
    ],
}

STORAGE_LOCATIONS = ["A栋1楼101", "A栋2楼205", "B栋1楼实验室", "B栋2楼机房", "C栋仓库", "综合楼3楼", "图书馆一楼", "行政楼5楼"]
SUPPLIERS = ["北京科仪科技有限公司", "上海教学设备有限公司", "广州天河电脑城", "深圳华强北电子市场", "京东企业购", "得力办公", "政府采购中心"]

STATUS_CODES = ["1", "2", "3", "4", "5"]  # 在用/闲置/借出/维修中/已报废
STATUS_WEIGHTS = [0.65, 0.10, 0.10, 0.08, 0.07]

# 使用人 user_biz_id (从现有用户中取)
USERS = {
    "DEPT2001": "USER001",  # admin
    "DEPT2002": "USER002",  # dept_admin
    "DEPT2003": "USER003",  # teacher
    "DEPT2004": "USER004",  # student
}


def generate_biz_id(prefix=""):
    return prefix + uuid.uuid4().hex[:16].upper()


def today():
    return date.today().isoformat()


def random_date(days_back=1095):
    return (date.today() - timedelta(days=random.randint(0, days_back))).isoformat()


def seed_dict(conn):
    """插入资产类型字典"""
    cur = conn.cursor()
    for name, code in ASSET_TYPES:
        exists = cur.execute(
            "SELECT 1 FROM sys_dict WHERE dict_type='asset_type' AND dict_code=? AND is_delete=0", (code,)
        ).fetchone()
        if not exists:
            biz_id = generate_biz_id("DICT_")
            cur.execute(
                "INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES (?, ?, ?, ?, ?)",
                (biz_id, "asset_type", code, name, 0),
            )
            print(f"  [DICT] + {code} = {name}")
    conn.commit()


def seed_role_perms(conn):
    """绑定角色和权限"""
    cur = conn.cursor()
    count = 0
    for role_biz_id, perm_list in ROLE_PERM_MAP.items():
        for perm_biz_id in perm_list:
            exists = cur.execute(
                "SELECT 1 FROM sys_role_permission WHERE role_biz_id=? AND perm_biz_id=?",
                (role_biz_id, perm_biz_id),
            ).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO sys_role_permission (role_biz_id, perm_biz_id) VALUES (?, ?)",
                    (role_biz_id, perm_biz_id),
                )
                count += 1
    conn.commit()
    print(f"  [ROLE-PERM] 插入 {count} 条绑定")
    # 打印各角色权限数量
    for role_biz_id in ["ROLE001", "ROLE002", "ROLE003", "ROLE004"]:
        cnt = cur.execute("SELECT COUNT(*) FROM sys_role_permission WHERE role_biz_id=?", (role_biz_id,)).fetchone()[0]
        role_name = cur.execute("SELECT role_name FROM sys_role WHERE biz_id=?", (role_biz_id,)).fetchone()[0]
        print(f"    {role_name} ({role_biz_id}): {cnt} 条权限")


def seed_assets(conn):
    """插入示例资产数据"""
    cur = conn.cursor()
    row_num = 1000
    asset_count = 0
    asset_ids = []

    for _ in range(80):  # 生成 80 条资产
        # 随机选择 资产类型
        type_code = random.choice(ASSET_TYPES)[1]
        if type_code not in ASSET_NAMES:
            continue
        candidates = ASSET_NAMES[type_code]
        name, spec, price = random.choice(candidates)
        price = price * random.uniform(0.85, 1.15)  # 价格浮动

        # 随机部门 (偏向学院)
        dept = random.choice(COLLEGE_DEPTS) if random.random() < 0.75 else random.choice(ADMIN_DEPTS)

        # 随机状态
        status = random.choices(STATUS_CODES, weights=STATUS_WEIGHTS, k=1)[0]

        # 使用人 (50%概率有使用人)
        use_user = ""
        if status == "3" or (status == "1" and random.random() < 0.3):
            use_user = USERS.get(dept, random.choice(list(USERS.values())))

        biz_id = generate_biz_id("AST_")
        row_num += 1
        cur.execute(
            """INSERT INTO fams_asset 
            (biz_id, asset_name, asset_type_code, buy_time, asset_price, store_location, 
             dept_biz_id, current_status_code, use_user_biz_id, supplier, spec, create_user_biz_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                biz_id,
                name,
                type_code,
                random_date(days_back=1825),
                round(price, 2),
                random.choice(STORAGE_LOCATIONS),
                dept,
                status,
                use_user,
                random.choice(SUPPLIERS),
                spec,
                "USER001",
            ),
        )
        asset_count += 1
        asset_ids.append(biz_id)

        # 每20条提交一次
        if asset_count % 20 == 0:
            conn.commit()

    conn.commit()
    print(f"  [ASSET] 插入 {asset_count} 条资产")

    # 验证
    cnt = cur.execute("SELECT COUNT(*) FROM fams_asset WHERE is_delete=0").fetchone()[0]
    print(f"  [ASSET] 数据库现有 {cnt} 条资产")

    # 按类型统计
    print("  [ASSET] 按类型分布:")
    for name, code in ASSET_TYPES:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM fams_asset WHERE asset_type_code=? AND is_delete=0", (code,)
        ).fetchone()[0]
        if cnt > 0:
            print(f"    {name}: {cnt} 台")

    # 按状态统计
    print("  [ASSET] 按状态分布:")
    for code, name in [("1", "在用"), ("2", "闲置"), ("3", "借出"), ("4", "维修中"), ("5", "已报废")]:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM fams_asset WHERE current_status_code=? AND is_delete=0", (code,)
        ).fetchone()[0]
        print(f"    {name}: {cnt} 台")


def main():
    print("=" * 60)
    print("  FAMS 种子数据脚本")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] 数据库不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        print("\n[1/3] 插入资产类型字典...")
        seed_dict(conn)

        print("\n[2/3] 绑定角色与权限...")
        seed_role_perms(conn)

        print("\n[3/3] 插入示例资产...")
        seed_assets(conn)

        print("\n" + "=" * 60)
        print("  所有种子数据写入完成!")
        print("=" * 60)
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
