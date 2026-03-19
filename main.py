#!/usr/bin/env python3
# coding=utf-8

import sys
import os,yaml
from datetime import datetime

from sqlalchemy import null

# 将 src 目录加入搜索路径，之后所有模块均可直接导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# ── 在 sys.path 设置完成后再导入业务模块 ──
from iot_sensor_exec.iot_sensor_wb import IoTSensorClient, WebSocketConfig

with open('data/configuration/sql_db.yaml', 'r', encoding='utf-8') as f:
    db_config = yaml.safe_load(f)

db_username = db_config['db']['username']
db_passwd = db_config['db']['passwd']
db_ip = db_config['db']['ip']
db_port = db_config['db']['port']
db_name = db_config['db']['uav_name']
print(db_config)


if __name__ == "__main__":
    # config = WebSocketConfig()
    # print(config.uri)
    # client = IoTSensorClient(config)
    # client.start()
    print(datetime.now().date())
    
    # try:
    #     client.start()
    # except KeyboardInterrupt:
    #     client.stop()
    #     client.logger.info("程序已退出")
    # a = null
    # if a:
    #     print(1)
    # else:
    #     print(2)
