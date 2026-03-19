#!/usr/bin/env python3
"""
tcp_server_lora_gateway_encapsulated.py
封装版本：将获取数据和导出Excel表格功能模块化封装
"""

import socket
import struct
import json
import time
import threading
from datetime import datetime
import pandas as pd
import os

# 这里的 LISTEN_IP / LISTEN_PORT 仅作为交互模式(main)的默认值。
# 实际业务中，将通过 task_progress.py 动态计算网关绑定的 IP 和端口，
# 并在调用 get_gateway_data(listen_ip, listen_port, group_ids=...) 时传入。
LISTEN_IP = '0.0.0.0'
LISTEN_PORT = 1350
SLAVE_ID = 0x01

# 配置参数
DEBUG = False  # 关闭调试输出
READ_INTERVAL = 5  # 1小时读取一次
GENERATE_EXCEL = False  # 交互查询模式下不生成Excel
QUIET_MODE = True  # 安静模式，减少控制台输出

class ModbusRTUReader:
    """Modbus RTU协议读取器"""
    
    @staticmethod
    def computeCRC(data: bytes) -> int:
        """计算Modbus CRC16校验码"""
        crc = 0xFFFF
        for b in data:
            crc ^= b
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    @staticmethod
    def build_rtu_frame(slave, function_code, addr, count):
        """构建Modbus RTU请求帧"""
        buf = struct.pack('>BBHH', slave, function_code, addr, count)
        crc = ModbusRTUReader.computeCRC(buf)
        return buf + struct.pack('<H', crc)

    @staticmethod
    def parse_rtu_frame(resp):
        """解析Modbus RTU响应帧"""
        if DEBUG:
            print(f'<<< 原始响应 ({len(resp)}字节): {resp.hex(" ")}')
        
        if len(resp) < 5:
            raise ValueError(f'响应帧太短: {len(resp)}字节')
        
        # 检查CRC
        received_crc = struct.unpack('<H', resp[-2:])[0]
        computed_crc = ModbusRTUReader.computeCRC(resp[:-2])
        if received_crc != computed_crc:
            raise ValueError(f'CRC校验失败 接收:{received_crc:04X} 计算:{computed_crc:04X}')
        
        slave_id = resp[0]
        function_code = resp[1]
        
        if function_code == 0x03:  # 读保持寄存器
            byte_count = resp[2]
            data_bytes = resp[3:3+byte_count]
            
            if byte_count % 2 != 0:
                raise ValueError(f'数据字节数不是偶数: {byte_count}')
            
            register_count = byte_count // 2
            registers = list(struct.unpack('>' + 'H' * register_count, data_bytes))
            return registers
        
        elif function_code == 0x83:  # 异常响应
            error_code = resp[2]
            error_messages = {
                0x01: "非法功能码",
                0x02: "非法数据地址", 
                0x03: "非法数据值",
                0x04: "从站设备故障"
            }
            raise ValueError(f"Modbus异常: {error_messages.get(error_code, f'未知错误码{error_code:02X}')}")
        
        else:
            raise ValueError(f'不支持的功能码: {function_code:02X}')

    @staticmethod
    def read_registers(sock, slave, start_addr, count):
        """读取多个寄存器"""
        if count > 125:
            raise ValueError(f'一次读取寄存器数量不能超过125, 请求: {count}')
        
        frame = ModbusRTUReader.build_rtu_frame(slave, 0x03, start_addr, count)
        
        if DEBUG:
            print(f'>>> 发送请求: 地址={start_addr}, 数量={count}')
            print(f'>>> 原始请求: {frame.hex(" ")}')
        
        sock.sendall(frame)
        time.sleep(0.2)
        
        # 计算预期响应长度
        expected_byte_count = count * 2
        expected_frame_len = 5 + expected_byte_count
        
        # 尝试读取响应
        resp = b''
        start_time = time.time()
        while len(resp) < expected_frame_len and (time.time() - start_time) < 3.0:
            chunk = sock.recv(256)
            if chunk:
                resp += chunk
            else:
                time.sleep(0.1)
        
        if not resp:
            raise ValueError("未收到响应")
        
        return ModbusRTUReader.parse_rtu_frame(resp)

