#!/usr/bin/env python3
# coding=utf-8

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from db_orm import iot_data_db, iot_device_db, iot_task_db

# 测试数据库连接
class TestDB:

    def test_iot_data_db(self):
        result_list =iot_data_db.session.query(iot_data_db.ItemDefinition).limit(5).all()
        print("-------------------------ItemDefinition-------------------------")
        for result in result_list:
            print(result.to_dict())
        print("----------------------------------------------------------------")
        iot_data_db.session.close()
    
    def test_iot_device_db(self):
        result_list =iot_device_db.session.query(iot_device_db.Device).limit(5).all()
        print("-------------------------Device-------------------------")
        for result in result_list:
            print(result.to_dict())
        result_list =iot_device_db.session.query(iot_device_db.DeviceType).limit(5).all()
        print("-------------------------DeviceType-------------------------")
        for result in result_list:
            print(result.to_dict())
        result_list =iot_device_db.session.query(iot_device_db.AbilityDef).limit(5).all()
        print("-------------------------AbilityDef-------------------------")
        for result in result_list:
            print(result.to_dict())
        result_list =iot_device_db.session.query(iot_device_db.Attr).limit(5).all()
        print("-------------------------Attr-------------------------")
        for result in result_list:
            print(result.to_dict())
        result_list =iot_device_db.session.query(iot_device_db.TypeAbility).limit(5).all()
        print("-------------------------TypeAbility-------------------------")
        for result in result_list:
            print(result.to_dict())
        result_list =iot_device_db.session.query(iot_device_db.Preset).limit(5).all()
        print("-------------------------Preset-------------------------")
        for result in result_list:
            print(result.to_dict())
        print("----------------------------------------------------------------")
        iot_device_db.session.close()

    def test_iot_task_db(self):
        result_list =iot_task_db.session.query(iot_task_db.Task).limit(5).all()
        print("-------------------------Task-------------------------")
        for result in result_list:
            print(result.to_dict())
        result_list =iot_task_db.session.query(iot_task_db.Action).limit(5).all()
        print("-------------------------Action-------------------------")
        for result in result_list:
            print(result.to_dict())
        print("----------------------------------------------------------------")
        result_list =iot_task_db.session.query(iot_task_db.Result).limit(5).all()
        print("-------------------------Result-------------------------")
        for result in result_list:
            print(result.to_dict())
        result_list =iot_task_db.session.query(iot_task_db.Plan).limit(5).all()
        print("-------------------------Plan-------------------------")
        for result in result_list:
            print(result.to_dict())
        result_list =iot_task_db.session.query(iot_task_db.Progress).limit(5).all()
        print("-------------------------Progress-------------------------")
        for result in result_list:
            print(result.to_dict())
        print("----------------------------------------------------------------")
        iot_task_db.session.close()

if __name__ == "__main__":
    test_db = TestDB()
    test_db.test_iot_data_db()
    test_db.test_iot_device_db()
    test_db.test_iot_task_db()
    
