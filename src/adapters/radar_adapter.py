"""雷达适配器 — 收集判断雷达信息（距离/障碍/环境地图）"""

from adapters.base_adapter import BaseAdapter, AdapterResult
import random
import math


class RadarAdapter(BaseAdapter):
    """
    雷达数据适配器

    支持 LiDAR（激光雷达）和 超声波传感器。
    工具:
      - radar_scan:       单次扫描，返回前方距离/障碍列表
      - radar_get_map:    获取当前环境地图快照（极坐标点集）
      - radar_check_safe: 检查指定方向是否安全（无障碍）
    """

    def tool_definitions(self):
        return [
            {
                "name": "radar_scan",
                "description": "执行雷达扫描，返回障碍物距离和角度分布",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "range_m": {"type": "number", "default": 5.0, "description": "扫描范围（米）"},
                        "angle_start": {"type": "number", "default": 0, "description": "起始角度（度）"},
                        "angle_end": {"type": "number", "default": 360, "description": "结束角度（度）"},
                    },
                },
            },
            {
                "name": "radar_check_safe",
                "description": "检查指定方向是否安全（无近距障碍）",
                "inputSchema": {
                    "type": "object",
                    "required": ["direction"],
                    "properties": {
                        "direction": {"type": "string", "enum": ["front", "left", "right", "back", "all"]},
                        "safe_distance_m": {"type": "number", "default": 0.5},
                    },
                },
            },
            {
                "name": "radar_get_map",
                "description": "获取360度极坐标环境地图",
                "inputSchema": {"type": "object"},
            },
        ]

    def handle_tool(self, tool_name, arguments):
        if tool_name == "radar_scan":
            return self._scan(arguments)
        elif tool_name == "radar_check_safe":
            return self._check_safe(arguments)
        elif tool_name == "radar_get_map":
            return self._get_map()
        return AdapterResult(False, message=f"未知工具: {tool_name}")

    def _scan(self, args):
        range_m = args.get("range_m", 5.0)
        angle_start = args.get("angle_start", 0)
        angle_end = args.get("angle_end", 360)

        if self.backend == "mock":
            # 模拟雷达数据：在范围内随机生成障碍物
            obstacles = []
            num_obstacles = random.randint(2, 6)
            for _ in range(num_obstacles):
                angle = random.uniform(angle_start, angle_end)
                distance = round(random.uniform(0.3, range_m), 2)
                obstacles.append({
                    "angle_deg": round(angle, 1),
                    "distance_m": distance,
                    "confidence": round(random.uniform(0.8, 1.0), 2),
                })
            obstacles.sort(key=lambda x: x["distance_m"])

            nearest = obstacles[0] if obstacles else None
            return AdapterResult(
                True,
                data={
                    "obstacles": obstacles,
                    "count": len(obstacles),
                    "nearest": nearest,
                    "scan_range_m": range_m,
                    "clear_front": nearest is None or nearest["distance_m"] > 1.0 and abs(nearest["angle_deg"]) < 30,
                },
                message=f"扫描完成: {len(obstacles)} 个障碍物" + (f"，最近 {nearest['distance_m']}m" if nearest else ""),
            )

        if self.backend == "http":
            result = self._send_http("radar/scan", args)
            return AdapterResult(result.get("success", False), data=result)

        return AdapterResult(False, message="不支持的后端")

    def _check_safe(self, args):
        direction = args.get("direction", "front")
        safe_dist = args.get("safe_distance_m", 0.5)

        # 先扫描
        scan_result = self._scan({"range_m": 3.0})
        if not scan_result.success:
            return scan_result

        obstacles = scan_result.data.get("obstacles", [])

        # 方向 → 角度范围映射
        dir_angles = {
            "front": (315, 45),
            "left": (225, 315),
            "right": (45, 135),
            "back": (135, 225),
            "all": (0, 360),
        }
        a_start, a_end = dir_angles.get(direction, (0, 360))

        def in_range(angle):
            if a_start < a_end:
                return a_start <= angle <= a_end
            return angle >= a_start or angle <= a_end

        relevant = [o for o in obstacles if in_range(o["angle_deg"])]
        unsafe = [o for o in relevant if o["distance_m"] < safe_dist]

        return AdapterResult(
            True,
            data={
                "direction": direction,
                "is_safe": len(unsafe) == 0,
                "safe_distance_m": safe_dist,
                "obstacles_in_direction": relevant,
                "unsafe_count": len(unsafe),
            },
            message=f"方向 '{direction}' {'✅安全' if not unsafe else f'❌有 {len(unsafe)} 个危险障碍'}",
        )

    def _get_map(self):
        scan = self._scan({"range_m": 10.0, "angle_start": 0, "angle_end": 360})
        if not scan.success:
            return scan

        # 构建极坐标点集
        points = []
        for obs in scan.data.get("obstacles", []):
            angle_rad = math.radians(obs["angle_deg"])
            points.append({
                "x": round(obs["distance_m"] * math.cos(angle_rad), 2),
                "y": round(obs["distance_m"] * math.sin(angle_rad), 2),
                "angle": obs["angle_deg"],
                "distance": obs["distance_m"],
            })

        return AdapterResult(
            True,
            data={"points": points, "point_count": len(points), "format": "polar_xy"},
            message=f"环境地图: {len(points)} 个点",
        )
