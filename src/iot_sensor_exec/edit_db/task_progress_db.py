import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from db_orm import iot_task_db, iot_device_db

def query_unpost_progress()->list:
    """
    查询未推送的任务进度,
    返回数据格式:
    [{'id': 4041, 'device_code': '8393423428', 'progress_uuid': 'c96eeee4-6633-46c0-98eb-e4fe0c12490d'},
     {'id': 4042, 'device_code': '8393423428', 'progress_uuid': '711ce61b-2502-4953-84c6-8e6fb36996e0'},
      {'id': 4043, 'device_code': '8393423428', 'progress_uuid': '61841498-1558-407e-97b4-5c0f6b672c55'}]
    """
    result_list = []
    try:
        query = iot_task_db.session.query(iot_task_db.Progress.id, iot_task_db.Progress.device_id, iot_task_db.Progress.status, iot_task_db.Progress.progress_uuid)\
        .filter(iot_task_db.Progress.failure_reason == "un_post").all()
        if query:
            for result in query:
                device_id = result.device_id
                device_query = iot_device_db.session.query(iot_device_db.Device.id, iot_device_db.Device.device_code)\
                .filter(iot_device_db.Device.id == device_id).first()
                if device_query:
                    result_list.append({
                        "id": result.id,
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
    # flag, result = query_unpost_progress()
    flag, result = get_progress_by_uuid("ff398873-0a15-4692-96e7-f0e082a46fee")
    print(flag)
    print(result)
    # flag, result = update_progress_post_status(result)
    # print(flag)
    # print(result)