"""眼球控制适配器 — 控制仿生眼球的注视方向和运动模式

复用 animatronic-eye-pro 项目的 EyeThing.h 协议和 BoardConfigXZ 引脚映射。
"""

from adapters.base_adapter import BaseAdapter, AdapterResult
import math

class EyeAdapter(BaseAdapter):
    """
    眼球控制适配器

    对接 animatronic-eye-pro 的 JSON 串口协议：
      {"cmd": "look", "x": 0.5, "y": 0.3}
      {"cmd": "emotion", "name": "happy"}

    工具:
      - eye_look:     控制眼球看向指定方向（归一化坐标或方向词）
      - eye_track:    追踪移动目标（连续模式）
      - eye_action:   执行预定义眼球动作（眨眼/扫视/搜索）
    """

    # 方向词 → 归一化坐标 (x: -1左 ~ 1右, y: -1下 ~ 1上)
    DIRECTIONS = {
        "center": (0.0, 0.0),
        "left": (-0.8, 0.0),
        "right": (0.8, 0.0),
        "up": (0.0, 0.8),
        "down": (0.0, -0.8),
        "up_left": (-0.6, 0.6),
        "up_right": (0.6, 0.6),
        "down_left": (-0.6, -0.6),
        "down_right": (0.6, -0.6),
    }

    # 安全限位
    MAX_X = 1.0
    MAX_Y = 1.0
    MAX_SPEED = 200  # 度/秒

    def tool_definitions(self):
        return [
            {
                "name": "eye_look",
                "description": "控制眼球看向指定方向",
                "inputSchema": {
                    "type": "object",
                    "required": ["direction"],
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": list(self.DIRECTIONS.keys()),
                            "description": "注视方向",
                        },
                        "x": {"type": "number", "minimum": -1, "maximum": 1, "description": "自定义水平坐标（覆盖 direction）"},
                        "y": {"type": "number", "minimum": -1, "maximum": 1, "description": "自定义垂直坐标"},
                        "duration_s": {"type": "number", "default": 2.0, "description": "注视持续时间"},
                    },
                },
            },
            {
                "name": "eye_track",
                "description": "开启/关闭目标追踪模式",
                "inputSchema": {
                    "type": "object",
                    "required": ["action"],
                    "properties": {
                        "action": {"type": "string", "enum": ["start", "stop", "status"]},
                        "target": {"type": "string", "description": "追踪目标（如'人脸'）"},
                    },
                },
            },
            {
                "name": "eye_action",
                "description": "执行预定义眼球动作",
                "inputSchema": {
                    "type": "object",
                    "required": ["action"],
                    "properties": {
                        "action": {"type": "string", "enum": ["blink", "saccade", "scan", "reset"]},
                        "speed": {"type": "string", "enum": ["slow", "normal", "fast"], "default": "normal"},
                    },
                },
            },
        ]

    def handle_tool(self, tool_name, arguments):
        if tool_name == "eye_look":
            return self._look(arguments)
        elif tool_name == "eye_track":
            return self._track(arguments)
        elif tool_name == "eye_action":
            return self._action(arguments)
        return AdapterResult(False, message=f"未知工具: {tool_name}")

    def _look(self, args):
        direction = args.get("direction", "center")
        x = args.get("x")
        y = args.get("y")

        # 如果提供了自定义坐标，覆盖方向
        if x is not None and y is not None:
            x = max(-self.MAX_X, min(self.MAX_X, x))
            y = max(-self.MAX_Y, min(self.MAX_Y, y))
        else:
            x, y = self.DIRECTIONS.get(direction, (0.0, 0.0))

        duration = args.get("duration_s", 2.0)

        if self.backend == "serial":
            cmd = f'{{"cmd":"look","x":{x},"y":{y},"duration":{duration}}}'
            resp = self._send_serial(cmd)
            return AdapterResult(True, data={"x": x, "y": y, "serial_response": resp}, message=f"眼球看向 ({x:.1f}, {y:.1f})")

        # mock
        angle_h = round(math.degrees(math.atan2(x, 1.0)), 1)  # 水平角度
        angle_v = round(math.degrees(math.atan2(y, 1.0)), 1)  # 垂直角度
        return AdapterResult(
            True,
            data={"x": x, "y": y, "angle_h": angle_h, "angle_v": angle_v, "duration_s": duration},
            message=f"眼球看向方向 '{direction}' (x={x:.1f}, y={y:.1f})，持续 {duration}s",
        )

    def _track(self, args):
        action = args.get("action", "status")
        target = args.get("target", "face")

        if action == "start":
            return AdapterResult(True, data={"tracking": True, "target": target}, message=f"开始追踪: {target}")
        elif action == "stop":
            return AdapterResult(True, data={"tracking": False}, message="停止追踪")
        else:
            return AdapterResult(True, data={"tracking": False, "target": None}, message="追踪状态: 未激活")

    def _action(self, args):
        action = args.get("action", "blink")
        speed = args.get("speed", "normal")

        speed_map = {"slow": 0.5, "normal": 1.0, "fast": 2.0}
        speed_factor = speed_map.get(speed, 1.0)

        if self.backend == "serial":
            cmd = f'{{"cmd":"action","name":"{action}","speed":{speed_factor}}}'
            resp = self._send_serial(cmd)
            return AdapterResult(True, data={"action": action, "speed": speed, "response": resp}, message=f"执行: {action} ({speed})")

        return AdapterResult(
            True,
            data={"action": action, "speed": speed, "speed_factor": speed_factor},
            message=f"执行眼球动作: {action} ({speed})",
        )
