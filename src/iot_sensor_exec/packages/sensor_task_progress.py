#!/usr/bin/env python3
# coding=utf-8

import yaml,pymysql
import sys
import os, queue, time, threading
import uuid
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from iot_sensor_exec.edit_db import task_progress_db
from log_record.log_record import LogAndRecord
with open('data/configuration/log_path.yaml', 'r', encoding='utf-8') as f:
    log_config = yaml.safe_load(f)
log_path = log_config['log']['sensor_task_progress']
with open('data/configuration/iot_device.yaml', 'r', encoding='utf-8') as f:
    iot_device_config = yaml.safe_load(f)
sensor_device_type_id = iot_device_config['device_type_id']['wenzhen_id']
camera_device_type_id = iot_device_config['device_type_id']['camera_id']

"""
    根据iot数据库的task_progress表, 查询未推送的任务进度, 并推送至端侧
"""
class SensorTaskProgress:
    def __init__(self):
        self.log_init = LogAndRecord()
        self.log_init.log_init(log_path, "sensor_task_progress")
        if not self.log_init:
            raise Exception("日志初始化失败")
        self.logger = self.log_init.logger
        self.sensor_recv_mes = queue.Queue()
        self.camera_recv_mes = queue.Queue()
        self._stop_event = threading.Event()
        threading.Thread(target=self.schedule_task, daemon=True).start()

    def stop(self):
        """外部调用此方法通知线程停止"""
        self._stop_event.set()
        self.logger.info("任务进度推送线程停止")

    def schedule_task(self):
        """
        定时任务
        """
        while not self._stop_event.is_set():
            self.exec()
            self._stop_event.wait(timeout=5)
    
    @staticmethod
    def _fmt_dt(val):
        """将 datetime 对象转为秒级时间戳，非 datetime 原样返回"""
        if isinstance(val, datetime):
            return str(int(val.timestamp()))
        return val

    def exec(self):
        """
        执行任务进度推送任务
        v1.1 补全任务进度数据,包括任务计划ID、任务进度、任务开始时间、任务结束时间、任务状态、设备编码、任务进度UUID
        """
        flag, result = task_progress_db.query_unpost_progress()
        if flag:
            if result:
                flag, mes = task_progress_db.update_progress_post_status(result)
                if flag:
                    for mes in result:
                        device_type_id = mes.get("device_type_id")
                        if device_type_id in sensor_device_type_id:
                            self.sensor_recv_mes.put({
                                "func_value": "iot_push_task_progress",
                                "device_code": mes.get("device_code"),
                                "message_id": str(uuid.uuid4()),
                                "error_info": None,
                                "data": {
                                    "task_progress_uuid": mes.get("progress_uuid"),
                                    "task_plan_id": mes.get("task_plan_srv_id"),
                                    "task_id": mes.get("task_srv_id"),
                                    "progress_percent": mes.get("progress"),
                                    "task_progress_status": mes.get("status"),
                                    "start_time": self._fmt_dt(mes.get("start_time")),
                                    "end_time": self._fmt_dt(mes.get("end_time")),
                                },
                            })
                        elif device_type_id in camera_device_type_id:
                            self.camera_recv_mes.put({
                                "func_value": "iot_push_task_progress",
                                "device_code": mes.get("device_code"),
                                "message_id": str(uuid.uuid4()),
                                "error_info": None,
                                "data": {
                                    "task_progress_uuid": mes.get("progress_uuid"),
                                    "task_plan_id": mes.get("task_plan_srv_id"),
                                    "task_id": mes.get("task_srv_id"),
                                    "progress_percent": mes.get("progress"),
                                    "task_progress_status": mes.get("status"),
                                    "start_time": self._fmt_dt(mes.get("start_time")),
                                    "end_time": self._fmt_dt(mes.get("end_time")),
                                },
                            })
                        else:
                            pass
                    self.logger.info(f"任务进度推送成功: {result}")
                else:
                    self.logger.error(f"任务进度推送失败: {mes}")

        else:
            self.logger.error(f"任务进度查询失败: {result}")

    def _save_progress(self, progress: dict):
        """
        保存任务进度到udmp数据库中，临时存入
        """
        conn = pymysql.connect(host="120.26.22.61", port=15698, user="root", password="123456", database="udmp",charset="utf8mb4",cursorclass=pymysql.cursors.DictCursor)
        query_sql = "SELECT id FROM task_progress WHERE progress_uuid = %s"
        with conn.cursor() as cur:
            cur.execute(query_sql, (progress.get('progress_uuid'),))
            result = cur.fetchone()
            if result:#数据已经存在，只需要更新
                update_sql = "UPDATE task_progress SET progress = %s, status = %s, end_time = %s, sync_time = %s, update_time = %s WHERE id = %s"
                cur.execute(update_sql, (progress.get('progress'), progress.get('status'), progress.get('end_time'), progress.get('update_time'), progress.get('update_time'), result["id"]))
                conn.commit()
            else:#数据不存在，需要插入
                save_mes = (progress.get('task_plan_id'), progress.get('task_id'), progress.get('device_id'), 
                progress.get('progress'), progress.get('task_detail'), progress.get('status'), 
                progress.get('pause_time'), progress.get('pause_reason'), progress.get('resume_time'), 
                progress.get('start_time'), progress.get('end_time'), None, 
                progress.get('progress_uuid'), progress.get('update_time'), 
                progress.get('create_time'), progress.get('update_time'),0)
                cur.execute("INSERT INTO task_progress (task_plan_id, task_id, device_id, progress,\
                task_detail, status, pause_time, pause_reason, resume_time, start_time, end_time, \
                failure_reason, progress_uuid,sync_time, create_time,update_time,is_delete) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", save_mes)
                conn.commit()
        conn.close()


if __name__ == "__main__":
    sensor_task_progress = SensorTaskProgress()
    # print(sensor_task_progress.exec())
    # sensor_task_progress.stop()
    import datetime
    data = {'id': 4440, 'task_plan_id': 2, 'task_id': 2, 'device_id': 68, 'progress': 100, 'task_detail': None, 'status': 1, 'pause_time': None, 'pause_reason': None, 'resume_time': None, 'start_time': datetime.datetime(2026, 3, 15, 15, 30), 'end_time': datetime.datetime(2026, 3, 15, 15, 29, 27), 'failure_reason': 'post_success', 'progress_status': 0, 'progress_uuid': 'ff398873-0a15-4692-96e7-f0e082a46fee', 'sync_time': datetime.datetime(2026, 1, 23, 8, 51, 12), 'create_time': datetime.datetime(2026, 1, 23, 8, 51, 12), 'update_time': datetime.datetime(2026, 3, 15, 15, 40, 12)}
    sensor_task_progress._save_progress(data)
    time.sleep(10)
