#!/usr/bin/env python3
# coding=utf-8

"""
pymysql 数据库操作示例
涵盖：单条/批量 增删查改
"""

import pymysql
import json

# ─────────────────────────────────────────
# 数据库连接配置
# ─────────────────────────────────────────
UDMPDB_DB = {
    "host":     "120.26.22.61",
    "port":     15698,
    "user":     "root",
    "password": "123456",
    "database": "udmp",
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,   # 查询结果返回字典格式
}

IOT_DB = {
    "host":     "120.26.22.61",
    "port":     15698,
    "user":     "root",
    "password": "123456",
    "database": "iot",
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

def get_conn(db_config: dict):
    """创建并返回数据库连接"""
    return pymysql.connect(**db_config)


# ═══════════════════════════════════════════
#  单条操作
# ═══════════════════════════════════════════

def insert_one(name: str, status: int) -> int:
    """单条插入，返回新记录的 id"""
    sql = "INSERT INTO test_table (name, status) VALUES (%s, %s)"
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (name, status))
        conn.commit()
        return conn.insert_id()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def select_one(record_id: int) -> dict:
    """单条查询，根据 id 返回一条记录"""
    sql = "SELECT * FROM test_table WHERE id = %s"
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (record_id,))
            return cur.fetchone()
    finally:
        conn.close()


def update_one(record_id: int, name: str) -> int:
    """单条修改，根据 id 更新 name，返回受影响行数"""
    sql = "UPDATE test_table SET name = %s WHERE id = %s"
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (name, record_id))
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def delete_one(record_id: int) -> int:
    """单条删除，根据 id 删除，返回受影响行数"""
    sql = "DELETE FROM test_table WHERE id = %s"
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (record_id,))
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ═══════════════════════════════════════════
#  批量操作
# ═══════════════════════════════════════════

def insert_many(records: list) -> int:
    """
    批量插入
    records: [{"name": "a", "status": 1}, ...]
    返回受影响行数
    """
    sql = "INSERT INTO test_table (name, status) VALUES (%s, %s)"
    data = [(r["name"], r["status"]) for r in records]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, data)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def select_many(status: int) -> list:
    """
    批量查询，根据 status 查询所有匹配记录
    返回 list[dict]
    """
    sql = "SELECT * FROM test_table WHERE status = %s"
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (status,))
            return cur.fetchall()
    finally:
        conn.close()


def update_many(ids: list, new_status: int) -> int:
    """
    批量修改，将指定 id 列表的 status 统一更新
    返回受影响行数
    """
    placeholders = ",".join(["%s"] * len(ids))
    sql = f"UPDATE test_table SET status = %s WHERE id IN ({placeholders})"
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, [new_status] + ids)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def delete_many(ids: list) -> int:
    """
    批量删除，根据 id 列表批量删除
    返回受影响行数
    """
    placeholders = ",".join(["%s"] * len(ids))
    sql = f"DELETE FROM test_table WHERE id IN ({placeholders})"
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, ids)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ═══════════════════════════════════════════
#  测试入口（需先建好 test_table 表）
#
#  CREATE TABLE test_table (
#      id     INT PRIMARY KEY AUTO_INCREMENT,
#      name   VARCHAR(100) NOT NULL,
#      status INT NOT NULL DEFAULT 0
#  );
# ═══════════════════════════════════════════

