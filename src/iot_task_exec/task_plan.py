#!/usr/bin/env python3
# coding=utf-8

"""
v1.1
任务计划执行文件,通过检测数据库中的任务计划iot_task_plan表,
如果需要执行,则下发24小时以内任务到iot_task_process表中,并根据任务计划类型进行执行
新增检测计划超时功能
"""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from log_record.log_record import LogAndRecord
from edit_db import task_plan_db
from datetime import datetime
import yaml 
import signal
import time
import schedule

with open('data/configuration/log_path.yaml', 'r', encoding='utf-8') as f:
    log_config = yaml.safe_load(f)
log_path = log_config['log']['task_plan']

with open('data/configuration/iot_device.yaml', 'r', encoding='utf-8') as f:
    iot_device_config = yaml.safe_load(f)
device_type = iot_device_config['device_type']
device_type_id :list = [device_type[mes] for mes in device_type.keys() if mes]

class TaskPlan:
    def __init__(self,):
        self.log_init = LogAndRecord()
        self.log_init.log_init(log_path, "task_plan")
        if not self.log_init:
            raise Exception("日志初始化失败")
        self.logger = self.log_init.logger
        self.temp_plan_list = []
        schedule.every(60).seconds.do(self.update_task_plan_status)

    def update_task_plan_status(self,):
        """
        v1.1更新任务计划状态，将已过期的任务计划状态更改为已过期
        """
        flag, err_info = task_plan_db.update_task_plan_status()
        if not flag:
            self.logger.error(f"任务计划状态更新失败，错误信息: {err_info}")
        else:
            self.logger.info(f"任务计划状态更新成功")

    def detect_task_plan(self):
        """
        检测任务计划
        """
        if device_type_id:#有需要根据任务过滤的设备类型
            flag, mes_list = task_plan_db.query_task_plan(device_type_id)#v1.1新增设备分类参数用作筛选操作,过滤掉不满足条件的任务计划
            if flag:
                if mes_list:
                    self.temp_plan_list = mes_list.copy()
                self.logger.info(f"检测到任务计划: {self.temp_plan_list}")
                return True
            else:
                self.logger.error(f"检测任务计划失败，错误信息: {mes_list}")
                return False
        else:#不需要根据任务过滤的设备类型
            return False
    
    def compare_task_plan(self):
        """
        对比任务计划，检测新增、删除、更新三种变更：
        - 新增：DB 中存在但 temp 中不存在的 id → 生成新 progress
        - 删除：temp 中存在但 DB 中不存在的 id → 删除对应 progress
        - 更新：id 相同但内容不同 → 重新生成 progress
        """
        flag, mes_list = task_plan_db.query_task_plan(device_type_id)
        if not flag:
            self.logger.error(f"对比任务计划失败，错误信息: {mes_list}")
            return False

        db_list = mes_list if mes_list else []

        # 构建 id → plan 的字典，便于 O(1) 查找
        temp_dict = {plan.get("id"): plan for plan in self.temp_plan_list}
        db_dict   = {plan.get("id"): plan for plan in db_list}

        temp_ids = set(temp_dict.keys())
        db_ids   = set(db_dict.keys())

        new_ids     = db_ids - temp_ids          # 新增计划
        deleted_ids = temp_ids - db_ids          # 被删除的计划
        common_ids  = temp_ids & db_ids          # 共有计划（检测更新）

        new_plans     = [db_dict[pid] for pid in new_ids]
        deleted_plans = [temp_dict[pid] for pid in deleted_ids]
        updated_plans = [db_dict[pid] for pid in common_ids if temp_dict[pid] != db_dict[pid]]

        # 有任何变更时更新内存缓存
        if new_plans or deleted_plans or updated_plans:
            self.temp_plan_list = db_list.copy()
            self.logger.info(f"临时任务计划列表已更新")

        # 返回需要新建 progress 的计划（新增 + 更新），由调用方统一调用 __add_task_plan_progress
        plans_to_add = new_plans + updated_plans
        if plans_to_add:
            self.logger.info(f"待新建进度的任务计划: {plans_to_add}")
            return plans_to_add

        return False


    def __parse_today_tasks(self, plan_list: list) -> list:
        """
        解析今日待执行任务时间列表
        - plan_type=1: 日计划，时间范围内每天执行
        - plan_type=2: 周计划，cycle_config['weekdays'] 指定星期几执行（1=周一 ... 7=周日）
        - plan_type=3: 月计划，cycle_config['day_of_month'] 指定每月几号执行
        返回今日未超时的执行时间列表，格式：['2026-01-25 00:30:00', ...]
        """
        today = datetime.now()
        today_date = today.date()
        result = []

        for plan in plan_list:
            plan_type     = plan.get("plan_type")
            cycle_start   = plan.get("cycle_start_time")
            cycle_end     = plan.get("cycle_end_time")
            cycle_config  = plan.get("cycle_config") or {}
            if isinstance(cycle_config, str):
                try:
                    cycle_config = json.loads(cycle_config)
                except (json.JSONDecodeError, ValueError):
                    cycle_config = {}
            time_list     = cycle_config.get("time", [])
            data_dict = {"id": plan.get("id"), "task_id": plan.get("task_id"),"sync_time": plan.get("create_time"), 
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),}
            # 1. 判断今天是否在计划有效时间范围内
            if not (cycle_start and cycle_end):
                continue
            if not (cycle_start.date() <= today_date <= cycle_end.date()):
                continue

            # 2. 判断今天是否命中计划周期
            has_task_today = False
            if plan_type == 0:
                #单次执行
                execute_time = plan.get("execute_time")
                if execute_time:
                    if execute_time > today:
                        data_dict["start_time"] = execute_time.strftime("%Y-%m-%d %H:%M:%S")
                        data_dict["progress_generate"] = 2
                        result.append(data_dict.copy())
                    else:
                        continue
                else:
                    continue
            elif plan_type == 1:
                # 日计划：范围内每天都执行
                has_task_today = True
            elif plan_type == 2:
                # 周计划：isoweekday() 1=周一 2=周二 ... 7=周日
                weekdays = cycle_config.get("weekdays", [])
                has_task_today = str(today.isoweekday()) in weekdays
            elif plan_type == 3:
                # 月计划：判断今天是本月第几号
                day_of_month = cycle_config.get("day_of_month", [])
                has_task_today = str(today_date.day) in day_of_month
            elif plan_type == 4:
                #立刻执行
                execute_time = plan.get("execute_time")
                now_time = datetime.now()
                if execute_time:
                    diff = abs((execute_time - now_time).total_seconds())
                    if diff <= 600:
                        data_dict["progress_generate"] = 2
                        data_dict["start_time"] = now_time.strftime("%Y-%m-%d %H:%M:%S")
                        result.append(data_dict.copy())
                    else:
                        continue
           
            # 3. 筛选今日未超时的任务时间
            if has_task_today:
                is_last_day = (today_date == cycle_end.date())
                for t in time_list:
                    hour, minute, second = map(int, t.split(":"))
                    task_time = today.replace(hour=hour, minute=minute, second=second, microsecond=0)
                    if task_time > today:
                        data_dict["start_time"] = task_time.strftime("%Y-%m-%d %H:%M:%S")
                        data_dict["progress_generate"] = 2 if is_last_day else 1
                        result.append(data_dict.copy())
                    else:
                        continue
        return result

    def __add_task_plan_progress(self, plan_list: list):
        """
        添加任务计划进度,根据结果添加任务计划进度
        新增前统一清理旧的待执行进度（status=4, progress_status=0），
        防止计划更新或次日循环时产生重复/残留记录
        """
        del_flag, del_err = task_plan_db.delete_task_plan_progress_by_id(plan_list)
        if not del_flag:
            self.logger.error(f"新增前清理旧进度失败，错误信息: {del_err}")
        result_list = self.__parse_today_tasks(plan_list)
        if result_list:
            self.logger.info(f"比较之后待添加的任务计划列表: {result_list}")
            flag, add_result = task_plan_db.add_task_plan_progress(result_list)
            if not flag:
                self.logger.error(f"添加任务计划进度失败,错误信息: {add_result}")
            else:
                if add_result:
                    flag, update_err = task_plan_db.update_task_plan(add_result)
                    if not flag:
                        self.logger.error(f"更新任务计划状态失败,错误信息: {update_err}")
                    else:
                        self.logger.info(f"更新任务计划状态成功")
                        # update_task_plan 成功后这些计划的 progress_generate 已变为非 0，
                        updated_ids = {d.get("id") for d in add_result}
                        self.temp_plan_list = [p for p in self.temp_plan_list if p.get("id") not in updated_ids]
                        self.logger.info(f"已从临时列表移除已生成进度的计划: {updated_ids}")

    def main(self):
        running = True
        def signal_handler(signum, frame):
            nonlocal running
            self.logger.info(f"接收到信号: {signum}, 程序即将退出")
            running = False
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        flag = self.detect_task_plan()
        if flag:
            self.__add_task_plan_progress(self.temp_plan_list)
        while running:
            plan_list =self.compare_task_plan()
            if plan_list:
                self.__add_task_plan_progress(plan_list)
            schedule.run_pending()
            time.sleep(1)
            if not running:
                break
        


if __name__ == "__main__":
    task_plan = TaskPlan()
    task_plan.main()