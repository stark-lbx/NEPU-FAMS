#!/usr/bin/env python3
"""
FAMS 示例资产数据插入脚本 (独立运行)
插入 80 条资产到各学院/行政部门
"""

import sqlite3
import os
import uuid
import random
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fams.db")

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

COLLEGE_DEPTS = [
    "DEPT2001","DEPT2002","DEPT2003","DEPT2004","DEPT2005",
    "DEPT2006","DEPT2007","DEPT2008","DEPT2009","DEPT2010",
    "DEPT2011","DEPT2012","DEPT2013","DEPT2014",
]
ADMIN_DEPTS = ["DEPT1001","DEPT1002","DEPT1003","DEPT1010","DEPT1013","DEPT1017","DEPT1019"]

STORAGE_LOCATIONS = [
    "A栋1楼101","A栋2楼205","B栋1楼实验室","B栋2楼机房",
    "C栋仓库","综合楼3楼","图书馆一楼","行政楼5楼",
]
SUPPLIERS = [
    "北京科仪科技有限公司","上海教学设备有限公司",
    "广州天河电脑城","深圳华强北电子市场",
    "京东企业购","得力办公","政府采购中心",
]

STATUS_CODES = ["1","2","3","4","5"]
STATUS_WEIGHTS = [0.65, 0.10, 0.10, 0.08, 0.07]

USERS = {
    "DEPT2001": "USER001",
    "DEPT2002": "USER002",
    "DEPT2003": "USER003",
    "DEPT2004": "USER004",
}

def generate_biz_id(prefix=""):
    return prefix + uuid.uuid4().hex[:16].upper()

def random_date(days_back=1825):
    return (date.today() - timedelta(days=random.randint(0, days_back))).isoformat()

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] 数据库不存在: {DB_PATH}")
        return

    # 先插入字典
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for name, code in ASSET_TYPES:
        exists = cur.execute(
            "SELECT 1 FROM sys_dict WHERE dict_type='asset_type' AND dict_code=? AND is_delete=0",
            (code,)
        ).fetchone()
        if not exists:
            cur.execute(
                "INSERT INTO sys_dict (biz_id, dict_type, dict_code, dict_name, sort) VALUES (?,?,?,?,?)",
                (generate_biz_id("DICT_"), "asset_type", code, name, 0),
            )
            print(f"  [DICT] + {code} = {name}")
    conn.commit()

    # 插入资产
    print(f"\n开始插入资产...")
    count = 0
    for _ in range(80):
        type_code = random.choice(ASSET_TYPES)[1]
        if type_code not in ASSET_NAMES:
            continue
        candidates = ASSET_NAMES[type_code]
        name, spec, price = random.choice(candidates)
        price = round(price * random.uniform(0.85, 1.15), 2)
        dept = random.choice(COLLEGE_DEPTS) if random.random() < 0.75 else random.choice(ADMIN_DEPTS)
        status = random.choices(STATUS_CODES, weights=STATUS_WEIGHTS, k=1)[0]
        use_user = ""
        if status == "3" or (status == "1" and random.random() < 0.3):
            use_user = USERS.get(dept, random.choice(list(USERS.values())))

        cur.execute(
            """INSERT INTO fams_asset 
            (biz_id, asset_name, asset_type_code, buy_time, asset_price, store_location,
             dept_biz_id, current_status_code, use_user_biz_id, supplier, spec, create_user_biz_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                generate_biz_id("AST_"), name, type_code, random_date(1825),
                price, random.choice(STORAGE_LOCATIONS), dept, status, use_user,
                random.choice(SUPPLIERS), spec, "USER001",
            ),
        )
        count += 1
        if count % 20 == 0:
            conn.commit()

    conn.commit()

    print(f"\n插入完成: {count} 条资产")
    total = cur.execute("SELECT COUNT(*) FROM fams_asset WHERE is_delete=0").fetchone()[0]
    print(f"数据库现有资产: {total} 条")

    # 统计
    print("\n按类型分布:")
    for name, code in ASSET_TYPES:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM fams_asset WHERE asset_type_code=? AND is_delete=0", (code,)
        ).fetchone()[0]
        if cnt > 0:
            print(f"  {name}: {cnt} 台")

    print("\n按状态分布:")
    for code, label in [("1","在用"),("2","闲置"),("3","借出"),("4","维修中"),("5","已报废")]:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM fams_asset WHERE current_status_code=? AND is_delete=0", (code,)
        ).fetchone()[0]
        print(f"  {label}: {cnt} 台")

    conn.close()
    print("\n✅ 示例资产数据写入完成!")

if __name__ == "__main__":
    main()
