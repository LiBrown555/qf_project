#!/usr/bin/env python3
# coding=utf-8

import yaml,json,requests,time
import sys,threading
import os
import uuid
from datetime import datetime
from collections import OrderedDict
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from iot_sensor_exec.edit_db import task_post_db
from log_record.log_record import LogAndRecord

with open('data/configuration/log_path.yaml', 'r', encoding='utf-8') as f:
    log_config = yaml.safe_load(f)
log_path = log_config['log']['sensor_task_post']
with open('data/configuration/iot_device.yaml', 'r', encoding='utf-8') as f:
    iot_device_config = yaml.safe_load(f)
sensor_url = iot_device_config['device_status_post']['sensor_url']
camera_url = iot_device_config['device_status_post']['camera_url']
sensor_device_type_id = iot_device_config['device_type_id']['wenzhen_id']
camera_device_type_id = iot_device_config['device_type_id']['camera_id']

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()
    
    def get(self, key: str):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key: str, value: any):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
    
    def clear(self):
        self.cache.clear()
    

   

class SensorTaskPost:
    def __init__(self):
        self.log_init = LogAndRecord()
        self.log_init.log_init(log_path, "sensor_task_post")
        if not self.log_init:
            raise Exception("日志初始化失败")
        
        self.progress_uuid_cache = LRUCache(20)
        self.device_code_uuid_cache = LRUCache(200)
        self.logger = self.log_init.logger
        self._stop_event = threading.Event()
        threading.Thread(target=self.schedule_task, daemon=True).start()

    def stop(self):
        """外部调用此方法通知线程停止"""
        self._stop_event.set()
        self.logger.info("任务结果推送线程停止")
    
    def schedule_task(self):
        """
        定时任务
        """
        while not self._stop_event.is_set():
            self.exec()
            self._stop_event.wait(timeout=1)

    def exec(self):
        """
        执行任务结果推送任务
        """
        flag, result = task_post_db.get_unpost_mes(3)#默认查询3天内的未推送任务结果
        if flag:
            if result:
                self._build_post_mes(result)
                time.sleep(3)
            else:
                time.sleep(10)
        else:
            self.logger.error(f"任务结果查询失败: {result}")
            time.sleep(30)
    
    @staticmethod
    def _fmt_dt(val):
        """将 datetime 对象转为秒级时间戳，非 datetime 原样返回"""
        if isinstance(val, datetime):
            return str(int(val.timestamp()))
        return val
    
    def _build_post_mes(self, mes_list: list):
        """
        构建推送消息
        """
        post_mes_list = []
        flag, item_definition_dict = task_post_db.get_item_definition()
        if not flag:
            self.logger.error(f"获取设备定义失败: {item_definition_dict}")
            return False
        flag, result_list = task_post_db.get_mes_code_by_result_dict(mes_list)
        if flag:
            if result_list:
                for result in result_list:
                    task_item_list = []
                    id = result.get("id")
                    device_code = result.get("device_code")
                    progress_uuid = result.get("progress_uuid")
                    task_srv_id = result.get("srv_id")
                    action_params = result.get("action_params")
                    task_item_values = result.get("item_values")
                    file_path = result.get("file_path")
                    error_info = result.get("error_info")
                    device_type_id = result.get("device_type_id")
                    capture_time = result.get("create_time")
                    if device_type_id in sensor_device_type_id: #温振传感器
                        for action_param in action_params:
                            item_code = item_definition_dict.get(action_param.get("item"))
                            if item_code:
                                task_item_list.append({
                                    "item": action_param.get("item"),
                                    "value": task_item_values.get(item_code) if task_item_values.get(item_code) else 0,
                                })
                            else:
                                task_item_list.append({
                                    "item": action_param.get("item"),
                                    "value": 0,
                                })
                                self.logger.error(f"设备定义为{item_code}的设备定义不存在: {item_definition_dict}")
                        post_mes_list.append({
                            "id": id,
                            "url": sensor_url,
                            "file_parameter": None,
                            "post_message": {
                                "func_value": "iot_push_sensor_data",
                                "device_code": device_code,
                                "message_id": str(uuid.uuid4()),
                                "error_info": error_info,
                                "data": json.dumps({
                                    "task_progress_uuid": progress_uuid,
                                    "task_action_id": task_srv_id,
                                    "task_action_params": task_item_list,
                                    "file_parameter": None,
                                    "capture_time": self._fmt_dt(capture_time)
                                }, ensure_ascii=False)
                            }
                        })
                    elif device_type_id in camera_device_type_id:#相机
                        post_mes_list.append({
                            "id": id,
                            "url": camera_url,
                            "file_parameter": file_path,
                            "post_message": {
                                "func_value": "iot_push_capture_data",
                                "device_code": device_code,
                                "message_id": str(uuid.uuid4()),
                                "error_info": error_info,
                                "data": json.dumps({
                                    "task_progress_uuid": progress_uuid,
                                    "task_action_id": task_srv_id,
                                    "task_action_param": action_params,
                                    "file_parameter": file_path,
                                    "capture_time": self._fmt_dt(capture_time)
                                }, ensure_ascii=False)
                            }
                        })
                    else:#其他设备类型不推送
                        self.logger.warning(f"设备类型为{device_type_id}的设备不推送任务结果")
                        continue

            else:
                return False
        else:
            self.logger.error(f"任务结果查询失败: {result_list}")
            return False

        update_result_list = []
        if post_mes_list:
            for post_mes in post_mes_list:
                id = post_mes.get("id")
                url = post_mes.get("url")
                post_message = post_mes.get("post_message")
                file_path = post_mes.get("file_parameter")
                if file_path:
                    with open(file_path, "rb") as file:
                        response = requests.post(url, data=post_message, files={"file": file})
                        if response.status_code == 200:
                            update_result_list.append({"id": id, "post_status": 1})
                            self.logger.info(f"推送任务结果成功: {response.json()}")
                        else:
                            update_result_list.append({"id": id, "post_status": 2})
                            self.logger.error(f"推送任务结果失败,推送数据:{post_message}")
                else:
                    response = requests.post(url, data=post_message)
                    if response.status_code == 200:
                        update_result_list.append({"id": id, "post_status": 1})
                        self.logger.info(f"推送任务结果成功: {response.json()}")
                    else:
                        update_result_list.append({"id": id, "post_status": 2})
                        self.logger.error(f"推送任务结果失败,推送数据:{post_message}")
        if update_result_list:
            flag, result = task_post_db.update_result_post_status(update_result_list)
            if flag:
                pass
            else:
                self.logger.error(f"更新任务结果推送状态失败: {result}")

if __name__ == "__main__":
    sensor_task_post = SensorTaskPost()
    sensor_task_post.exec()