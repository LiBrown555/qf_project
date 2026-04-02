#!/usr/bin/env python3
# coding=utf-8

"""
IoT 传感器 WebSocket 客户端
支持多客户端并发，声明式配置扩展：
  - 新增客户端只需在 CLIENT_SPECS 追加一条 ClientSpec
  - 新增数据源只需在 SharedContext 添加实例并更新对应 Spec 的 queue_getter
"""

import asyncio
import json
import queue
import signal
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import websockets
import yaml
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from log_record.log_record import LogAndRecord
from iot_sensor_exec.packages import (
    device_check,
    sensor_task_plan,
    sensor_task_post,
    sensor_task_progress,
)

with open('data/configuration/log_path.yaml', 'r', encoding='utf-8') as f:
    log_config = yaml.safe_load(f)
log_path = log_config['log']['iot_sensor_wb']


# ──────────────────────────────────────────────
# 连接配置
# ──────────────────────────────────────────────
class WebSocketConfig:
    """从 iot_websocket.yaml 读取指定 config_key 的连接参数"""

    def __init__(self, config_key: str = "sensor_wb") -> None:
        with open('data/configuration/iot_websocket.yaml', 'r', encoding='utf-8') as f:
            wb_cfg = yaml.safe_load(f)[config_key]
        self.host: str = wb_cfg['host']
        self.port: int = wb_cfg['port']
        self.path: str = wb_cfg['path']
        self.auth_token: str = wb_cfg['auth_token']
        self.scheme: str = "ws"
        self.reconnect_delay: float = 5.0
        self.max_reconnect_attempts: int = 0 # 0 = 无限重连
        self.ping_interval: Optional[float] = 20.0
        self.ping_timeout: Optional[float] = 10.0
        self.extra_headers: dict = {}

    @property
    def uri(self) -> str:
        return (
            f"{self.scheme}://{self.host}:{self.port}{self.path}"
            f"?authToken={self.auth_token}"
        )

@dataclass
class SharedContext:
    """
    统一持有所有后台生产者，避免重复实例化。
    新增数据源时，在此添加对应字段。
    """
    device_check_inst: device_check.DeviceCheck = field(
        default_factory=device_check.DeviceCheck
    )
    sensor_task_progress_inst: sensor_task_progress.SensorTaskProgress = field(
        default_factory=sensor_task_progress.SensorTaskProgress
    )
    sensor_task_plan_inst: sensor_task_plan.SensorTaskPlan = field(
        default_factory=sensor_task_plan.SensorTaskPlan
    )
    sensor_task_post_inst: sensor_task_post.SensorTaskPost = field(
        default_factory=sensor_task_post.SensorTaskPost
    )

@dataclass
class ClientSpec:
    """
    描述一个 WebSocket 客户端的完整规格。
    新增客户端只需在 CLIENT_SPECS 追加一条 ClientSpec，无需改动任何核心逻辑。
    """
    name: str                                                       # 客户端名称，用于日志区分
    config_key: str                                                 # iot_websocket.yaml 中的 key
    queue_getter: Callable[[SharedContext], List[queue.Queue]]      # 从 SharedContext 取哪些队列上传


# ── 在此声明所有客户端 ──────────────────────────
CLIENT_SPECS: List[ClientSpec] = [
    ClientSpec(
        name="sensor",
        config_key="sensor_wb",
        queue_getter=lambda ctx: [
            ctx.device_check_inst.sensor_recv_mes,
            ctx.sensor_task_progress_inst.sensor_recv_mes,
        ],
    ),
    ClientSpec(
        name="camera",
        config_key="nvr_wb",
        queue_getter=lambda ctx: [
            ctx.device_check_inst.camera_recv_mes,
            ctx.sensor_task_progress_inst.camera_recv_mes,
        ],
    )
]

