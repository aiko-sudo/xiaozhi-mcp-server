"""
适配器基类 — 所有外设适配器的统一接口

支持三种通信后端：
  - mock:   模拟模式（无硬件，返回假数据）
  - serial: 串口通信（ESP32/STM32 直连）
  - http:   HTTP API（Jetson/ROS2 服务）
"""

import time
import random
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AdapterResult:
    """适配器统一返回结构"""
    success: bool
    data: dict = field(default_factory=dict)
    message: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class BaseAdapter(ABC):
    """
    外设适配器基类

    子类必须实现:
      - tool_definitions() → list[ToolDef]
      - handle_tool(name, args) → AdapterResult
    """

    def __init__(self, name: str, backend: str = "mock", config: dict = None):
        self.name = name
        self.backend = backend  # "mock" | "serial" | "http"
        self.config = config or {}
        self.connected = False
        self._serial_conn = None
        self._http_base = self.config.get("http_base_url", "http://localhost:8080")

        if backend == "serial":
            self._init_serial()
        elif backend == "http":
            self._init_http()
        elif backend == "mock":
            self.connected = True
            logger.info(f"[{self.name}] Mock 模式启动")

    def _init_serial(self):
        """初始化串口连接"""
        port = self.config.get("serial_port", "/dev/ttyUSB0")
        baud = self.config.get("serial_baud", 115200)
        try:
            import serial
            self._serial_conn = serial.Serial(port, baud, timeout=1)
            self.connected = True
            logger.info(f"[{self.name}] 串口连接: {port}@{baud}")
        except ImportError as e:
            raise RuntimeError(f"[{self.name}] pyserial 未安装，拒绝使用模拟数据代替真实设备") from e
        except Exception as e:
            raise RuntimeError(f"[{self.name}] 串口连接失败，拒绝降级为 mock: {e}") from e

    def _init_http(self):
        """初始化 HTTP 连接"""
        try:
            import requests
            r = requests.get(f"{self._http_base}/health", timeout=2)
            r.raise_for_status()
            self.connected = True
            logger.info(f"[{self.name}] HTTP 连接: {self._http_base}")
        except Exception as e:
            raise RuntimeError(f"[{self.name}] HTTP 健康检查失败，拒绝降级为 mock: {e}") from e

    def _send_serial(self, command: str) -> str:
        """通过串口发送命令并读取响应"""
        if not self._serial_conn:
            raise RuntimeError(f"[{self.name}] 串口未连接，拒绝伪造成功响应")
        self._serial_conn.write((command + "\n").encode())
        time.sleep(0.05)  # 等待设备处理
        response = self._serial_conn.readline().decode().strip()
        return response

    def _send_http(self, endpoint: str, data: dict = None) -> dict:
        """通过 HTTP 发送请求"""
        try:
            import requests
            url = f"{self._http_base}/{endpoint.lstrip('/')}"
            r = requests.post(url, json=data or {}, timeout=5)
            return r.json()
        except Exception as e:
            logger.warning(f"[{self.name}] HTTP 请求失败: {e}")
            return {"error": str(e)}

    def _mock_response(self, command: str) -> str:
        """Mock 模式默认响应"""
        return f"{{\"status\":\"ok\",\"mock\":true,\"cmd\":\"{command}\"}}"

    @abstractmethod
    def tool_definitions(self) -> list:
        """返回该适配器支持的 MCP 工具定义列表"""
        pass

    @abstractmethod
    def handle_tool(self, tool_name: str, arguments: dict) -> AdapterResult:
        """处理工具调用"""
        pass

    def status(self) -> dict:
        """适配器状态"""
        return {
            "name": self.name,
            "backend": self.backend,
            "connected": self.connected,
            "config": {k: v for k, v in self.config.items()
                       if k not in ("serial_port", "token", "password")},
        }