class SensorDataProcessor:
    """传感器数据处理类"""
    
    @staticmethod
    def decode_float(high_reg, low_reg):
        """将两个16位寄存器解码为32位浮点数"""
        data_bytes = struct.pack('>HH', high_reg, low_reg)
        return struct.unpack('>f', data_bytes)[0]

    @staticmethod
    def get_sensor_info(device_num):
        """根据设备编号获取传感器信息和数据类型"""
        # 计算传感器编号 (每4个设备组成一个温振传感器)
        sensor_num = (device_num - 1) // 4 + 1
        # 计算在传感器内的通道位置 (0:温度, 1:X轴, 2:Y轴, 3:Z轴)
        channel_in_sensor = (device_num - 1) % 4
        
        if channel_in_sensor == 0:
            data_type = "温度"
            unit = "°C"
            correction_factor = 10.0  # 温度数据除以10
        elif channel_in_sensor == 1:
            data_type = "X轴振动"
            unit = "m/s²"
            correction_factor = 10.0   # 振动数据保持原值
        elif channel_in_sensor == 2:
            data_type = "Y轴振动"
            unit = "m/s²"
            correction_factor = 10.0
        elif channel_in_sensor == 3:
            data_type = "Z轴振动"
            unit = "m/s²"
            correction_factor = 10.0
        else:
            data_type = "未知"
            unit = ""
            correction_factor = 10.0
        
        return sensor_num, channel_in_sensor, data_type, unit, correction_factor

