import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from db_orm import iot_task_db, iot_device_db, iot_data_db

def get_device_id(device_name:list):
    """
    根据设备名称获取设备ID
    """
    result_list = {}
    try:
        if not device_name:
            return False, "设备名称不能为空"
        else:
            for name in device_name:
                query = iot_device_db.session.query(iot_device_db.DeviceType.id).filter(iot_device_db.DeviceType.type_name == name).first()
                if query:
                    result_list[name] = query._asdict()["id"]
                else:
                    result_list[name] = None
            return True, result_list
    except Exception as e:
        iot_device_db.session.rollback()
        return False, str(e)
    finally:
        iot_device_db.session.close()

def get_device_config(device_id:list):
    """
    根据设备ID获取设备配置
    """
    device_code_dict = {}
    try:
        for id in device_id:
            query = iot_device_db.session.query(iot_device_db.Device.id, iot_device_db.Device.device_code)\
            .filter(iot_device_db.Device.device_type_id == id).all()
            if query:
                for result in query:
                    device_code_dict[str(result[0])] = result[1]
            else:
                pass
        if device_code_dict:
            for key, value in device_code_dict.items():
                query =iot_device_db.session.query(iot_device_db.Attr.ip, iot_device_db.Attr.port, 
                iot_device_db.Attr.username, iot_device_db.Attr.password, iot_device_db.Attr.parameter)\
                .filter(iot_device_db.Attr.device_code == value).first()
                if query:
                    device_code_dict[key] = query._asdict()
                else:
                    device_code_dict[key] = {}
        return True, device_code_dict
    except Exception as e:
        iot_device_db.session.rollback()
        return False, str(e)
    finally:
        iot_device_db.session.close()
    
def end_timeout_task():
    """
        获取当前系统时间，如果任务开始时间已经超时，将当前任务状态置为异常
        返回信息格式为：
        True, None 表示处理成功
        False, str(e) 表示处理失败
    """
    try:
        query = iot_task_db.session.query(iot_task_db.Progress.id, iot_task_db.Progress.start_time)\
        .filter(iot_task_db.Progress.start_time < datetime.now(), iot_task_db.Progress.status == 4, iot_task_db.Progress.progress_status == 0).all()
        if query:
            for result in query:
                iot_task_db.session.query(iot_task_db.Progress).filter(iot_task_db.Progress.id == result[0]).update({"status": 5})
        else:
            pass
        iot_task_db.session.commit()
        return True, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def get_task_plan(device_type_id: list,timeout = 1*60):
    """
    查询任务计划符合条件的计划
    v1.1新增设备分类参数用作筛选操作,过滤掉不满足条件的任务计划
    条件:
    1. status = 4
    2. progress_status = 0
    3. start_time <= 当前时间 + timeout秒
    4. 关联 iot_device, 过滤设备类型
    """
    task_list = []
    try:
        query = iot_task_db.session.query(iot_task_db.Progress.id,iot_task_db.Progress.task_plan_id,
        iot_task_db.Progress.task_id,iot_task_db.Progress.device_id,iot_task_db.Progress.start_time, iot_task_db.Progress.progress_uuid)\
        .join(iot_device_db.Device, iot_device_db.Device.id == iot_task_db.Progress.device_id)\
        .filter(iot_task_db.Progress.start_time <= datetime.now() + timedelta(seconds=timeout), 
        iot_task_db.Progress.status == 4, 
        iot_task_db.Progress.progress_status == 0,
        iot_device_db.Device.device_type_id.in_(device_type_id),)\
        .all()
        if query:
            for result in query:
                task_list.append(result._asdict())
            return True, task_list
        else:
            return True, []
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def get_task_action(task_id:int):
    """
    根据任务ID获取任务动作
    """
    action_list = []
    try:
        query = iot_task_db.session.query(iot_task_db.Action.id,iot_task_db.Action.task_id,
        iot_task_db.Action.device_id,iot_task_db.Action.device_ability_id,iot_task_db.Action.action_params)\
        .filter(iot_task_db.Action.task_id == task_id).all()
        if query:
            for result in query:
                action_list.append(result._asdict())
            return True, action_list
        else:
            return True, []
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

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


