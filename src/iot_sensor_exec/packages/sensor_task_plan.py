#!/usr/bin/env python3
# coding=utf-8
import json
from typing import Tuple
from log_record.log_record import LogAndRecord
from iot_sensor_exec.edit_db import task_plan_db
import yaml

with open('data/configuration/log_path.yaml', 'r', encoding='utf-8') as f:
    log_config = yaml.safe_load(f)
log_path = log_config['log']['sensor_task_plan']


"""
    接受端侧的任务计划，对本地的数据库的任务计划进行添加、修改、删除操作，接受反馈
"""
class SensorTaskPlan:
    def __init__(self,):
        self.log_init = LogAndRecord()
        self.log_init.log_init(log_path, "sensor_task_plan")
        if not self.log_init:
            raise Exception("日志初始化失败")
        self.logger = self.log_init.logger
    
    def execute(self, data: dict)->str:
        """
        总入口,针对数据进行处理
        """
        func_value = data.get("func_value")
        device_code = data.get("device_code")
        message_id = data.get("message_id")
        mes = data.get("data")
        if not isinstance(mes, dict):
            return json.dumps({"code": "500", "func_value": func_value, "device_code": device_code,
                               "message_id": message_id, "error_info": "data字段缺失或格式错误", "data": ""})
        operation = mes.get("operation")
        error_info = ""
        # 200:成功 400:失败 500:异常
        if operation == 0:#添加
            code , error_info = self.__add_task_plan(mes)
        elif operation == 1:#修改
            code , error_info = self.__update_task_plan(mes)
        elif operation == 2:#删除
            code , error_info = self.__delete_task_plan(mes)
        else:
            code = 500
            error_info = "操作类型错误"

        return json.dumps({"code": str(code), "func_value": func_value, "device_code": device_code, "message_id": message_id, "error_info": error_info, "data": ""})

    def __add_task_plan(self, data: dict)->Tuple[int, str]:
        """
        添加任务计划
        """
        flag, error_info = task_plan_db.add_task_plan(data)
        if flag:
            return 200, None
        else:
            self.logger.info(f"任务计划添加失败, 原始数据: {data}, 错误信息: {error_info}")
            return 400, str(error_info)

    def __update_task_plan(self, data: dict)->Tuple[int, str]:
        """
        修改任务计划
        """
        flag, error_info = task_plan_db.update_task_plan(data)
        if flag:
            return 200, None
        else:
            self.logger.info(f"任务计划修改失败, 原始数据: {data}, 错误信息: {error_info}")
            return 400, str(error_info)

    def __delete_task_plan(self, data: dict)->Tuple[int, str]:
        """
        删除任务计划
        """
        flag, error_info = task_plan_db.delete_task_plan(data)
        if flag:
            return 200, None
        else:
            self.logger.info(f"任务计划删除失败, 原始数据: {data}, 错误信息: {error_info}")
            return 400, str(error_info)



if __name__ == "__main__":
    data =  {"data": {"plan_execution_time": "2026-03-09T16:59:38.597", "cycle_execution_unit": 4, "task_id": 148, "strategy": 1, "operation": 1, "plan_id": 295, "plan_name": "测试1", "enabled": 1}, "device_code": "5648468468", "func_value": "iot_edit_sensor_task_plan", "message_id": "3b76f5e6-640d-48b2-825d-c5952df85c53"}