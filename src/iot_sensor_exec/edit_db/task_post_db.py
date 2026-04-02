from shlex import join
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from db_orm import iot_task_db, iot_device_db, iot_data_db

def get_device_host_type(device_id:int):
    """
    根据设备ID获取设备主机类型
    """
    try:
        host_type = -1
        host_id = -1
        while True:
            query = iot_device_db.session.query(iot_device_db.Device.id,iot_device_db.Device.device_type_id,iot_device_db.Device.parent_device_id).filter(iot_device_db.Device.id == device_id).first()
            if query:
                data = query._asdict()
                if data["parent_device_id"] == None:
                    host_type =int(data["device_type_id"])
                    host_id = int(data["id"])
                    break
                else:
                    device_id = int(data["parent_device_id"])
                    host_id = int(data["id"])
            else:
                break
        return host_type, host_id
    except Exception as e:
        iot_device_db.session.rollback()
        return -1, str(e)
    finally:
        iot_device_db.session.close()

def get_unpost_mes(timeout: int = 5):
    """
    获取未推送的任务结果
    timeout: 超时时间，单位:天
    """
    result_list = []
    try:
        query = iot_task_db.session.query(iot_task_db.Result)\
            .filter(iot_task_db.Result.post_status == 0,
            iot_task_db.Result.create_time >= datetime.now() - timedelta(days=timeout),
            iot_task_db.Result.create_time <= datetime.now()).all()
        if query:
            for result in query:
                result_list.append(result.to_dict())
            return True, result_list
        else:
            return True, []
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def get_progress_uuid_by_id(task_progress_id:int):
    """
    根据任务进度ID获取任务进度UUID
    """
    try:
        query = iot_task_db.session.query(iot_task_db.Progress.progress_uuid).filter(iot_task_db.Progress.id == task_progress_id).first()
        if query:
            return True, query.progress_uuid
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def get_device_mes_by_id(device_id:int):
    """
    根据设备ID获取设备编码
    """
    try:
        query = iot_device_db.session.query(iot_device_db.Device).filter(iot_device_db.Device.id == device_id).first()
        if query:
            return True, query.to_dict()
        else:
            return False, {}
    except Exception as e:
        iot_device_db.session.rollback()
        return False, str(e)
    finally:
        iot_device_db.session.close()

def get_mes_code_by_progress(task_progress: dict):
    """
    根据任务进度获取设备编码
    Action / Device / Progress 三表无直接外键关联，分开查询再合并
    """
    try:
        progress = iot_task_db.session.query(iot_task_db.Progress.progress_uuid)\
            .filter(iot_task_db.Progress.id == task_progress["task_progress_id"]).first()

        action = iot_task_db.session.query(iot_task_db.Action.srv_id)\
            .filter(iot_task_db.Action.id == task_progress["task_action_id"]).first()

        device = iot_device_db.session.query(
            iot_device_db.Device.device_code,
            iot_device_db.Device.device_type_id)\
            .filter(iot_device_db.Device.id == task_progress["device_id"]).first()

        if progress and action and device:
            return True, {
                "srv_id":          action.srv_id,
                "device_code":     device.device_code,
                "device_type_id":  device.device_type_id,
                "progress_uuid":   progress.progress_uuid,
            }
        else:
            return False, {}
    except Exception as e:
        iot_task_db.session.rollback()
        iot_device_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()
        iot_device_db.session.close()

def get_mes_code_by_result_dict(result_list: list):
    """
    根据任务结果获取设备编码
    返回信息:
    [{'id': 30232, 'file_path': '', 'item_values': {'temp': 20.8, 'signal': 98, 'battery': 100, 'vib_amp_x': 0.4, 'vib_amp_y': 0.9, 'vib_amp_z': 1.2},
     'error_info': None, 'progress_uuid': 'f0499212-3fb2-4012-a725-cddfde60718f', 'srv_id': 323, 'action_params': [{"item": 7, "param": 0}, 
     {"item": 8, "param": 0}, {"item": 9, "param": 0}, {"item": 10, "param": 0}], 'device_code': '4569763756', 'device_type_id': 15, 'create_time': '2026-03-30 10:00:00'}, ...] 
    """
    try:
        result_mes_list = []
        for result in result_list:
            query = iot_task_db.session.query(
                iot_task_db.Result.id,
                iot_task_db.Result.file_path,
                iot_task_db.Result.item_values,
                iot_task_db.Result.error_info,
                iot_task_db.Result.create_time,
                iot_task_db.Progress.progress_uuid,
                iot_task_db.Action.srv_id,
                iot_task_db.Action.action_params,
                iot_device_db.Device.device_code,
                iot_device_db.Device.device_type_id)\
            .join(iot_task_db.Progress,iot_task_db.Progress.id == iot_task_db.Result.task_progress_id)\
            .join(iot_task_db.Action,iot_task_db.Action.id == iot_task_db.Result.task_action_id)\
            .join(iot_device_db.Device,iot_device_db.Device.id == iot_task_db.Result.device_id)\
            .filter(iot_task_db.Result.id == result["id"]).first()
            if query:
                result_mes_list.append(query._asdict())
            else:
                pass
        return True, result_mes_list
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def get_item_definition_by_device_type_id(device_type_id:int):
    """
    根据设备类型ID获取设备定义
    """
    try:
        query = iot_data_db.session.query(iot_data_db.ItemDefinition.srv_id,iot_data_db.ItemDefinition.item_code)\
        .filter(iot_data_db.ItemDefinition.device_type_id == device_type_id,
        iot_data_db.ItemDefinition.srv_id != None, iot_data_db.ItemDefinition.srv_id != 'null')\
        .order_by(iot_data_db.ItemDefinition.sort_order.asc()).all()
        if query:
            return True, [{
                "srv_id": result.srv_id,
                "item_code": result.item_code
            } for result in query]
        else:
            return False, []
    except Exception as e:
        iot_data_db.session.rollback()
        return False, str(e)
    finally:
        iot_data_db.session.close()

def update_result_post_status(result_list: list):
    """
    更新任务结果推送状态
    """
    try:
        iot_task_db.session.bulk_update_mappings(iot_task_db.Result, result_list)
        iot_task_db.session.commit()
        return True, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def get_item_definition():
    """
    根据设备类型ID获取设备定义
    """
    query = iot_data_db.session.query(iot_data_db.ItemDefinition.srv_id,iot_data_db.ItemDefinition.item_code)\
        .where(iot_data_db.ItemDefinition.srv_id != None, iot_data_db.ItemDefinition.srv_id != 'null')\
        .all()
    if query:
        return True, {int(result.srv_id): result.item_code for result in query}
    else:
        return False, {}

if __name__ == "__main__":
    # flag, result = get_unpost_mes(1)
    # flag, result = get_progress_uuid_by_id(1218)
    # flag, result = get_mes_code_by_progress({"task_progress_id": 4962, "device_id": 84, "task_action_id": 323})
    # flag, result = get_mes_code_by_result_dict([{"id": 30232}, {"id": 30233}])
    flag, result = update_result_post_status([{"id": 40185, "post_status": 1}, {"id": 40186, "post_status": 1}])
    # flag, result = get_item_definition_by_device_type_id(15)
    # flag, result = get_item_definition()
    print(flag)
    print(result)