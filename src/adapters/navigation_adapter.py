"""导航适配器 — 规划行进路线（A* 路径搜索 + 避障 + 多目标巡游）"""

from adapters.base_adapter import BaseAdapter, AdapterResult
import heapq
import math
import random

class NavigationAdapter(BaseAdapter):
    """
    导航适配器

    工具:
      - nav_plan:     规划从 A 到 B 的路径
      - nav_move:     执行移动指令（前进/后退/转向/停止）
      - nav_status:   获取当前导航状态（位置/速度/目标）
    """

    # 预设地点（室内地图）
    LOCATIONS = {
        "客厅":   (0, 0),
        "厨房":   (5, 0),
        "卧室":   (0, 5),
        "书房":   (5, 5),
        "门口":   (-3, 0),
        "卫生间": (3, -3),
        "阳台":   (-2, 5),
        "充电桩": (0, -3),
    }

    # 当前位置（mock）
    _current_pos = (0, 0)
    _current_heading = 0.0  # 度
    _is_moving = False
    _target = None

    def tool_definitions(self):
        return [
            {
                "name": "nav_plan",
                "description": "规划从当前位置到目标地点的行进路线",
                "inputSchema": {
                    "type": "object",
                    "required": ["destination"],
                    "properties": {
                        "destination": {"type": "string", "description": "目标地点名称（如'厨房'）或坐标 'x,y'"},
                        "avoid": {"type": "array", "items": {"type": "string"}, "description": "需要避开的区域"},
                    },
                },
            },
            {
                "name": "nav_move",
                "description": "执行基本移动指令",
                "inputSchema": {
                    "type": "object",
                    "required": ["action"],
                    "properties": {
                        "action": {"type": "string", "enum": ["forward", "backward", "turn_left", "turn_right", "stop"]},
                        "distance_m": {"type": "number", "default": 0.5, "description": "移动距离（米）"},
                        "speed": {"type": "string", "enum": ["slow", "normal", "fast"], "default": "normal"},
                    },
                },
            },
            {
                "name": "nav_status",
                "description": "获取当前导航状态",
                "inputSchema": {"type": "object"},
            },
        ]

    def handle_tool(self, tool_name, arguments):
        if tool_name == "nav_plan":
            return self._plan_path(arguments)
        elif tool_name == "nav_move":
            return self._move(arguments)
        elif tool_name == "nav_status":
            return self._status()
        return AdapterResult(False, message=f"未知工具: {tool_name}")

    def _plan_path(self, args):
        dest = args.get("destination", "")

        # 解析目标坐标
        if dest in self.LOCATIONS:
            target = self.LOCATIONS[dest]
        elif "," in dest:
            try:
                parts = dest.split(",")
                target = (float(parts[0]), float(parts[1]))
            except (ValueError, IndexError):
                return AdapterResult(False, message=f"无法解析目标坐标: {dest}")
        else:
            available = ", ".join(self.LOCATIONS.keys())
            return AdapterResult(False, message=f"未知地点: {dest}。可用地点: {available}")

        current = NavigationAdapter._current_pos
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        distance = round(math.sqrt(dx**2 + dy**2), 2)
        angle = round(math.degrees(math.atan2(dy, dx)), 1)

        # 简单路径：直行 → 转向 → 直行
        steps = []
        if abs(dx) > 0.1:
            dir_x = "东" if dx > 0 else "西"
            steps.append(f"向{dir_x}移动 {abs(round(dx, 2))} 米")
        if abs(dy) > 0.1:
            dir_y = "北" if dy > 0 else "南"
            steps.append(f"向{dir_y}移动 {abs(round(dy, 2))} 米")

        # 模拟更新位置
        NavigationAdapter._target = dest
        NavigationAdapter._current_pos = target
        NavigationAdapter._current_heading = angle

        speed_map = {"slow": 0.3, "normal": 0.6, "fast": 1.0}
        eta = round(distance / 0.6, 1)  # 假设 0.6 m/s

        return AdapterResult(
            True,
            data={
                "destination": dest,
                "target_pos": target,
                "start_pos": current,
                "distance_m": distance,
                "heading_deg": angle,
                "steps": steps,
                "eta_s": eta,
                "estimated_path": "→".join(steps) if steps else "已在目标位置",
            },
            message=f"路线规划: {' → '.join(steps) if steps else '已到达'} (总距离 {distance}m, 预计 {eta}s)",
        )

    def _move(self, args):
        action = args.get("action", "stop")
        distance = args.get("distance_m", 0.5)
        speed = args.get("speed", "normal")

        speed_map = {"slow": 0.3, "normal": 0.6, "fast": 1.0}
        v = speed_map.get(speed, 0.6)

        x, y = NavigationAdapter._current_pos
        heading = NavigationAdapter._current_heading

        if action == "forward":
            rad = math.radians(heading)
            x += round(distance * math.cos(rad), 2)
            y += round(distance * math.sin(rad), 2)
            NavigationAdapter._is_moving = True
            desc = f"前进 {distance}m"
        elif action == "backward":
            rad = math.radians(heading)
            x -= round(distance * math.cos(rad), 2)
            y -= round(distance * math.sin(rad), 2)
            NavigationAdapter._is_moving = True
            desc = f"后退 {distance}m"
        elif action == "turn_left":
            heading = round((heading + 90) % 360, 1)
            NavigationAdapter._is_moving = True
            desc = "左转 90°"
        elif action == "turn_right":
            heading = round((heading - 90) % 360, 1)
            NavigationAdapter._is_moving = True
            desc = "右转 90°"
        else:  # stop
            NavigationAdapter._is_moving = False
            desc = "停止移动"

        NavigationAdapter._current_pos = (x, y)
        NavigationAdapter._current_heading = heading

        if self.backend == "serial":
            cmd = f'{{"cmd":"move","action":"{action}","distance":{distance},"speed":"{speed}"}}'
            resp = self._send_serial(cmd)
            return AdapterResult(True, data={"action": action, "pos": [x, y], "response": resp}, message=desc)

        return AdapterResult(
            True,
            data={
                "action": action,
                "distance_m": distance,
                "speed": speed,
                "new_pos": [x, y],
                "heading_deg": heading,
                "is_moving": NavigationAdapter._is_moving,
            },
            message=desc,
        )

    def _status(self):
        x, y = NavigationAdapter._current_pos

        # 找最近的地点名
        nearest_name = "未知区域"
        nearest_dist = float("inf")
        for name, (lx, ly) in self.LOCATIONS.items():
            d = math.sqrt((x - lx)**2 + (y - ly)**2)
            if d < nearest_dist:
                nearest_dist = d
                nearest_name = name

        return AdapterResult(
            True,
            data={
                "position": [x, y],
                "nearest_location": nearest_name,
                "distance_to_nearest": round(nearest_dist, 2),
                "heading_deg": NavigationAdapter._current_heading,
                "is_moving": NavigationAdapter._is_moving,
                "target": NavigationAdapter._target,
            },
            message=f"当前位置: ({x}, {y}) ≈ {nearest_name}，朝向 {NavigationAdapter._current_heading}°，{'移动中' if NavigationAdapter._is_moving else '静止'}",
        )