class SensorDataReader:
    """传感器数据读取器"""
    
    def __init__(self, slave_id=SLAVE_ID, total_devices=64):
        self.slave_id = slave_id
        self.total_devices = total_devices
    
    def batch_read_battery_signal(self, sock):
        """批量读取所有设备的电量和信号强度"""
        battery_data = {}
        signal_data = {}
        
        if not QUIET_MODE:
            print("正在批量读取电量和信号强度...")
        
        # 批量读取电量 (寄存器800-863)
        try:
            battery_regs = ModbusRTUReader.read_registers(sock, self.slave_id, 800, self.total_devices)
            for i in range(self.total_devices):
                if i < len(battery_regs):
                    battery_value = battery_regs[i]
                    if 0 <= battery_value <= 100:  # 有效范围
                        battery_data[i+1] = battery_value
                        if DEBUG:
                            print(f"设备{i+1}电量: {battery_value}%")
        except Exception as e:
            if not QUIET_MODE:
                print(f"批量读取电量失败: {e}")
        
        # 批量读取信号强度 (寄存器1200-1263)
        try:
            signal_regs = ModbusRTUReader.read_registers(sock, self.slave_id, 1200, self.total_devices)
            for i in range(self.total_devices):
                if i < len(signal_regs):
                    signal_value = signal_regs[i]
                    if 0 <= signal_value <= 199:  # 有效范围
                        signal_data[i+1] = signal_value
                        if DEBUG:
                            print(f"设备{i+1}信号强度: {signal_value}")
        except Exception as e:
            if not QUIET_MODE:
                print(f"批量读取信号强度失败: {e}")
        
        return battery_data, signal_data

    def batch_read_realtime_data(self, sock):
        """批量读取所有设备的实时数据"""
        realtime_data = {}
        
        if not QUIET_MODE:
            print("正在批量读取实时数据...")
        
        # 批量读取实时数据 (寄存器0-127，每个设备2个寄存器)
        try:
            # 分两次读取，每次64个寄存器（32个设备）
            realtime_regs_part1 = ModbusRTUReader.read_registers(sock, self.slave_id, 0, 64)  # 设备1-32
            realtime_regs_part2 = ModbusRTUReader.read_registers(sock, self.slave_id, 64, 64)  # 设备33-64
            
            realtime_regs = realtime_regs_part1 + realtime_regs_part2
            
            for device_num in range(1, self.total_devices + 1):
                idx = (device_num - 1) * 2
                if idx + 1 < len(realtime_regs):
                    high_reg = realtime_regs[idx]
                    low_reg = realtime_regs[idx + 1]
                    
                    raw_value = SensorDataProcessor.decode_float(high_reg, low_reg)
                    realtime_data[device_num] = raw_value
                    
                    if DEBUG and device_num <= 8:  # 只显示前8个设备调试信息
                        sensor_num, _, data_type, unit, correction_factor = SensorDataProcessor.get_sensor_info(device_num)
                        corrected_value = raw_value / correction_factor
                        print(f"设备{device_num}(传感器{sensor_num} {data_type}): 原始值={raw_value}, 修正值={corrected_value}{unit}")
        
        except Exception as e:
            if not QUIET_MODE:
                print(f"批量读取实时数据失败: {e}")
        
        return realtime_data

    def read_all_sensor_data(self, sock):
        """读取所有传感器数据（优化版本：批量读取）"""
        if not QUIET_MODE:
            print("\n=== 开始批量读取所有传感器数据 ===")
        
        # 第一步：批量读取电量和信号强度
        battery_data, signal_data = self.batch_read_battery_signal(sock)
        
        # 第二步：批量读取实时数据
        realtime_data = self.batch_read_realtime_data(sock)
        
        # 第三步：整合数据
        all_sensors = {}
        
        for device_num in range(1, self.total_devices + 1):
            sensor_num, channel_in_sensor, data_type, unit, correction_factor = SensorDataProcessor.get_sensor_info(device_num)
            
            # 初始化传感器数据结构
            if sensor_num not in all_sensors:
                all_sensors[sensor_num] = {
                    'sensor_num': sensor_num,
                    'temperature': {'value': None, 'raw': None, 'device_num': None},
                    'x_axis': {'value': None, 'raw': None, 'device_num': None},
                    'y_axis': {'value': None, 'raw': None, 'device_num': None},
                    'z_axis': {'value': None, 'raw': None, 'device_num': None},
                    # 所有通道设备中“最差”的电量/信号（向下取最小值，保持原有逻辑）
                    'battery': battery_data.get(device_num),
                    'signal': signal_data.get(device_num),
                    # 新增：记录该传感器下每个设备的电量、信号，方便后续按传感器ID精确查询
                    'device_batteries': {},   # {device_num: battery}
                    'device_signals': {},     # {device_num: signal}
                    'status': '不完整'
                }
            
            # 填充传感器数据
            sensor = all_sensors[sensor_num]
            if device_num in realtime_data:
                raw_value = realtime_data[device_num]
                corrected_value = raw_value / correction_factor
                
                if data_type == "温度":
                    sensor['temperature'] = {'value': corrected_value, 'raw': raw_value, 'device_num': device_num}
                elif data_type == "X轴振动":
                    sensor['x_axis'] = {'value': corrected_value, 'raw': raw_value, 'device_num': device_num}
                elif data_type == "Y轴振动":
                    sensor['y_axis'] = {'value': corrected_value, 'raw': raw_value, 'device_num': device_num}
                elif data_type == "Z轴振动":
                    sensor['z_axis'] = {'value': corrected_value, 'raw': raw_value, 'device_num': device_num}
            
            # 更新电量和信号（使用最低值）
            current_battery = battery_data.get(device_num)
            current_signal = signal_data.get(device_num)
            
            if current_battery is not None:
                # 记录该设备的电量
                all_sensors[sensor_num]['device_batteries'][device_num] = current_battery
                if sensor['battery'] is None or current_battery < sensor['battery']:
                    sensor['battery'] = current_battery
            
            if current_signal is not None:
                # 记录该设备的信号
                all_sensors[sensor_num]['device_signals'][device_num] = current_signal
                if sensor['signal'] is None or current_signal < sensor['signal']:
                    sensor['signal'] = current_signal
        
        # 检查传感器状态
        for sensor_num, sensor in all_sensors.items():
            has_all_data = (sensor['temperature']['value'] is not None and 
                           sensor['x_axis']['value'] is not None and 
                           sensor['y_axis']['value'] is not None and 
                           sensor['z_axis']['value'] is not None)
            sensor['status'] = '完整' if has_all_data else '不完整'
        
        return all_sensors