class IoTSensorClient:
    """
    IoT 通用 WebSocket 客户端
    - 自动重连
    - 收到服务端消息后通过 sensor_task_plan 处理并回送响应
    - 从注入的队列列表主动上传数据到服务端
    """

    def __init__(
        self,
        config: WebSocketConfig,
        upload_queues: List[queue.Queue],
        ctx: SharedContext,
        name: str = "",
    ) -> None:
        self.log_init = LogAndRecord()
        logger_name = f"iot_sensor_wb_{name}" if name else "iot_sensor_wb"
        self.log_init.log_init(log_path, logger_name)
        if not self.log_init:
            raise Exception("日志初始化失败")
        self.logger = self.log_init.logger
        self.name = name
        self.config = config
        self.ctx = ctx
        self._upload_queues = upload_queues
        self._attempt = 0
        self._task: Optional[asyncio.Task] = None
        self._ws = None

    # ── 消息处理 ────────────────────────────────
    def on_message(self, raw: str) -> Optional[str]:
        """收到服务端消息时触发，返回值非空则回送给服务端"""
        try:
            data = json.loads(raw)
            self.logger.info("[%s] 收到数据: %s", self.name, json.dumps(data, ensure_ascii=False))
            return self.ctx.sensor_task_plan_inst.execute(data)
        except json.JSONDecodeError:
            self.logger.info("[%s] 收到原始消息: %s", self.name, raw)
            return None
        except Exception as e:
            self.logger.error("[%s] 消息处理异常: %s", self.name, e)
            return None

    def on_open(self) -> None:
        self.logger.info("[%s] 连接已建立 -> %s", self.name, self.config.uri)

    def on_close(self, code: int, reason: str) -> None:
        self.logger.warning("[%s] 连接已关闭 [code=%s] %s", self.name, code, reason)

    def on_error(self, exc: Exception) -> None:
        self.logger.error("[%s] 连接异常: %s", self.name, exc)

    # ── 主动上传 ────────────────────────────────
    async def send_message(self, data: dict) -> None:
        """主动向服务端发送数据"""
        if self._ws is None:
            self.logger.warning("[%s] 尚未建立连接，无法发送数据", self.name)
            return
        try:
            payload = json.dumps(data, ensure_ascii=False)
            await self._ws.send(payload)
            self.logger.info("[%s] 主动上传数据: %s", self.name, payload)
        except Exception as e:
            self.logger.error("[%s] 主动上传失败: %s", self.name, e)

    async def _active_upload_loop(self) -> None:
        """通用队列消费循环：轮询所有注入的队列，有数据则上传"""
        while True:
            for q in self._upload_queues:
                while not q.empty():
                    mes = q.get_nowait()
                    await self.send_message(mes)
            await asyncio.sleep(1)

    async def _listen(self) -> None:
        async with websockets.connect(
            self.config.uri,
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
                upload_task.cancel()
                try:
                    await upload_task
                except asyncio.CancelledError:
                    pass
                self._ws = None

    async def _recv_loop(self, ws) -> None:
        """内部接收循环，将服务端消息交由 on_message 处理后回送响应"""
        async for message in ws:
            resp = self.on_message(message)
            if resp:
                await ws.send(resp)

    async def _run_with_reconnect(self) -> None:
        while True:
            try:
                await self._listen()
            except ConnectionClosedOK:
                self.logger.info("[%s] 服务端正常关闭连接，停止重连", self.name)
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
                self.logger.error("[%s] 已达最大重连次数 (%d)，停止", self.name, max_attempts)
                return

            self.logger.info(
                "[%s] %.1f 秒后尝试第 %d 次重连...",
                self.name,
                self.config.reconnect_delay,
                self._attempt,
            )
            await asyncio.sleep(self.config.reconnect_delay)

    def start(self) -> None:
        """阻塞式启动单客户端，SIGINT/SIGTERM 触发即时退出"""
        async def _main():
            loop = asyncio.get_running_loop()
            self._task = asyncio.current_task()

            def _on_signal(signum, frame):
                self.logger.info("[%s] 收到退出信号 (%d)，正在关闭...", self.name, signum)
                loop.call_soon_threadsafe(self._task.cancel)

            signal.signal(signal.SIGINT, _on_signal)
            signal.signal(signal.SIGTERM, _on_signal)

            try:
                await self._run_with_reconnect()
            except asyncio.CancelledError:
                pass
            finally:
                self.logger.info("[%s] 客户端已退出", self.name)

        asyncio.run(_main())

    async def start_async(self) -> None:
        """在已有事件循环中启动（协程形式），支持外部调用 stop() 停止"""
        self._task = asyncio.current_task()
        await self._run_with_reconnect()

    def stop(self) -> None:
        """线程安全地停止客户端"""
        if self._task and not self._task.done():
            self._task.get_loop().call_soon_threadsafe(self._task.cancel)
            self.logger.info("[%s] 客户端已请求停止", self.name)

def build_client(spec: ClientSpec, ctx: SharedContext) -> IoTSensorClient:
    """根据 ClientSpec 构建客户端实例"""
    return IoTSensorClient(
        config=WebSocketConfig(config_key=spec.config_key),
        upload_queues=spec.queue_getter(ctx),
        ctx=ctx,
        name=spec.name,
    )

def main():
    ctx = SharedContext()
    clients = [build_client(spec, ctx) for spec in CLIENT_SPECS]

    async def _main():
        loop = asyncio.get_running_loop()
        tasks = [asyncio.create_task(c.start_async()) for c in clients]

        def _on_signal(signum, frame):
            for t in tasks:
                loop.call_soon_threadsafe(t.cancel)

        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)

        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(_main())

if __name__ == "__main__":
    main()