"""
工具注册器 — 聚合所有适配器，统一管理 MCP 工具

负责：
  1. 初始化所有适配器
  2. 聚合工具定义
  3. 路由工具调用到对应适配器
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters.voice_adapter import VoiceAdapter
from adapters.radar_adapter import RadarAdapter
from adapters.camera_adapter import CameraAdapter
from adapters.eye_adapter import EyeAdapter
from adapters.emotion_adapter import EmotionAdapter
from adapters.navigation_adapter import NavigationAdapter
from adapters.event_adapter import EventAdapter

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    工具注册中心

    管理 7 大适配器的全部工具，提供统一调用接口。
    """

    def __init__(self, backend: str = "mock", config: dict = None):
        self.config = config or {}
        self.adapters = {}
        self._tool_map = {}  # tool_name → (adapter_name, adapter)

        self._init_adapters(backend)

    def _init_adapters(self, backend: str):
        """初始化所有适配器"""
        adapter_configs = {
            "voice": self.config.get("voice", {}),
            "radar": self.config.get("radar", {}),
            "camera": self.config.get("camera", {}),
            "eye": self.config.get("eye", {}),
            "emotion": self.config.get("emotion", {}),
            "navigation": self.config.get("navigation", {}),
            "event": self.config.get("event", {}),
        }

        adapter_classes = {
            "voice": VoiceAdapter,
            "radar": RadarAdapter,
            "camera": CameraAdapter,
            "eye": EyeAdapter,
            "emotion": EmotionAdapter,
            "navigation": NavigationAdapter,
            "event": EventAdapter,
        }

        for name, cls in adapter_classes.items():
            cfg = dict(adapter_configs.get(name, {}))
            cfg.setdefault("backend", backend)
            actual_backend = cfg.pop("backend", backend)
            if actual_backend != "mock":
                raise RuntimeError(
                    f"适配器 '{name}' 初始化失败: 实际设备后端尚未完成安全验证，暂仅支持显式 mock"
                )
            try:
                adapter = cls(name=name, backend=actual_backend, config=cfg)
                self.adapters[name] = adapter
                # 注册工具
                for tool_def in adapter.tool_definitions():
                    self._tool_map[tool_def["name"]] = (name, adapter)
                logger.info(f"适配器 '{name}' 初始化完成 ({len(adapter.tool_definitions())} 工具)")
            except Exception as e:
                logger.error(f"适配器 '{name}' 初始化失败，拒绝降级为模拟设备: {e}")
                raise RuntimeError(f"适配器 '{name}' 初始化失败: {e}") from e

    def list_tools(self) -> list:
        """列出所有可用工具（MCP tools/list 格式）"""
        tools = []
        for tool_name, (adapter_name, adapter) in self._tool_map.items():
            # 找到对应的 tool_def
            for td in adapter.tool_definitions():
                if td["name"] == tool_name:
                    tools.append(td)
                    break
        return tools

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        调用工具

        Args:
            tool_name: 工具名
            arguments: 参数字典

        Returns:
            AdapterResult.to_dict()
        """
        if tool_name not in self._tool_map:
            return {
                "success": False,
                "data": {},
                "message": f"未知工具: {tool_name}。可用工具: {', '.join(sorted(self._tool_map.keys()))}",
            }

        adapter_name, adapter = self._tool_map[tool_name]
        try:
            result = adapter.handle_tool(tool_name, arguments)
            payload = result.to_dict()
            payload["backend"] = adapter.backend
            payload["simulated"] = adapter.backend == "mock"
            return payload
        except Exception as e:
            logger.error(f"工具调用异常 [{tool_name}]: {e}")
            return {
                "success": False,
                "data": {},
                "message": f"工具执行异常: {e}",
            }

    def get_status(self) -> dict:
        """获取所有适配器状态"""
        return {
            name: adapter.status()
            for name, adapter in self.adapters.items()
        }

    @property
    def tool_count(self) -> int:
        return len(self._tool_map)

    @property
    def adapter_count(self) -> int:
        return len(self.adapters)
