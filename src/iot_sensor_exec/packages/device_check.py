#!/usr/bin/env python3
# coding=utf-8
import yaml
import sys
import os, socket, threading
import uuid, queue
import schedule
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from iot_sensor_exec.edit_db import device_check_db
from log_record.log_record import LogAndRecord
with open('data/configuration/log_path.yaml', 'r', encoding='utf-8') as f:
    log_config = yaml.safe_load(f)
log_path = log_config['log']['device_check']

"""
    iot传感器基本状态信息定时获取iot_device_attr表, 用于端侧设备状态更新，主动上传数据到服务器
"""

class DeviceCheck:
    def __init__(self):
        self.log_init = LogAndRecord()
        self.log_init.log_init(log_path, "device_check")
        if not self.log_init:
            raise Exception("日志初始化失败")
        self.logger = self.log_init.logger
        self.device_post_time = None
        self.device_name = None
        self.get_device_config()
        self.recv_status = False #接受状态为True，证明数据已经更新完成
        self.sensor_recv_mes = queue.Queue()
        self.camera_recv_mes = queue.Queue()
        self._stop_event = threading.Event()
        threading.Thread(target=self.schedule_task, daemon=True).start()

    def get_device_config(self):
        """
        获取设备配置
        """
        with open('data/configuration/iot_device.yaml', 'r', encoding='utf-8') as f:
            iot_device_config = yaml.safe_load(f)
        self.device_post_time = int(iot_device_config['device_status_post']['device_post_time'])
        self.device_name = iot_device_config['device_status_post']['device_name']
        self.sensor_device_type_id = iot_device_config['device_type_id']['wenzhen_id']
        self.camera_device_type_id = iot_device_config['device_type_id']['camera_id']
        self.logger.info(f"设备配置获取成功: 设备状态推送时间间隔: {self.device_post_time}, 设备名称: {self.device_name}")

    def stop(self):
        """外部调用此方法通知线程停止"""
        self._stop_event.set()
        self.logger.info("设备状态推送线程停止")

    def schedule_task(self):
        """
        定时任务
        """
        schedule.every(self.device_post_time).seconds.do(self.exec)
        while not self._stop_event.is_set():
            schedule.run_pending()
            self._stop_event.wait(timeout=1)
    
    def exec(self):
        """
        执行设备检查任务
        """
        device_message = device_check_db.get_device_message(self.device_name)
        for device in device_message:
            if device["device_type_id"] in self.sensor_device_type_id: #传感器
                result = self._sensor_host_check(device)
                if result:
                    self.sensor_recv_mes.put(result)
            elif device["device_type_id"] in self.camera_device_type_id: #相机
                result = self._camera_host_check(device)
                if result:
                    self.camera_recv_mes.put(result)
            else:
                pass
        self.recv_status = True
    
    def _sensor_host_check(self, device: dict):
        """
        温振监控设备状态在线监控检查
        """
        self.logger.info(f"温振监控设备状态在线监控检查: {device}")
        recv_data = {}
        result = {}
        davice_status = []
        host_ip = device["ip"]
        host_port = device["port"]
        if not self.check_port(host_ip, host_port):
            recv_data = {"device_code": device["device_code"], "online_status": 0, "device_base_info": {},}
        else:
            recv_data = {"device_code": device["device_code"], "online_status": 1, "device_base_info": {},}
        davice_status.append(recv_data)
        for child_mes in device["child_mes"]:
            parameter: dict = child_mes["parameter"]
            recv_data = {
                "device_code": child_mes["device_code"],
                "online_status": child_mes.get("online_status",0),
                "device_base_info": {
                    "battery_percentage": parameter.get("battery_percentage",0),
                    "signal": parameter.get("signal",0)
                    }
                }
            davice_status.append(recv_data)
        result = {
            "func_value": "iot_push_sensor_status",
            "device_code": device["device_code"],
            "message_id": str(uuid.uuid4()),
            "error_info": None,
            "data": {
                "device_status": davice_status
            }
        }
        self.logger.info(f"温振监控设备状态在线监控检查结果: {result}")
        return result
    def _camera_host_check(self, device: dict):
        """
        相机设备状态在线监控检查
        """
        self.logger.info(f"相机设备状态在线监控检查: {device}")
        recv_data = {}
        result = {}
        davice_status = []
        host_ip = device["ip"]
        host_port = device["port"]
        if not self.check_port(host_ip, host_port):
            recv_data = {"device_code": device["device_code"], "online_status": 0}
        else:
            recv_data = {"device_code": device["device_code"], "online_status": 1}
        davice_status.append(recv_data)
        for child_mes in device["child_mes"]:
            recv_data = {
                "device_code": child_mes["device_code"],
                "online_status": child_mes.get("online_status",0),
                }
            davice_status.append(recv_data)
        result = {
            "func_value": "iot_push_device_status",
            "device_code": device["device_code"],
            "message_id": str(uuid.uuid4()),
            "error_info": None,
            "data": {
                "device_status": davice_status
            }
        }
        self.logger.info(f"相机设备状态在线监控检查结果: {result}")
        return result
    def check_port(self, ip: str, port: int, timeout: float = 10.0) -> bool:
        """
        检测指定 IP 的端口是否可达
        :param ip: 目标 IP
        :param port: 目标端口
        :param timeout: 超时时间（秒）
        :return: True=端口开放, False=不可达
        """
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


if __name__ == "__main__":
    device_check = DeviceCheck()
    # time.sleep(10)
    device_check.exec()