def cp_iot_device():
    sql = "SELECT id, device_name, device_type_id, parent_device_id, device_code, create_time FROM device"
    conn = get_conn(UDMPDB_DB)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            result = cur.fetchall()
    finally:
        conn.close()
    
    sql = "INSERT INTO iot_device (id,device_name, device_type_id, parent_device_id, device_code, create_time) VALUES (%s, %s, %s, %s, %s, %s)"
    data = [(r["id"], r["device_name"], r["device_type_id"], r["parent_device_id"], r["device_code"], r["create_time"]) for r in result]
    conn = get_conn(IOT_DB)
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, data)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def cp_iot_device_attr():
    max = 300
    sql = "SELECT device_id, type_attr_id, type_attr_value, create_time FROM device_attribute WHERE device_id = %s"
    conn = get_conn(UDMPDB_DB)
    result_list = []
    try:
        with conn.cursor() as cur:
            for i in range(1,max):
                print(i)
                ip = None
                port = None
                username = None
                password = None
                factory_type = 0
                parameter = {}
                online_status = None
                create_time = None
                cur.execute(sql, (i,))
                result = cur.fetchall()
                if result:
                    for row in result:
                        device_code = None
                        device_sql = "SELECT device_code FROM device WHERE id = %s"
                        cur.execute(device_sql, (row["device_id"],))
                        device_result = cur.fetchone()
                        if device_result:
                            device_code = device_result["device_code"]
                        type_attr_sql = "SELECT attr_key FROM device_type_attr WHERE id = %s"
                        cur.execute(type_attr_sql, (row["type_attr_id"],))
                        attr_key = cur.fetchone()["attr_key"]
                        if attr_key == "ip":
                            ip = row["type_attr_value"]
                        elif attr_key == "port":
                            port = row["type_attr_value"]
                        elif attr_key == "username":
                            username = row["type_attr_value"]
                        elif attr_key == "password":
                            password = row["type_attr_value"]
                        elif attr_key == "group_id":
                            parameter = {"group_id": int(row["type_attr_value"])}
                        elif attr_key == "electric_threshold":
                            parameter = {"electric_threshold": row["type_attr_value"]}
                        elif attr_key == "holding_day":
                            parameter = {"holding_day": int(row["type_attr_value"])}
                        elif attr_key == "group":
                            parameter = {"group": int(row["type_attr_value"])}
                        elif attr_key == "api_url":
                            parameter = {"api_url": row["type_attr_value"]}
                        elif attr_key == "slave_id":
                            parameter = {"slave_id": row["type_attr_value"]}
                        elif attr_key == "channel":
                            parameter = {"channel": row["type_attr_value"]}
                        elif attr_key == "video_stream":
                            parameter = {"video_stream": row["type_attr_value"]}
                        else:
                            pass
                        create_time = row["create_time"]
                    result_list.append({
                        "device_code": device_code,
                        "ip": ip,
                        "port": port,
                        "username": username,
                        "password": password,
                        "factory_type": factory_type,
                        "parameter": parameter if parameter else None,
                        "online_status": online_status,
                        "create_time": create_time,
                    })       
                else:
                    pass
        print(result_list)
    finally:
        conn.close()
    sql = "INSERT INTO iot_device_attr (device_code, ip, port, username, password, factory_type, parameter, online_status, create_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    data = [(r["device_code"], r["ip"], r["port"], r["username"], r["password"], r["factory_type"],
              json.dumps(r["parameter"], ensure_ascii=False) if r["parameter"] is not None else None,
              r["online_status"], r["create_time"]) for r in result_list]
    conn = get_conn(IOT_DB)
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, data)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        print(e)
        conn.rollback()
    finally:
        conn.close()

def cp_iot_task_action():
    sql = "SELECT id, task_id, device_id, device_ability_id, preset_id, sort_order, action_params, create_time FROM task_point_action"
    conn = get_conn(UDMPDB_DB)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            result = cur.fetchall()
            print(result)
    finally:
        conn.close()
    sql = "INSERT INTO iot_task_action (id, srv_id, task_id, device_id, device_ability_id, preset_id, sort_order, action_params, create_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    data = [(r["id"],r["id"], r["task_id"], r["device_id"], r["device_ability_id"], r["preset_id"], r["sort_order"], r["action_params"], r["create_time"]) for r in result]
    conn = get_conn(IOT_DB)
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, data)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        print(e)
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # cp_iot_device()
    # cp_iot_device_attr()
    cp_iot_task_action()