class DataDisplay:
    """数据显示类"""
    
    def __init__(self, quiet_mode=QUIET_MODE):
        self.quiet_mode = quiet_mode
    
    def display_sensor_data(self, sensor_data):
        """显示传感器数据"""
        if self.quiet_mode:
            return
            
        for sensor_num in sorted(sensor_data.keys()):
            sensor = sensor_data[sensor_num]
            first_device_num = (sensor_num - 1) * 4 + 1  # 每4个设备组成一个传感器，取第1个设备的电量/信号
            device_batteries = sensor.get('device_batteries', {})
            device_signals = sensor.get('device_signals', {})
            
            output = {
                "sensor_id": sensor_num,
                "status": sensor.get('status'),
                "temperature": sensor.get('temperature', {}).get('value') or 0.0,
                "x_axis": sensor.get('x_axis', {}).get('value') or 0.0,
                "y_axis": sensor.get('y_axis', {}).get('value') or 0.0,
                "z_axis": sensor.get('z_axis', {}).get('value') or 0.0,
                "battery": device_batteries.get(first_device_num, 0),
                "signal": device_signals.get(first_device_num)
            }
            
            print(json.dumps(output, ensure_ascii=False))

class SensorDataManager:
    """传感器数据管理器"""
    
    def __init__(self, slave_id=SLAVE_ID, total_devices=64, generate_excel=GENERATE_EXCEL, quiet_mode=QUIET_MODE):
        self.data_reader = SensorDataReader(slave_id, total_devices)
        self.quiet_mode = quiet_mode
    
    def read_sensor_by_id(self, sock, sensor_id):
        """
        按传感器编号读取单个传感器的数据。
        
        返回结构示例(与终端打印格式完全一致，只保留汇总后的单个对象，不再输出各channel的独立值):
        {
            "sensor_id": 1,
            "status": "完整",
            "temperature": 0.0,
            "x_axis": 0.0,
            "y_axis": 0.0,
            "z_axis": 0.0,
            "battery": 0,
            "signal": null
        }
        """
        # 先批量读取所有传感器数据，复用已有的高效批量读取逻辑
        all_sensors = self.data_reader.read_all_sensor_data(sock)
        
        sensor = all_sensors.get(sensor_id)
        if sensor is None:
            return {
                "sensor_id": sensor_id,
                "error": f"指定的传感器 {sensor_id} 不存在或无数据"
            }

        device_batteries = sensor.get('device_batteries', {})
        device_signals = sensor.get('device_signals', {})
        # 每4个设备组成一个传感器, 按要求battery和signal取这一组中第1个设备的值
        first_device_num = (sensor_id - 1) * 4 + 1

        return {
            "sensor_id": sensor_id,
            "status": sensor.get('status'),
            "temperature": sensor.get('temperature', {}).get('value') or 0.0,
            "x_axis": sensor.get('x_axis', {}).get('value') or 0.0,
            "y_axis": sensor.get('y_axis', {}).get('value') or 0.0,
            "z_axis": sensor.get('z_axis', {}).get('value') or 0.0,
            "battery": device_batteries.get(first_device_num, 0),
            "signal": device_signals.get(first_device_num)
        }
    
    def read_all_node_data(self, sock):
        """读取所有节点数据（保留给兼容调用，不做任何打印）"""
        all_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sensors': {},
            'connection_test': '成功',
            'note': '温度数据应用除以10的修正，振动数据保持原值'
        }
        sensor_data = self.data_reader.read_all_sensor_data(sock)
        all_data['sensors'] = sensor_data
        return all_data

