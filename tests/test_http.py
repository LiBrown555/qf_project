#!/usr/bin/env python3
# coding=utf-8
import uuid,json,requests
from datetime import datetime

sensor_url = "http://192.168.1.173:18083/upload/iotPushSensorData"
camera_url = "http://192.168.1.173:18083/upload/iotPushCaptureData"

post_mes_list = []
post_mes_list.append({
    "url": sensor_url,
    "file_parameter": None,
    "post_message": {
        "func_value": "iot_push_sensor_data",
        "device_code": "5432783787",
        "message_id": str(uuid.uuid4()),
        "error_info": None,
        "data": json.dumps({
            "task_progress_uuid": "43ed1933-c371-4186-afcf-bc57d124e842",
            "task_action_id": 203,
            "task_action_params": [{"item": 7, "value": 79}],
            "file_parameter": None,
            "capture_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, ensure_ascii=False)
    }
})
post_mes_list.append({
    "url": camera_url,
    "file_parameter": None,
    "post_message": {
        "func_value": "iot_push_capture_data",
        "device_code": "5432783787",
        "message_id": str(uuid.uuid4()),
        "error_info": None,
        "data": json.dumps({
            "task_progress_uuid": "43ed1933-c371-4186-afcf-bc57d124e842",
            "task_action_id": 203,
            "task_action_param": {"item": 6},
            "file_parameter": None,
            "capture_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, ensure_ascii=False)
    }
})
if post_mes_list:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    for post_mes in post_mes_list:
        url = post_mes.get("url")
        post_message = post_mes.get("post_message")
        file_path = post_mes.get("file_parameter")
        # post_message = json.dumps(post_message, ensure_ascii=False).encode('utf-8')
        if file_path:
            with open(file_path, "rb") as file:
                response = requests.post(url, data=post_message, files={"file": file})
                if response.status_code == 200:
                    print(f"推送任务结果成功: {response.json()}")
                else:
                    print(f"推送任务结果失败,推送数据:{post_message}")
        else:
            response = requests.post(url, data=post_message)
            if response.status_code == 200:
                print(f"推送任务结果成功: {response.json()}")
            else:
                print(f"推送任务结果失败,推送数据:{post_message}")