import sqlite3

# 连接数据库（文件不存在则自动创建）
conn = sqlite3.connect('../../fams.db')
cursor = conn.cursor()

def fams_init():
    # 读取SQL文件并执行批量建表
    with open('fams_sqlite.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()

    cursor.executescript(sql_script)
    conn.commit()
    print("数据库表创建完成")

def dept_init():
    with open('insert_dept_sqlite.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    cursor.executescript(sql_script)
    conn.commit()
    print("部门表初始化成功")

def role_init():
    with open('insert_role_sqlite.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    cursor.executescript(sql_script)
    conn.commit()
    print("角色表初始化成功")

def dict_init():
    with open('insert_dict_sqlite.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    cursor.executescript(sql_script)
    conn.commit()
    print("字典表初始化成功")

def permission_init():
    with open('insert_permission_sqlite.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()
    cursor.executescript(sql_script)
    conn.commit()
    print("权限表初始化成功")

# if __name__ == '__main__':

fams_init()
dept_init()
role_init()
dict_init()
permission_init()
conn.close()