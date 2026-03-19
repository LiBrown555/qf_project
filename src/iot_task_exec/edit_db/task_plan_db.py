#!/usr/bin/env python3
# coding=utf-8

import sys
import os
import uuid
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import or_, and_, func
from db_orm import iot_task_db, iot_device_db

def query_task_plan(device_type_id: list):
    """
    查询任务计划符合条件的计划,根据设备类型ID过滤
    v1.1新增设备分类参数用作筛选操作,过滤掉不满足条件的任务计划
    条件:
    1. plan_status = 1 #已启动
    2. progress_generate = 0 #未生成
       OR progress_generate = 1 且 update_time 日期 < 今天（循环计划次日及以后需重新生成进度）
    3. 关联 iot_task、iot_device，过滤设备类型
    使用 JOIN 将原来 2N+1 次查询优化为 1 次查询
    """
    try:
        today = datetime.now().date()
        rows = iot_task_db.session.query(
                iot_task_db.Plan.id, iot_task_db.Plan.task_id,
                iot_task_db.Plan.plan_type, iot_task_db.Plan.execute_time,
                iot_task_db.Plan.cycle_config, iot_task_db.Plan.cycle_start_time,
                iot_task_db.Plan.cycle_end_time, iot_task_db.Plan.create_time,
                iot_task_db.Plan.update_time)\
            .join(iot_task_db.Task, iot_task_db.Task.id == iot_task_db.Plan.task_id)\
            .join(iot_device_db.Device, iot_device_db.Device.id == iot_task_db.Task.device_id)\
            .filter(
                iot_task_db.Plan.plan_status == 1,
                iot_device_db.Device.device_type_id.in_(device_type_id),
                or_(
                    iot_task_db.Plan.progress_generate == 0,
                    and_(
                        iot_task_db.Plan.progress_generate == 1,
                        func.date(iot_task_db.Plan.update_time) < today
                    )
                )
            )\
            .order_by(iot_task_db.Plan.create_time.desc())\
            .all()
        mes_list = [row._asdict() for row in rows]
        return True, mes_list
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def delete_task_plan_progress_by_id(data_list: list):
    """
    根据id列表删除任务计划进度,需要删除对应的任务进度
    条件:
    1. task_plan_id 在 data_list 中
    2. status = 4
    3. progress_status = 0
    """
    try:
        for data in data_list:
            query = iot_task_db.session.query(iot_task_db.Progress)\
            .filter(iot_task_db.Progress.task_plan_id == data.get("id"), 
            iot_task_db.Progress.status == 4, 
            iot_task_db.Progress.progress_status == 0)
            if query.count() > 0:#已经存在对应的任务，需要删除
                query.delete(synchronize_session=False)
                iot_task_db.session.commit()
            else:
                pass
        return True, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def add_task_plan_progress(data_list: list):
    """
    添加任务计划进度
    """
    try:
        mes_list = []
        task_ids = list({data.get("task_id") for data in data_list if data.get("task_id")})
        task_device_map = {
            row.id: row.device_id
            for row in iot_task_db.session.query(iot_task_db.Task.id, iot_task_db.Task.device_id)
            .filter(
                iot_task_db.Task.id.in_(task_ids),
                iot_task_db.Task.status == 0,
                iot_task_db.Task.is_delete == 0
            ).all()
        }
        for data in data_list:
            device_id = task_device_map.get(data.get("task_id"))
            if device_id is not None:
                data["device_id"] = device_id
                mes_list.append(data)
        if mes_list:
            datas = []
            for data in mes_list:
                datas.append(iot_task_db.Progress(
                    task_plan_id = data.get("id"),
                    task_id = data.get("task_id"),
                    device_id = data.get("device_id"),
                    progress = 0,
                    task_detail = None,
                    status = 4,
                    start_time = data.get("start_time"),
                    progress_status = 0,
                    progress_uuid = str(uuid.uuid4()),
                    sync_time = data.get("sync_time"),
                    create_time = data.get("create_time"),
                    update_time = data.get("update_time"),
                ))
            iot_task_db.session.add_all(datas)
            iot_task_db.session.commit()
            return True, mes_list
        else:
            return True, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def update_task_plan_status():
    """
    更新任务计划状态
    """
    try:
        iot_task_db.session.query(iot_task_db.Plan)\
        .filter(iot_task_db.Plan.plan_status == 1, iot_task_db.Plan.cycle_end_time <= datetime.now().strftime("%Y-%m-%d %H:%M:%S"))\
        .update({"plan_status": 2})
        iot_task_db.session.commit()
        return True, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

def update_task_plan(data_list: list):
    """
    更新任务计划进度
    """
    try:
        for data in data_list:
            update_data = {
                "id": data.get("id"),
                "progress_generate": data.get("progress_generate"),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            iot_task_db.session.query(iot_task_db.Plan).filter(iot_task_db.Plan.id == data.get("id")).update(update_data)
        iot_task_db.session.commit()
        return True, None
    except Exception as e:
        iot_task_db.session.rollback()
        return False, str(e)
    finally:
        iot_task_db.session.close()

if __name__ == "__main__":
    add_list = [{'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime (2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 16:00:00', 'progress_generate': 1},
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 16:30:00', 'progress_generate': 1},
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 17:00:00', 'progress_generate': 1}, 
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 17:30:00', 'progress_generate': 1}, 
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 18:00:00', 'progress_generate': 1}, 
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 19:00:00', 'progress_generate': 1},
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 20:00:00', 'progress_generate': 1},
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 20:30:00', 'progress_generate': 1},
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 21:00:00', 'progress_generate': 1},
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 21:30:00', 'progress_generate': 1},
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 22:00:00', 'progress_generate': 1},
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 23:00:00', 'progress_generate': 1},
    {'id': 2, 'task_id': 2, 'sync_time': datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime(2026, 3, 16, 15, 35, 5), 'start_time': '2026-03-16 23:30:00', 'progress_generate': 1}]
    # flag, mes_list = add_task_plan_progress(add_list)
    flag, mes_list = update_task_plan_status()
    if flag:
        print(mes_list)
    # flag, mes_list = add_task_plan_progress([{"id": 148}])
    # flag, mes_list = query_task_plan([12, 13, 14, 15, 16])
    # if flag:
    #     print(mes_list)
    # if flag:
    #     print(mes_list)
    # print(datetime(2026, 3, 10, 10, 44, 40).strftime("%Y-%m-%d %H:%M:%S"))
    