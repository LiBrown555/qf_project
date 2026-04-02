#!/usr/bin/env python3
# coding=utf-8

"""
IoT 传感器 WebSocket 客户端
实时接收服务端推送的传感器数据
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Optional
from log_record.log_record import LogAndRecord
import websockets
import yaml
import signal
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from iot_sensor_exec.packages import sensor_task_plan, device_check, sensor_task_progress, sensor_task_post

with open('data/configuration/log_path.yaml', 'r', encoding='utf-8') as f:
    log_config = yaml.safe_load(f)
log_path = log_config['log']['iot_sensor_wb']

# ──────────────────────────────────────────────
# 连接配置
# ──────────────────────────────────────────────
@dataclass
class WebSocketConfig:
    scheme: str = "ws"                  # ws / wss
    reconnect_delay: float = 5.0        # 断线重连间隔（秒）
    max_reconnect_attempts: int = 0     # 0 = 无限重连
    ping_interval: Optional[float] = 20.0
    ping_timeout: Optional[float] = 10.0
    extra_headers: dict = field(default_factory=dict)
    with open('data/configuration/iot_websocket.yaml', 'r', encoding='utf-8') as f:
        websocket_config = yaml.safe_load(f)
    host: str = websocket_config['sensor_wb']['host']
    port: int = websocket_config['sensor_wb']['port']
    path: str = websocket_config['sensor_wb']['path']
    auth_token: str = websocket_config['sensor_wb']['auth_token']

    @property
    def uri(self) -> str:
        return (
            f"{self.scheme}://{self.host}:{self.port}{self.path}"
            f"?authToken={self.auth_token}"
        )


class IoTSensorClient:
    """
    IoT 传感器 WebSocket 客户端
    - 自动重连
    - 结构化消息处理
    """

    def __init__(self, config: WebSocketConfig) -> None:
        self.log_init = LogAndRecord()
        self.log_init.log_init(log_path, "iot_sensor_wb")
        if not self.log_init:
            raise Exception("日志初始化失败")
        self.logger = self.log_init.logger
        self.config = config
        self._attempt = 0
        self._task: Optional[asyncio.Task] = None
        self._ws = None                          # 当前 WebSocket 连接引用
        self.sensor_task_plan = sensor_task_plan.SensorTaskPlan()
        self.device_check = device_check.DeviceCheck()
        self.sensor_task_progress = sensor_task_progress.SensorTaskProgress()
        self.sensor_task_post = sensor_task_post.SensorTaskPost()
    # ── 消息处理（可按需重写） ──────────────────
    def on_message(self, raw: str) -> None:
        """收到服务端消息时触发"""
        try:
            data = json.loads(raw)
            self.logger.info("收到数据: %s", json.dumps(data, ensure_ascii=False))
            return self.sensor_task_plan.execute(data)
        except json.JSONDecodeError:
            self.logger.info("收到原始消息: %s", raw)
            return None
        except Exception as e:
            self.logger.error("消息处理异常: %s", e)
            return None

    def on_open(self) -> None:
        """连接建立时触发"""
        self.logger.info("连接已建立 -> %s", self.config.uri)

    def on_close(self, code: int, reason: str) -> None:
        """连接关闭时触发"""
        self.logger.warning("连接已关闭 [code=%s] %s", code, reason)

    def on_error(self, exc: Exception) -> None:
        """连接发生错误时触发"""
        self.logger.error("连接异常: %s", exc)

    # ── 主动上传 ────────────────────────────────
    async def send_message(self, data: dict) -> None:
        """主动向服务端发送数据（可在任意协程中调用）"""
        if self._ws is None:
            self.logger.warning("尚未建立连接，无法发送数据")
            return
        try:
            payload = json.dumps(data, ensure_ascii=False)
            await self._ws.send(payload)
            self.logger.info("主动上传数据: %s", payload)
        except Exception as e:
            self.logger.error("主动上传失败: %s", e)

    async def _active_upload_loop(self) -> None:
        """
        主动上传循环（可按需重写）。
        默认空实现，子类覆盖此方法以实现周期性推送逻辑。
        示例：每隔 10 秒上报一次心跳或采集数据。
        """
        while True:
            if self.device_check.recv_status:
                # 原子性地取走列表并重置状态，避免竞态丢数据
                recv_mes = self.device_check.recv_mes.copy()
                self.device_check.recv_mes.clear()
                self.device_check.recv_status = False
                for mes in recv_mes:
                    await self.send_message(mes)   # 传字典，send_message内部统一序列化
            # 一次性排空队列，避免积压
            while not self.sensor_task_progress.recv_mes.empty():
                recv_mes = self.sensor_task_progress.recv_mes.get_nowait()
                await self.send_message(recv_mes)
            await asyncio.sleep(1)

    async def _listen(self) -> None:
        uri = self.config.uri
        async with websockets.connect(
            uri,
            ping_interval=self.config.ping_interval,
            ping_timeout=self.config.ping_timeout,
            extra_headers=self.config.extra_headers,
        ) as ws:
            self._ws = ws
            self._attempt = 0
            self.on_open()
            upload_task = asyncio.create_task(self._active_upload_loop())
            try:
                await self._recv_loop(ws)
            finally:
                # _recv_loop 无论正常结束还是异常，都取消上传任务并重置 ws
                upload_task.cancel()
                try:
                    await upload_task
                except asyncio.CancelledError:
                    pass
                self._ws = None

    async def _recv_loop(self, ws) -> None:
        """内部接收循环"""
        async for message in ws:
            recv_mes = self.on_message(message)
            if recv_mes:
                await ws.send(recv_mes)

    async def _run_with_reconnect(self) -> None:
        while True:
            try:
                await self._listen()
            except ConnectionClosedOK:
                self.logger.info("服务端正常关闭连接，停止重连")
                return
            except asyncio.CancelledError:
                raise
            except ConnectionClosedError as exc:
                self.on_close(exc.code, exc.reason)
            except Exception as exc:
                self.on_error(exc)

            self._attempt += 1
            max_attempts = self.config.max_reconnect_attempts
            if max_attempts and self._attempt >= max_attempts:
                self.logger.error("已达最大重连次数 (%d)，停止", max_attempts)
                return

            self.logger.info(
                "%.1f 秒后尝试第 %d 次重连...",
                self.config.reconnect_delay,
                self._attempt,
            )
            await asyncio.sleep(self.config.reconnect_delay)

    def start(self) -> None:
        """阻塞式启动，SIGINT/SIGTERM 触发即时退出"""
        async def _main():
            loop = asyncio.get_running_loop()
            self._task = asyncio.current_task()

            def _on_signal(signum, frame):
                self.logger.info("收到退出信号 (%d)，正在关闭...", signum)
                loop.call_soon_threadsafe(self._task.cancel)

            signal.signal(signal.SIGINT, _on_signal)
            signal.signal(signal.SIGTERM, _on_signal)

            try:
                await self._run_with_reconnect()
            except asyncio.CancelledError:
                pass
            finally:
                self.logger.info("客户端已退出")

        asyncio.run(_main())

    async def start_async(self) -> None:
        """在已有事件循环中启动（协程形式），支持外部调用 stop() 停止"""
        self._task = asyncio.current_task()
        await self._run_with_reconnect()

    def stop(self) -> None:
        """线程安全地停止客户端"""
        if self._task and not self._task.done():
            self._task.get_loop().call_soon_threadsafe(self._task.cancel)
            self.logger.info("客户端已请求停止")


if __name__ == "__main__":
    config = WebSocketConfig()
    client = IoTSensorClient(config)
    client.start()
