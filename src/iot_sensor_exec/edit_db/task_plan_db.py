#!/usr/bin/env python3
# coding=utf-8

import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from db_orm import iot_task_db

def add_task_plan(data: dict):
    """
    添加任务计划
    """
    if data.get("plan_execution_time",) != None:
        start_time = datetime.fromisoformat(data.get("plan_execution_time"))
    else:
        start_time = None
    cycle_execution_unit = data.get("cycle_execution_unit",None)
    if cycle_execution_unit != None:
        if cycle_execution_unit == 1:
            config_data = {"time":data.get("cycle_execution_times")}
        elif cycle_execution_unit == 2:
            config_data = {"weekdays": data.get("interval_values"), "time":data.get("cycle_execution_times")}
        elif cycle_execution_unit == 3:
            config_data = {"day_of_month": data.get("interval_values"), "time":data.get("cycle_execution_times")}
        else:
            config_data = None
    else:
        config_data = None
    
    task_srv_id = data.get("task_id")
    try:    #v1.1新增task_srv_id查询task_id，防止task_id被删除或禁用后无法查询到task_id
        if task_srv_id != None:
            query = iot_task_db.session.query(iot_task_db.Task.id)\
                .filter(iot_task_db.Task.srv_id == task_srv_id)\
                .where(iot_task_db.Task.is_delete == 0 and iot_task_db.Task.status == 0)\
                .first()
            if query != None:
                task_id = query.id
            else:
                return False, "task_id不存在"
        else:
            return False, "task_id不存在"
    except Exception as e:
        return False, str(e)
    finally:
        iot_task_db.session.close()

    plan =iot_task_db.Plan(
            srv_id = data.get("plan_id"),
            task_id = task_id,
            plan_name = data.get("plan_name"),
            plan_type = data.get("cycle_execution_unit"),
            execute_time = start_time,
            cycle_config = config_data,
            cycle_start_time = data.get("plan_start_date",start_time),
            cycle_end_time = data.get("plan_end_date",start_time),
            plan_status = data.get("enabled"),
            progress_generate = data.get("progress_generate", 0),
            create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    try:
        iot_task_db.session.add(plan)
        iot_task_db.session.commit()
        return True, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def update_task_plan(data: dict):
    """
    修改任务计划
    """
    if data.get("plan_execution_time",) != None:
        start_time = datetime.fromisoformat(data.get("plan_execution_time"))
    else:
        start_time = None
    cycle_execution_unit = data.get("cycle_execution_unit",None)
    if cycle_execution_unit != None:
        if cycle_execution_unit == 1:
            config_data = {"time":data.get("cycle_execution_times")}
        elif cycle_execution_unit == 2:
            config_data = {"weekdays": data.get("interval_values"), "time":data.get("cycle_execution_times")}
        elif cycle_execution_unit == 3:
            config_data = {"day_of_month": data.get("interval_values"), "time":data.get("cycle_execution_times")}
        else:
            config_data = None
    else:
        config_data = None
    update_data ={
        "srv_id": data.get("plan_id"),
        "task_id": data.get("task_id"),
        "plan_name": data.get("plan_name"),
        "plan_type": data.get("cycle_execution_unit"),
        "execute_time": start_time,
        "cycle_config": config_data,
        "cycle_start_time": data.get("plan_start_date",start_time),
        "cycle_end_time": data.get("plan_end_date",start_time),
        "plan_status": data.get("enabled"),
        "progress_generate": data.get("progress_generate", 0),
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        iot_task_db.session.query(iot_task_db.Plan).filter(iot_task_db.Plan.srv_id == data.get("plan_id")).update(update_data)
        iot_task_db.session.commit()
        return True, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def delete_task_plan(data: dict):
    """
    删除任务计划
    """
    try:
        mes = iot_task_db.session.query(iot_task_db.Plan).filter(iot_task_db.Plan.srv_id == data.get("plan_id"))
        if mes.count() > 0:
            mes.delete()
            iot_task_db.session.commit()
            return True, None
        else:
            return False, "任务计划不存在, plan_id: " + str(data.get("plan_id"))
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

if __name__ == "__main__":
    data =  {"data": {"plan_id": 295, "cycle_execution_unit": 3, "cycle_execution_times": ["17:37:04", "20:37:10"], "interval_values": ["3", "4", "6", "24", "26", "28"], "task_id": 148, "plan_end_date": "2026-03-12", "strategy": 2, "operation": 0, "plan_start_date": "2026-03-12", "plan_name": "测试1", "enabled": 1}, "device_code": "5648468468", "func_value": "iot_edit_sensor_task_plan", "message_id": "a7c3351c-e6b7-4b01-a33e-63954ff827f1"}
    data = {"data": {"plan_id": 295, "cycle_execution_unit": 2, "cycle_execution_times": ["16:36:48", "17:36:51"], "interval_values": ["2", "4", "6", "7"], "task_id": 148, "plan_end_date": "2026-03-12", "strategy": 2, "operation": 0, "plan_start_date": "2026-03-12", "plan_name": "测试1", "enabled": 1}, "device_code": "5648468468", "func_value": "iot_edit_sensor_task_plan", "message_id": "54e33469-dd2c-4531-880d-5ab317f163a2"}
    data = {"data": {"plan_id": 319, "cycle_execution_unit": 1, "cycle_execution_times": ["17:39:24"], "task_id": 148, "plan_end_date": "2026-03-12", "strategy": 2, "operation": 0, "plan_start_date": "2026-03-12", "plan_name": "测试1", "enabled": 1}, "device_code": "5648468468", "func_value": "iot_edit_sensor_task_plan", "message_id": "bf1d4d98-d685-4e20-8a78-9587d5ae9ffb"}
    delete_task_plan(data["data"])