class GatewayReader:
    """LORA网关读取器"""
    
    def __init__(self, listen_ip, listen_port, interval=3600):
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.interval = interval
        self.running = False
        self.server_socket = None
        self.last_read_time = 0
        self.sensor_manager = SensorDataManager()
        
    def start(self):
        """启动服务器"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.listen_ip, self.listen_port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)
        
        print(f'[*] 服务器已启动 {self.listen_ip}:{self.listen_port}')
        print(f'[*] LORA网关站号: {SLAVE_ID}')
        print(f'[*] 读取间隔: {self.interval}秒 ({self.interval//3600}小时)')
        print(f'[*] 安静模式: {"开启" if QUIET_MODE else "关闭"}')
        print(f'[*] 按Ctrl+C停止服务器\n')
        
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                
                current_time = time.time()
                
                if current_time - self.last_read_time >= self.interval or self.last_read_time == 0:
                    if not QUIET_MODE:
                        print(f'[+] 开始读取数据，客户端: {addr}')
                    
                    try:
                        conn.settimeout(30.0)
                        
                        all_data = self.sensor_manager.read_all_node_data(conn)
                        
                        # 发送JSON数据给客户端
                        json_data = json.dumps(all_data, ensure_ascii=False, indent=2)
                        conn.sendall(json_data.encode() + b'\n')
                        
                        if not QUIET_MODE:
                            print(f"[+] 数据已发送给客户端")
                        
                        self.last_read_time = current_time
                        
                    except Exception as e:
                        if not QUIET_MODE:
                            print(f"处理数据时出错: {e}")
                        error_msg = {"error": f"处理数据时出错: {e}", "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        conn.sendall(json.dumps(error_msg).encode() + b'\n')
                    finally:
                        conn.close()
                        if not QUIET_MODE:
                            print('[-] 连接关闭\n')
                
                else:
                    wait_time = self.interval - (current_time - self.last_read_time)
                    if not QUIET_MODE:
                        print(f'[!] 未到读取时间，{wait_time:.0f}秒后再次读取，客户端: {addr}')
                    conn.close()
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    if not QUIET_MODE:
                        print(f"接受连接时出错: {e}")
                continue
    
    def stop(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        # 不再直接打印停止信息，保持安静模式

def get_gateway_data(listen_ip, listen_port, group_ids=None, timeout=60):
    """
    对外提供的网关数据读取函数（供 task_progress.py 调用）。

    - 在指定 IP/端口上作为 TCP 服务器监听，等待 LoRa 网关连接一次；
    - 使用已有的 SensorDataManager.read_all_node_data 读取所有传感器数据；
    - 若传入 group_ids(list[int])，则仅保留这些传感器编号对应的数据；
    - 返回结构示例：
        {
            "timestamp": "...",
            "sensors": { 1: { ... }, 2: { ... } },
            "connection_test": "成功",
            "note": "..."
        }

    注意：
    - listen_ip / listen_port 应由 task_progress.py 从数据库(iot_device_attr.ip/port)
      中动态获取后传入；
    - group_ids 应为任务关联的传感器(组号)列表。
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((listen_ip, listen_port))
        server_socket.listen(1)
        server_socket.settimeout(timeout)

        conn, addr = server_socket.accept()
        with conn:
            conn.settimeout(30.0)
            manager = SensorDataManager()
            all_data = manager.read_all_node_data(conn)

            # 根据 group_ids 过滤需要的传感器
            if group_ids:
                sensors = all_data.get("sensors", {}) or {}
                target_ids = {int(gid) for gid in group_ids if gid is not None}
                filtered = {}
                for key, value in sensors.items():
                    try:
                        sid = int(key)
                    except Exception:
                        continue
                    if sid in target_ids:
                        filtered[sid] = value
                all_data["sensors"] = filtered

            return all_data
    except socket.timeout:
        raise TimeoutError(
            "在限定时间内未收到 LoRa 网关连接，请检查网关配置（目标 IP/端口是否为指定的 listen_ip/listen_port）。"
        )
    finally:
        server_socket.close()


def main():
    """
    简单交互式主函数：保持原有行为，方便单独手工测试。
    """
    try:
        sensor_id_str = input("请输入要查询的传感器编号（整数）：").strip()
        sensor_id = int(sensor_id_str)
    except Exception:
        print("输入的传感器编号无效，请输入整数。")
        return

    try:
        data = get_gateway_data(LISTEN_IP, LISTEN_PORT, group_ids=[sensor_id])
        sensors = data.get("sensors", {})
        # 交互模式下，仍然使用原来的单传感器展现形式
        if not sensors:
            print(json.dumps(
                {"sensor_id": sensor_id, "error": "指定的传感器不存在或无数据"},
                ensure_ascii=False,
                indent=2,
            ))
        else:
            # 只取第一个匹配的传感器
            sid, payload = next(iter(sensors.items()))
            output = {
                "sensor_id": int(sid),
                "status": payload.get("status"),
                "temperature": payload.get("temperature", {}).get("value") or 0.0,
                "x_axis": payload.get("x_axis", {}).get("value") or 0.0,
                "y_axis": payload.get("y_axis", {}).get("value") or 0.0,
                "z_axis": payload.get("z_axis", {}).get("value") or 0.0,
                "battery": payload.get("battery") or 0,
                "signal": payload.get("signal"),
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
    except TimeoutError as e:
        print(str(e))
    except OSError as e:
        print(f"监听或接受网关连接失败: {e}")

if __name__ == '__main__':
    main()