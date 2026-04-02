#!/usr/bin/env python3
# coding=utf-8

import sys
import os,yaml
from datetime import datetime

from sqlalchemy import null

# 将 src 目录加入搜索路径，之后所有模块均可直接导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# ── 在 sys.path 设置完成后再导入业务模块 ──
from iot_sensor_exec.iot_sensor_wb_new import main
with open('data/configuration/iot_device.yaml', 'r', encoding='utf-8') as f:
    iot_device_config = yaml.safe_load(f)
device_type_id = iot_device_config['device_type_id']['wenzhen_id']
print(device_type_id)

if __name__ == "__main__":
    main()
    # config = WebSocketConfig()
    # print(config.uri)
    # client = IoTSensorClient(config)
    # # client.start()
    
    # try:
    #     client.start()
    # except KeyboardInterrupt:
    #     client.stop()
    #     client.logger.info("程序已退出")
    
