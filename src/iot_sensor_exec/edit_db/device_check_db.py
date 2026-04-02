import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from db_orm import iot_device_db

def get_device_message(device_name:list):
    """
    根据设备大类列表，获取设备大类、绑定大类设备、绑定子设备信息
    [{'id': 24, 'device_name': '温振监控主机01', 'device_type_id': 9, 'parent_device_id': None,
    'device_code': '8393423428', 'child_mes': [{'id': 25, 'device_name': '温振传感器（01）', 
    'device_type_id': 6, 'parent_device_id': 24, 'device_code': '4486186248'},
    {'id': 26, 'device_name': '温振传感器（02）', 'device_type_id': 6, 'parent_device_id': 24,
    'device_code': '4486186214','ip': None, 'port': None, 'username': None, 'password': None, 'parameter': {'group_id': 1}}, {'id': 27, 'device_name': '温振传感器（03）', 'device_type_id': 6,
    'parent_device_id': 24, 'device_code': '4275287637','ip': None, 'port': None, 'username': None, 'password': None, 'parameter': {'group_id': 2}}, {'id': 28, 'device_name': '温振传感器（04）',
    'device_type_id': 6, 'parent_device_id': 24, 'device_code': '5427837934','ip': None, 'port': None, 'username': None, 'password': None, 'parameter': {'group_id': 3}}, {'id': 29, 'device_name': '温振传感器（05）',
    'device_type_id': 6, 'parent_device_id': 24, 'device_code': '2788697344','ip': None, 'port': None, 'username': None, 'password': None, 'parameter': {'group_id': 4}}]}, {'id': 70, 'device_name': '温振监控主机02',
    'device_type_id': 9, 'parent_device_id': None, 'device_code': '2028701390980997120', 'ip': None, 'port': None, 'username': None, 'password': None, 'parameter': {'group_id': 3},
    'child_mes': [{'id': 71, 'device_name': '温振201', 'device_type_id': 6, 'parent_device_id': 70,
    'device_code': '2028701517615423488','ip': None, 'port': None, 'username': None, 'password': None, 'parameter': {'group_id': 1}}, {'id': 72, 'device_name': '温振202', 'device_type_id': 6, 'parent_device_id': 70,
    'device_code': '2028702801953251328','ip': None, 'port': None, 'username': None, 'password': None, 'parameter': {'group_id': 2}}, {'id': 73, 'device_name': '温振203', 'device_type_id': 6, 'parent_device_id': 70,
    'device_code': '2028702877853376512','ip': None, 'port': None, 'username': None, 'password': None, 'parameter': {'group_id': 3}}]}]
    """
    result_list = {}
    result_mes = []
    try:
        query =iot_device_db.session.query(iot_device_db.DeviceType.id, iot_device_db.DeviceType.type_name).filter(iot_device_db.DeviceType.type_name.in_(device_name)).all()
        if query: #设备大类存在
            for result in query:
                result_list[result[1]] = result[0]
            for key, value in result_list.items():
                parent_device_query =iot_device_db.session.query(iot_device_db.Device.id,iot_device_db.Device.device_name, iot_device_db.Device.device_type_id,
                iot_device_db.Device.parent_device_id,iot_device_db.Device.device_code)\
                .filter(iot_device_db.Device.device_type_id == value).all()
                if parent_device_query:#绑定大类设备存在
                    for result in parent_device_query:
                        parent_mes = result._asdict().copy()

                        attr_query =iot_device_db.session.query(iot_device_db.Attr.ip,iot_device_db.Attr.port,iot_device_db.Attr.username,
                        iot_device_db.Attr.password,iot_device_db.Attr.parameter,iot_device_db.Attr.online_status)\
                        .filter(iot_device_db.Attr.device_code == parent_mes["device_code"]).first()
                        if attr_query:
                            parent_mes["ip"] = attr_query.ip
                            parent_mes["port"] = attr_query.port
                            parent_mes["username"] = attr_query.username
                            parent_mes["password"] = attr_query.password
                            parent_mes["parameter"] = attr_query.parameter
                            parent_mes["online_status"] = attr_query.online_status
                        else:
                            parent_mes["ip"] = None
                            parent_mes["port"] = None
                            parent_mes["username"] = None
                            parent_mes["password"] = None
                            parent_mes["parameter"] = {"group_id": None}
                            parent_mes["online_status"] = 0

                        child_device_query =iot_device_db.session.query(iot_device_db.Device.id,iot_device_db.Device.device_name, iot_device_db.Device.device_type_id,
                        iot_device_db.Device.parent_device_id,iot_device_db.Device.device_code)\
                        .filter(iot_device_db.Device.parent_device_id == result[0]).all()
                        child_mes = []
                        if child_device_query:#绑定子设备存在
                            for child_result in child_device_query:
                                child_item = child_result._asdict().copy()
                                child_query =iot_device_db.session.query(iot_device_db.Attr.ip,iot_device_db.Attr.port,iot_device_db.Attr.username,
                                iot_device_db.Attr.password,iot_device_db.Attr.parameter,iot_device_db.Attr.online_status)\
                                .filter(iot_device_db.Attr.device_code == child_item["device_code"]).first()
                                if child_query:
                                    child_item["ip"] = child_query.ip
                                    child_item["port"] = child_query.port
                                    child_item["username"] = child_query.username
                                    child_item["password"] = child_query.password
                                    child_item["parameter"] = child_query.parameter
                                    child_item["online_status"] = child_query.online_status
                                else:
                                    child_item["ip"] = None
                                    child_item["port"] = None
                                    child_item["username"] = None
                                    child_item["password"] = None
                                    child_item["parameter"] = None
                                    child_item["online_status"] = 0
                                child_mes.append(child_item)
                            parent_mes["child_mes"] = child_mes
                        else:#绑定子设备不存在
                            parent_mes["child_mes"] = []
                        result_mes.append(parent_mes)
                else:#绑定设备不存在
                    pass
        else:#设备大类不存在
            pass
        return result_mes
    except Exception as e:
        iot_device_db.session.rollback()
        print(f"device_check_db.get_device_message 获取设备信息失败: {e}")
        return result_mes
    finally:
        iot_device_db.session.close()

if __name__ == "__main__":
    result_mes = get_device_message(["温振监控主机", "局放监控主机", "声纹传感器", "硬盘录像机"])
    print(result_mes)