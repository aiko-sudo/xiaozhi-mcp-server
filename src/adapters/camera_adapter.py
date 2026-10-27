"""摄像头适配器 — 捕获分析摄像头数据（目标检测/人脸/场景描述）"""

from adapters.base_adapter import BaseAdapter, AdapterResult
import random


class CameraAdapter(BaseAdapter):
    """
    摄像头数据适配器

    工具:
      - camera_capture:  拍摄一张照片并返回分析结果
      - camera_detect:   在当前帧中检测目标物体
      - camera_describe: 用文字描述当前画面内容
    """

    MOCK_OBJECTS = ["杯子", "手机", "书", "键盘", "鼠标", "盆栽", "椅子", "台灯", "水壶", "遥控器"]
    MOCK_SCENES = ["桌面", "客厅", "厨房", "办公室", "卧室", "走廊", "户外"]

    def tool_definitions(self):
        return [
            {
                "name": "camera_capture",
                "description": "拍摄一张照片并返回分析结果（目标检测+场景）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "enum": ["front", "wide", "depth"], "default": "front"},
                        "save_path": {"type": "string", "description": "保存路径（可选）"},
                    },
                },
            },
            {
                "name": "camera_detect",
                "description": "在当前帧中检测指定目标物体",
                "inputSchema": {
                    "type": "object",
                    "required": ["target"],
                    "properties": {
                        "target": {"type": "string", "description": "要检测的物体名称（如'杯子'）"},
                    },
                },
            },
            {
                "name": "camera_describe",
                "description": "用文字描述当前画面内容（视觉→语言）",
                "inputSchema": {"type": "object"},
            },
        ]

    def handle_tool(self, tool_name, arguments):
        if tool_name == "camera_capture":
            return self._capture(arguments)
        elif tool_name == "camera_detect":
            return self._detect(arguments)
        elif tool_name == "camera_describe":
            return self._describe()
        return AdapterResult(False, message=f"未知工具: {tool_name}")

    def _capture(self, args):
        source = args.get("source", "front")

        if self.backend == "mock":
            num_objects = random.randint(2, 5)
            detected = []
            for _ in range(num_objects):
                obj = random.choice(self.MOCK_OBJECTS)
                detected.append({
                    "name": obj,
                    "confidence": round(random.uniform(0.7, 0.99), 2),
                    "bbox": {
                        "x": round(random.uniform(0.1, 0.8), 2),
                        "y": round(random.uniform(0.1, 0.8), 2),
                        "w": round(random.uniform(0.1, 0.3), 2),
                        "h": round(random.uniform(0.1, 0.3), 2),
                    },
                })

            scene = random.choice(self.MOCK_SCENES)
            return AdapterResult(
                True,
                data={
                    "source": source,
                    "scene": scene,
                    "objects": detected,
                    "object_count": len(detected),
                    "image_ref": f"mock_{source}_{random.randint(1000,9999)}",
                    "resolution": "1280x720",
                },
                message=f"拍摄完成（{source}），检测到 {len(detected)} 个物体，场景: {scene}",
            )

        if self.backend == "http":
            result = self._send_http("camera/capture", args)
            return AdapterResult(result.get("success", False), data=result)

        return AdapterResult(False, message="不支持的后端")

    def _detect(self, args):
        target = args.get("target", "")

        # 先拍一张
        capture = self._capture({})
        if not capture.success:
            return capture

        objects = capture.data.get("objects", [])
        found = [o for o in objects if target.lower() in o["name"].lower()]

        if found:
            best = max(found, key=lambda x: x["confidence"])
            return AdapterResult(
                True,
                data={"target": target, "found": True, "best_match": best, "all_matches": found},
                message=f"✅ 找到 '{target}'，置信度 {best['confidence']}",
            )
        else:
            return AdapterResult(
                True,
                data={"target": target, "found": False, "detected_objects": [o["name"] for o in objects]},
                message=f"❌ 未找到 '{target}'，画面中有: {', '.join(o['name'] for o in objects)}",
            )

    def _describe(self):
        capture = self._capture({})
        if not capture.success:
            return capture

        scene = capture.data.get("scene", "未知场景")
        objects = [o["name"] for o in capture.data.get("objects", [])]

        if objects:
            desc = f"当前是{scene}场景，画面中有{'、'.join(objects)}。"
        else:
            desc = f"当前是{scene}场景，画面中没有检测到明显的物体。"

        return AdapterResult(
            True,
            data={"description": desc, "scene": scene, "objects": objects},
            message=desc,
        )
