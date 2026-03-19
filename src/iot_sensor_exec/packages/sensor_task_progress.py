#!/usr/bin/env python3
# coding=utf-8

import yaml,pymysql
import sys
import os, queue, time, threading
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from iot_sensor_exec.edit_db import task_progress_db
from log_record.log_record import LogAndRecord
with open('data/configuration/log_path.yaml', 'r', encoding='utf-8') as f:
    log_config = yaml.safe_load(f)
log_path = log_config['log']['sensor_task_progress']

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
        self.recv_mes = queue.Queue()
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
    
    def exec(self):
        """
        执行任务进度推送任务
        """
        flag, result = task_progress_db.query_unpost_progress()
        if flag:
            if result:
                flag, mes = task_progress_db.update_progress_post_status(result)
                if flag:
                    for mes in result:
                        self.recv_mes.put({
                            "func_value": "iot_push_task_progress",
                            "device_code": mes.get("device_code"),
                            "message_id": str(uuid.uuid4()),
                            "error_info": None,
                            "data": {
                                "task_progress_uuid": mes.get("progress_uuid"),
                                "task_progress_status": mes.get("status"),
                            },
                        })
                    self.logger.info(f"任务进度推送成功: {result}")
                else:
                    self.logger.error(f"任务进度推送失败: {mes}")

                save_flag, save_result = task_progress_db.get_progress_by_uuid(mes.get("progress_uuid"))
                if save_flag:
                    self._save_progress(save_result)
                else:
                    self.logger.error(f"任务进度查询失败: {save_result}")
        else:
            self.logger.error(f"任务进度查询失败: {result}")
        return self.recv_mes

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
