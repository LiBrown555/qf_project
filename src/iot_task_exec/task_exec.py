#!/usr/bin/env python3
# coding=utf-8

import yaml,pymysql
import sys, time
import os, uuid, requests,json
import signal, subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from edit_db import task_exec_db
from sensor_driver import wenzhen_reader
from log_record.log_record import LogAndRecord

"""
v1.1新增设备分类参数用作筛选操作,过滤掉不满足条件的任务计划
"""

with open('data/configuration/iot_device.yaml', 'r', encoding='utf-8') as f:
    iot_device_config = yaml.safe_load(f)
device_type = iot_device_config['device_type']
device_type_id :list = [device_type[mes] for mes in device_type.keys() if mes]

with open('data/configuration/log_path.yaml', 'r', encoding='utf-8') as f:
    log_config = yaml.safe_load(f)
log_path = log_config['log']['task_exec']

class TaskExec:
    def __init__(self):
        self.log_init = LogAndRecord()
        result = self.log_init.log_init(log_path, "task_exec")
        if not result:
            raise Exception("日志初始化失败")
        self.logger = self.log_init.logger

        self.device_config = {}
        self.task_list = []
        self.image_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mes_data","image"))
        self.logger.info(f"任务执行程序已经初始化完成,开始执行任务")
    
    def _get_device_config(self):
        """
            根据设备类别获取对应设备配置
            返回信息格式为
            {'24': {'id': 24, 'ip': '192.168.10.201', 'port': 1350, 'username': None, 'password': None, 'parameter': None}, 
            '25': {'id': 25, 'ip': None, 'port': None, 'username': None, 'password': None, 'parameter': {'group_id': 1}}, 
            '26': {'id': 26, 'ip': None, 'port': None, 'username': None, 'password': None, 'parameter': {'group_id': 2}}, }
        """
        flag ,mes = task_exec_db.get_device_config(device_type_id)
        if flag :
            self.device_config = mes
            return True
        else:
            self.logger.error(f"获取设备配置失败,错误信息: {mes}")
            return False
    def _end_timeout_task(self):
        """
        结束超时任务
        """
        flag, result = task_exec_db.end_timeout_task()
        if flag:
            return True
        else:
            self.logger.error(f"结束超时任务失败,错误信息: {result}")
    def _get_task_plan(self):
        """
        获取任务计划
        """
        if device_type_id:
            flag, task_list = task_exec_db.get_task_plan(device_type_id)
            if flag:
                if task_list:
                    self.task_list = task_list.copy()
                    self.logger.info(f"任务计划: {self.task_list}")
                    return True
                else:
                    return False
            else:
                self.logger.error(f"获取任务计划失败,错误信息: {task_list}")
                return False
        else:
            self.logger.error(f"没有设备类型,所以不执行任务计划")
            return False
    
    def _task_exec(self, task_list: list):
        """
        执行任务
        host_type == 13 :温振传感器主机
        host_type == 2  :摄像头抓拍任务
        新增任务类型只需在 TASK_REGISTRY 中添加一条记录：
            host_type: (执行函数, exclusive_key)
            exclusive_key=None  表示不限制并发
            exclusive_key=字符串 表示同时只能运行一个该 key 的任务
        """
        # ── 任务注册表（新增类型只改这里）─────────────────────────
        TASK_REGISTRY = {
            13: (self._wenzhen_sensor_host_task, "wenzhen"),
            2:  (self._capture_task,             None),
        }

        jobs = []
        for task in task_list:
            flag, result = task_exec_db.get_task_action(int(task["task_id"]))
            if not flag:
                self.logger.error(f"获取任务动作失败,错误信息: {result}")
                continue
            if not result:
                self.logger.info(f"任务 {task['task_id']} 无动作,跳过")
                continue
            host_type, host_result = task_exec_db.get_device_host_type(int(task["device_id"]))
            if host_type == -1:
                self.logger.error(f"获取设备主机类型失败,错误信息: {host_result}")
                continue
            if host_type not in TASK_REGISTRY:
                self.logger.error(f"未注册的任务类型 host_type={host_type},跳过执行: {task}")
                continue
            fn, ex_key = TASK_REGISTRY[host_type]
            jobs.append((fn, task, result, ex_key))

        if not jobs:
            return

        pending  = list(jobs)
        running  = set()
        future_to_key = {}  
        locked_keys   = set()  

        with ThreadPoolExecutor(max_workers=20) as ex:
            while pending or running:
                next_pending = []
                for fn, task, result, ex_key in pending:
                    if ex_key is not None and ex_key in locked_keys:
                        next_pending.append((fn, task, result, ex_key))
                        continue
                    fut = ex.submit(fn, task, result, self.device_config)
                    running.add(fut)
                    future_to_key[fut] = ex_key
                    if ex_key is not None:
                        locked_keys.add(ex_key)
                pending = next_pending

                if not running:
                    break

                # 等待任意一个任务完成
                done, _ = wait(running, return_when=FIRST_COMPLETED)
                for fut in done:
                    running.remove(fut)
                    ex_key = future_to_key.pop(fut, None)
                    if ex_key is not None:
                        locked_keys.discard(ex_key)  # 释放互斥锁
                    try:
                        fut.result()
                    except Exception as e:
                        self.logger.error(f"任务执行失败: {e}")
    
    def _capture_task(self, task: dict, action_list: list, task_config: dict)->dict:
        """
        执行摄像头抓拍任务
        task: 任务计划
        action_list: 任务对应的动作列表
        task_config: 任务配置
        """
        task_exec_db.update_task_progress(int(task["id"]), 0)#更新任务进度为进行中
        save_mes_list = []
        update_result = {}

        for action in action_list:
            update_result[action["device_id"]] = {"online_status": 0}
            ip = task_config[str(int(action["device_id"]))].get("ip")
            port = task_config[str(int(action["device_id"]))].get("port")
            username = task_config[str(int(action["device_id"]))].get("username")
            password = task_config[str(int(action["device_id"]))].get("password")
            if not all([ip, port, username, password]):
                self.logger.error(f"_capture_task设备连接参数不完整: {task_config[str(int(action['device_id']))]}")
                save_mes_list.append({
                    "task_plan_id": task["task_plan_id"],
                    "task_action_id": action["id"],
                    "task_progress_id": task["id"],
                    "device_id": action["device_id"],
                    "file_path":  None,
                    "item_values": None,
                    "parameters": None,
                    "error_info": "设备连接参数不完整",
                    "post_status": 0,
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                continue
            os.makedirs(os.path.join(self.image_path, datetime.now().strftime("%Y_%m_%d")), exist_ok=True)
            img_filename =f"{action['device_id']}_{uuid.uuid4()}_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.jpg"
            img_path = os.path.join(self.image_path, datetime.now().strftime("%Y_%m_%d"), img_filename)
            SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sensor_driver", "capture_single.py")
            try:
                result = subprocess.run(
                    [
                        sys.executable,  # 使用当前 Python 解释器
                        str(SCRIPT_PATH),
                        ip,
                        username,
                        password,
                        str(port),
                        "1",  # channel
                        img_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=20  # 总共最多 20 秒
                )
                if result.returncode == 0:
                    success = True
                    error_msg = None
                else:
                    success = False
                    error_msg = f"Subprocess failed (code={result.returncode}): {result.stderr}"
            except subprocess.TimeoutExpired as e:
                error_msg = f"Timeout: {e}"
                self.logger.error(f"摄像头抓拍任务超时,错误信息:{error_msg}")
                success = False
            except Exception as e:
                error_msg = f"Error: {e}"
                self.logger.error(f"摄像头抓拍任务失败,错误信息:{error_msg}")
                success = False
            finally:
                save_mes = {
                    "task_plan_id": task["task_plan_id"],
                    "task_action_id": action["id"],
                    "task_progress_id": task["id"],
                    "device_id": action["device_id"],
                    "file_path": img_path if success else None,
                    "item_values": None,
                    "parameters": None,
                    "error_info": error_msg if not success else None,
                    "post_status": 0,
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                update_result[action["device_id"]] = {"online_status": 1 if success else 0}
                save_mes_list.append(save_mes)
                self.logger.info(f"保存任务结果: {save_mes}")
        update_result_list = []
        for device_id, result in update_result.items():#拼接状态信息
            update_result_list.append(
                {
                    "id": self.device_config[str(device_id)].get("id"),
                    "online_status": result["online_status"],
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        flag, result = task_exec_db.save_task_result(save_mes_list)
        if not flag:
            self.logger.error(f"保存任务结果失败,错误信息: {result}")
            task_exec_db.update_task_progress(int(task["id"]), 2)
            flag, result = task_exec_db.update_device_online(update_result_list)
            if not flag:
                self.logger.error(f"更新设备在线状态失败,错误信息: {result}")
            return False
        else:
            task_exec_db.update_task_progress(int(task["id"]), 1)
            flag, result = task_exec_db.update_device_online(update_result_list)
            if not flag:
                self.logger.error(f"更新设备在线状态失败,错误信息: {result}")
            return True
    def _wenzhen_sensor_host_task(self, task: dict, action_list: list, task_config: dict)->bool:
        """
        执行温振传感器主机任务
        task: 任务计划
        action: 任务对应的动作
        task_config: 任务配置
        """
        task_exec_db.update_task_progress(int(task["id"]), 0)#更新任务进度为进行中
        host_type, host_result = task_exec_db.get_device_host_type(int(task["device_id"]))
        group_id_list = []
        save_mes_list = []
        save_mes_data = []
        save_mes_params = {}
        update_result = {}
        if host_type != -1:
            if host_type == 13: #执行温振传感器主机任务
                host_config: dict = self.device_config[str(host_result)]
                ip = host_config.get("ip")
                port = host_config.get("port")
            else:
                self.logger.error(f"_wenzhen_sensor_host_task_温振传感器主机类型错误: {host_type}")
                task_exec_db.update_task_progress(int(task["id"]), 2)
                return False
        else:
            self.logger.error(f"_wenzhen_sensor_host_task_获取温振传感器主机类型失败: {host_result}")
            task_exec_db.update_task_progress(int(task["id"]), 2)
            return False
        for action in action_list:
            #判断为None
            group_id=task_config[str(int(action["device_id"]))]["parameter"].get("group_id")
            save_mes_data.append({
                "task_action_id": action["id"],
                "device_id": action["device_id"],
                "group_id": int(group_id) if group_id else None,#可能存入信息为None
                "item_values": None,
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            if group_id: # group_id 存在, 
                group_id_list.append(int(group_id))
            update_result[action["device_id"]] = {"signal": 0, "battery_percentage": 0, "online_status": 0}
        try:
            recv_data = {}
            data = wenzhen_reader.get_gateway_data(ip,port,group_id_list)
            sensors = data.get("sensors", {})
            # 交互模式下，仍然使用原来的单传感器展现形式
            if not sensors:
                for group_id in group_id_list:
                    save_mes_params[group_id] = {
                        "error": "指定的传感器无数据",
                        "item_values": None,
                        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "recv_status": False,
                    }
            else:
                for sid, payload in sensors.items():
                    recv_data = {
                    "sensor_id": int(sid),
                    "status": payload.get("status"),
                    "temp": payload.get("temperature", {}).get("value") or 0.0,
                    "vib_amp_x": payload.get("x_axis", {}).get("value") or 0.0,
                    "vib_amp_y": payload.get("y_axis", {}).get("value") or 0.0,
                    "vib_amp_z": payload.get("z_axis", {}).get("value") or 0.0,
                    "battery": payload.get("battery") or 0,
                    "signal": payload.get("signal"),
                    }
                    save_mes_params[int(sid)] = {    # int(sid)：统一为 int，与 group_id 类型一致
                        "error": None,
                        "item_values": recv_data,
                        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "recv_status": True,
                    }
        except TimeoutError as e:
            self.logger.error(f"温振传感器主机任务连接超时,错误信息: {str(e)}")
            for group_id in group_id_list:
                save_mes_params[group_id] = {
                    "error": "连接超时",
                    "item_values": None,
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "recv_status": False,
                }
        except OSError as e:
            self.logger.error(f"温振传感器主机监听或接受网关连接失败: {e}")
            for group_id in group_id_list:
                save_mes_params[group_id] = {
                    "error": "监听或接受网关连接失败",
                    "item_values": None,
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "recv_status": False,
                }
        except Exception as e:
            self.logger.error(f"温振传感器主机执行温振传感器主机任务失败: {e}")
            for group_id in group_id_list:
                save_mes_params[group_id] = {
                    "error": "执行温振传感器主机任务失败",
                    "item_values": None,
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "recv_status": False,
                }
        finally:
            for save_mes in save_mes_data:
                if save_mes["group_id"]:#不为None
                    mes = save_mes_params[save_mes["group_id"]]
                    if mes["recv_status"]:#为True
                        update_result[save_mes["device_id"]] = {"signal": mes["item_values"]["signal"], "battery_percentage": mes["item_values"]["battery"], "online_status": 1}
                        flag , item_definition_list = task_exec_db.get_item_definition(save_mes["device_id"])
                        if flag:#获取设备定义成功
                            if item_definition_list:#设备定义列表不为空
                                item_values = {}
                                for item_definition in item_definition_list:
                                    item_values[item_definition["item_code"]] = mes["item_values"][item_definition["item_code"]]
                                save_mes["item_values"] = item_values
                                save_mes["create_time"] = mes["create_time"]
                            else:
                                save_mes["error_info"] = "设备定义列表为空"
                                save_mes["create_time"] = mes["create_time"]
                        else:
                            save_mes["error_info"] = "获取设备定义失败"
                            save_mes["create_time"] = mes["create_time"]
                    else:
                        save_mes["error_info"] = mes["error"]
                        save_mes["create_time"] = mes["create_time"]
                else:
                    save_mes["error_info"] = "传感器无数据无group_id"
                self.logger.info(f"保存任务结果: {save_mes}")
                save_mes_list.append({
                "task_plan_id": task["task_plan_id"],
                "task_action_id": save_mes["task_action_id"],
                "task_progress_id": task["id"],
                "device_id": save_mes["device_id"],
                "file_path": None,
                "item_values": save_mes["item_values"],
                "parameters": None,
                "error_info": mes.get("error_info", None),
                "post_status": 0,
                "create_time": save_mes["create_time"],
                })
                update_result_list = []
            for device_id, result in update_result.items():#拼接状态信息
                parameter = self.device_config[str(device_id)].get("parameter")
                parameter["signal"] = result["signal"]
                parameter["battery_percentage"] = result["battery_percentage"]
                update_result_list.append(
                    {
                        "id": self.device_config[str(device_id)].get("id"),
                        "online_status": result["online_status"],
                        "parameter": parameter,
                        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
            if update_result_list:
                update_result_list.append({
                    "id": host_config.get("id"),
                    "online_status": 1,
                    "parameter": host_config.get("parameter"),
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
            else:
                update_result_list.append({
                    "id": host_config.get("id"),
                    "online_status": 0,
                    "parameter": host_config.get("parameter"),
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
            flag, result = task_exec_db.save_task_result(save_mes_list)
            if not flag:
                self.logger.error(f"保存任务结果失败,错误信息: {result}")
                task_exec_db.update_task_progress(int(task["id"]), 2)
                flag, result = task_exec_db.update_device_online(update_result_list)
                if not flag:
                    self.logger.error(f"更新设备在线状态失败,错误信息: {result}")
                return False
            else:
                task_exec_db.update_task_progress(int(task["id"]), 1)
                flag, result = task_exec_db.update_device_online(update_result_list)
                if not flag:
                    self.logger.error(f"更新设备在线状态失败,错误信息: {result}")
                return True

    def _save_task_result(self, task: dict, action: dict,save_result: dict):
        try:
            save_mes = {}
            save_list = []
            save_mes["task_id"] =2
            save_mes["task_plan_id"] = 2
            conn = pymysql.connect(host="120.26.22.61", port=15698, user="root", password="123456", database="udmp",charset="utf8mb4",cursorclass=pymysql.cursors.DictCursor)
            query_sql = "SELECT id FROM task_progress WHERE progress_uuid = %s"
            with conn.cursor() as cur:
                cur.execute(query_sql, (task["progress_uuid"],))
                result = cur.fetchone()
                if result:
                    save_mes["task_progress_id"] = result["id"]
                else:
                    self.logger.error(f"任务进度查询失败,错误信息: {result}")
                    return False
            save_mes["task_point_action_id"] = action["id"]
            save_mes["device_id"] = action["device_id"]
            save_mes["device_point_id"] = None
            save_mes["algorithm_ability_id"] = 5
            save_mes["detect_status"] = 0
            save_mes["device_ability_id"] = 3
            save_mes["file_path"] = None
            save_mes["detect_file_path"] = None
            save_mes["result_status"] = 0
            save_mes["create_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_mes["is_delete"] = 0
            item_values = save_result["item_values"]
            if item_values:
                save_mes["inspection_item_id"] = 7
                save_mes["inspection_item_value"] = item_values["temp"]
                save_list.append(save_mes.copy())
                save_mes["inspection_item_id"] = 8
                save_mes["inspection_item_value"] = item_values["vib_amp_x"]
                save_list.append(save_mes.copy())
                save_mes["inspection_item_id"] = 9
                save_mes["inspection_item_value"] = item_values["vib_amp_y"]
                save_list.append(save_mes.copy())
                save_mes["inspection_item_id"] = 10
                save_mes["inspection_item_value"] = item_values["vib_amp_z"]
                save_list.append(save_mes.copy())
            if save_list:
                with conn.cursor() as cur:
                    save_sql = ("INSERT INTO task_result (task_id, task_plan_id, task_progress_id, task_point_action_id,"
                                "device_id, device_point_id, algorithm_ability_id, detect_status, detect_file_path, result_status,"
                                "create_time, is_delete, inspection_item_id, inspection_item_value) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
                    data = [(r["task_id"], r["task_plan_id"], r["task_progress_id"], r["task_point_action_id"],
                    r["device_id"], r["device_point_id"], r["algorithm_ability_id"], r["detect_status"], 
                    r["detect_file_path"], r["result_status"], r["create_time"], r["is_delete"],
                    r["inspection_item_id"], r["inspection_item_value"]) for r in save_list]
                    cur.executemany(save_sql, data)
                    conn.commit()
            else:
                self.logger.error(f"保存任务结果失败,错误信息: {save_list}")
                return False
        except Exception as e:
            self.logger.error(f"保存任务结果失败,错误信息: {e}")
            return False
        finally:
            conn.close()


    def main(self):
        """
        主函数
        """
        running = True
        def signal_handler(signum, frame):
            nonlocal running
            self.logger.info(f"接收到信号: {signum}, 程序即将退出")
            running = False
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        while running:
            self._end_timeout_task()#启动时将所有超时任务状态更改为异常
            flag = self._get_task_plan()#获取任务计划
            if flag: #查询到任务计划
                if self._get_device_config(): #获取设备配置成功
                    self._task_exec(self.task_list)#执行任务
                else:
                    pass
            else:
                pass
            if not running:
                break
            time.sleep(2)


if __name__ == "__main__":
    task_exec = TaskExec()
    task_exec.main()