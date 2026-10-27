"""语音指令适配器 — 处理语音输入的转写、意图识别和命令执行"""

from adapters.base_adapter import BaseAdapter, AdapterResult
import random


class VoiceAdapter(BaseAdapter):
    """
    语音指令适配器

    工具:
      - voice_transcribe:   语音 → 文本
      - voice_intent:       文本 → 意图分类
      - voice_execute:      意图 → 命令执行（联动其他适配器）
    """

    INTENT_MAP = {
        "导航": ["去", "走", "过来", "前进", "后退", "左转", "右转", "停下"],
        "观察": ["看", "瞧", "是什么", "有什么", "看看", "扫描"],
        "表情": ["开心", "难过", "生气", "惊讶", "害怕", "困了"],
        "雷达": ["多远", "多近", "障碍", "前面", "危险", "距离"],
        "事件": ["提醒", "通知", "定时", "告诉我", "监测"],
    }

    def tool_definitions(self):
        return [
            {
                "name": "voice_transcribe",
                "description": "将语音音频转写为文本（模拟 STT）",
                "inputSchema": {
                    "type": "object",
                    "required": ["audio_ref"],
                    "properties": {
                        "audio_ref": {"type": "string", "description": "音频引用（文件路径或缓冲区 ID）"},
                        "language": {"type": "string", "default": "zh"},
                    },
                },
            },
            {
                "name": "voice_intent",
                "description": "从文本识别意图并分类",
                "inputSchema": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "text": {"type": "string", "description": "输入文本"},
                    },
                },
            },
            {
                "name": "voice_execute",
                "description": "根据意图执行对应动作（联动其他设备）",
                "inputSchema": {
                    "type": "object",
                    "required": ["intent", "text"],
                    "properties": {
                        "intent": {"type": "string"},
                        "text": {"type": "string"},
                        "params": {"type": "object"},
                    },
                },
            },
        ]

    def handle_tool(self, tool_name, arguments):
        if tool_name == "voice_transcribe":
            return self._transcribe(arguments)
        elif tool_name == "voice_intent":
            return self._detect_intent(arguments)
        elif tool_name == "voice_execute":
            return self._execute_intent(arguments)
        return AdapterResult(False, message=f"未知工具: {tool_name}")

    def _transcribe(self, args):
        if self.backend == "mock":
            # 模拟 STT 返回
            sample_texts = [
                "帮我看一下前面有什么",
                "去厨房",
                "开心一点",
                "前面有没有障碍物",
                "十分钟后提醒我",
            ]
            text = random.choice(sample_texts)
            return AdapterResult(True, data={"text": text, "language": args.get("language", "zh")}, message="STT 转写完成（mock）")

        if self.backend == "http":
            result = self._send_http("voice/transcribe", args)
            return AdapterResult(result.get("success", False), data=result, message=result.get("message", ""))

        return AdapterResult(False, message="不支持的后端")

    def _detect_intent(self, args):
        text = args.get("text", "")
        detected = []
        for intent, keywords in self.INTENT_MAP.items():
            if any(kw in text for kw in keywords):
                detected.append(intent)

        if not detected:
            detected = ["对话"]

        primary = detected[0]
        confidence = round(random.uniform(0.75, 0.98), 2) if self.backend == "mock" else 0.9

        return AdapterResult(
            True,
            data={
                "intent": primary,
                "all_intents": detected,
                "confidence": confidence,
                "original_text": text,
            },
            message=f"意图识别: {primary} (置信度 {confidence})",
        )

    def _execute_intent(self, args):
        intent = args.get("intent", "对话")
        text = args.get("text", "")
        params = args.get("params", {})

        # 意图 → 目标适配器/动作映射
        routing = {
            "导航": {"adapter": "navigation", "action": "navigate"},
            "观察": {"adapter": "camera", "action": "capture"},
            "表情": {"adapter": "emotion", "action": "set_emotion"},
            "雷达": {"adapter": "radar", "action": "scan"},
            "事件": {"adapter": "event", "action": "register"},
        }

        route = routing.get(intent)
        if not route:
            return AdapterResult(True, data={"action": "chat"}, message=f"意图 '{intent}' 转为对话处理")

        return AdapterResult(
            True,
            data={"route_to": route["adapter"], "action": route["action"], "text": text, "params": params},
            message=f"意图 '{intent}' → 路由到 {route['adapter']} 适配器",
        )