def update_task_progress(task_id:int, progress_status:int):
    """
    更新任务进度,
    执行状态(0:执行中, 1:已完成, 2:失败, 3:暂停, 4:待执行, 5:异常)
    """
    try:
        progress = 100 if progress_status == 1 else 0
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if progress_status == 1 or progress_status == 2 else None
        failure_reason = "un_post" if progress_status == 1 or progress_status == 2 or progress_status == 0 else None
        iot_task_db.session.query(iot_task_db.Progress).filter(iot_task_db.Progress.id == task_id)\
            .update({"status": progress_status, "progress": progress,"end_time": end_time ,"failure_reason": failure_reason,"update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        iot_task_db.session.commit()
        return True, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def get_item_definition(device_id:int):
    """
    根据设备ID获取设备定义
    """
    item_definition_list = []
    try:
        query = iot_device_db.session.query(iot_device_db.Device.device_type_id).filter(iot_device_db.Device.id == device_id).first()
        if query:
            query = iot_data_db.session.query(iot_data_db.ItemDefinition.item_code, iot_data_db.ItemDefinition.item_name,
            iot_data_db.ItemDefinition.unit,).filter(iot_data_db.ItemDefinition.device_type_id == query[0]).all()
            if query:
                for result in query:
                    item_definition_list.append(result._asdict())
            else:
                pass
            return True, item_definition_list
        else:
            return False, []
    except Exception as e:
        iot_device_db.session.rollback()
        iot_data_db.session.rollback()
        return False, str(e)
    finally:
        iot_device_db.session.close()
        iot_data_db.session.close()

def save_task_result(task_result:dict):
    """
    保存任务结果
    """
    try:
        result = iot_task_db.Result(
            task_plan_id=task_result.get("task_plan_id"),
            task_action_id=task_result.get("task_action_id"),
            task_progress_id=task_result.get("task_progress_id"),
            device_id=task_result.get("device_id"),
            file_path=task_result.get("file_path") or "",
            item_values=task_result.get("item_values"),
            parameters=task_result.get("parameters"),
            error_info=task_result.get("error_info"),
            post_status=task_result.get("post_status"),
            create_time=task_result.get("create_time"),
        )
        iot_task_db.session.add(result)
        iot_task_db.session.commit()
        return True, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def get_device_code_by_int(device_id:int):
    """
    根据设备ID获取设备编码
    """
    try:
        query = iot_device_db.session.query(iot_device_db.Device).filter(iot_device_db.Device.id == device_id).first()
        return True, query.to_dict()
    except Exception as e:
        iot_device_db.session.rollback()
        return False, str(e)
    finally:
        iot_device_db.session.close()



if __name__ == "__main__":
    # flag, result = get_device_id(["温振监控主机", "温振传感器"])
    # flag, result = end_timeout_task()
    # flag , result= get_task_plan([12, 13, 14, 15, 16],120*60)
    flag, result = get_task_action(2)
    # print(flag)
    # print(result)
    # host_type, result = get_device_host_type(24)
    # flag, result = update_task_progress(4043, 2)
    # flag, result = get_item_definition(25)
    save_mes = {'task_plan_id': 2, 'task_action_id': 104, 'task_progress_id': 3987, 
    'device_id': 29, 'file_path': None, 'item_value': None, 'parameters': None, 'error_info': '执行温振传感器主机任务失败',
    'post_status': 0, 'create_time': '2026-03-12 16:17:01',
    'item_values': None}
    # flag, result = save_task_result(save_mes)
    # flag, result = get_device_code_by_int(24)
    print(flag)
    print(result)
 
    