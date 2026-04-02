import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from db_orm import iot_task_db, iot_device_db

def query_unpost_progress()->list:
    """
    v1.1补全任务进度数据,包括任务计划ID、任务进度、任务开始时间、任务结束时间、任务状态、设备编码、任务进度UUID
    查询未推送的任务进度,
    返回数据格式:
    [{'id': 4041, 'task_srv_id': 1, 'task_plan_srv_id': 1, 'device_type_id': 1, 'progress': 50, 'start_time': '2026-03-27 10:00:00', 'end_time': '2026-03-27 10:00:00', 'status': 0, 'device_code': '8393423428', 'progress_uuid': 'c96eeee4-6633-46c0-98eb-e4fe0c12490d'},
     {'id': 4042, 'task_srv_id': 1, 'task_plan_srv_id': 1, 'device_type_id': 1, 'progress': 50, 'start_time': '2026-03-27 10:00:00', 'end_time': '2026-03-27 10:00:00', 'status': 0, 'device_code': '8393423428', 'progress_uuid': '711ce61b-2502-4953-84c6-8e6fb36996e0'},
      {'id': 4043, 'task_srv_id': 1, 'task_plan_srv_id': 1, 'device_type_id': 1, 'progress': 50, 'start_time': '2026-03-27 10:00:00', 'end_time': '2026-03-27 10:00:00', 'status': 0
    """
    result_list = []
    try:
        query = iot_task_db.session.query(iot_task_db.Progress.id, iot_task_db.Task.srv_id.label('task_srv_id'),
        iot_task_db.Plan.srv_id.label('task_plan_srv_id'), iot_task_db.Progress.device_id,
        iot_task_db.Progress.progress,iot_task_db.Progress.start_time,iot_task_db.Progress.end_time,
        iot_task_db.Progress.status, iot_task_db.Progress.progress_uuid)\
        .join(iot_task_db.Plan, iot_task_db.Plan.id == iot_task_db.Progress.task_plan_id)\
        .join(iot_task_db.Task, iot_task_db.Task.id == iot_task_db.Progress.task_id)\
        .filter(iot_task_db.Progress.failure_reason == "un_post").all()
        if query:
            for result in query:
                device_id = result.device_id
                device_query = iot_device_db.session.query(iot_device_db.Device.id, iot_device_db.Device.device_type_id,iot_device_db.Device.device_code)\
                .filter(iot_device_db.Device.id == device_id).first()
                if device_query:
                    result_list.append({
                        "id": result.id,
                        "task_srv_id": result.task_srv_id,
                        "task_plan_srv_id": result.task_plan_srv_id,
                        "device_type_id": device_query.device_type_id,
                        "progress": result.progress,
                        "start_time": result.start_time,
                        "end_time": result.end_time,
                        "status": result.status,
                        "device_code": device_query.device_code,
                        "progress_uuid": result.progress_uuid
                    })
                else:
                    pass
            return True, result_list
        else:
            return True, result_list
    except Exception as e:
        iot_device_db.session.rollback()
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_device_db.session.close()
        iot_task_db.session.close()

def update_progress_post_status(mes_list: list):
    """
    更新任务进度推送状态,
    返回数据格式:
    """
    update_mes = []
    try:
        for mes in mes_list:
            update_mes.append({
                "id": mes.get("id"),
                "failure_reason": "post_success",
            })
        iot_task_db.session.bulk_update_mappings(
            iot_task_db.Progress,
            update_mes,
        )
        iot_task_db.session.commit()
        return True, "更新成功"
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def get_progress_by_uuid(uuid: str):
    """
    根据任务进度UUID查询任务进度
    """
    try:
        query = iot_task_db.session.query(iot_task_db.Progress).filter(iot_task_db.Progress.progress_uuid == uuid).first()
        if query:
            return True, query.to_dict()
        else:
            return False, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()


if __name__ == "__main__":
    flag, result = query_unpost_progress()
    # flag, result = get_progress_by_uuid("ff398873-0a15-4692-96e7-f0e082a46fee")
    print(flag)
    print(result)
    # flag, result = update_progress_post_status(result)
    # print(flag)
    # print(result)