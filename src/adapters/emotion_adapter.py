"""表情管理适配器 — 模拟和管理机器人面部表情

复用 animatronic-eye-pro 的 EmotionMapper 和 EyeExpression 系统。
8 种基础表情 + 自定义 + 情绪映射。
"""

from adapters.base_adapter import BaseAdapter, AdapterResult
import random

class EmotionAdapter(BaseAdapter):
    """
    表情管理适配器

    工具:
      - emotion_set:    设置当前表情/情绪
      - emotion_list:   列出所有可用表情
      - emotion_map:    从文本关键词推断情绪（TTS 情绪反射）
    """

    # 8 种基础表情（对齐 animatronic-eye-pro EyeExpression）
    EMOTIONS = {
        "happy":       {"name": "开心", "intensity": 0.7, "keywords": ["开心", "高兴", "快乐", "棒", "好"]},
        "sad":         {"name": "难过", "intensity": 0.6, "keywords": ["难过", "伤心", "哭", "悲伤"]},
        "angry":       {"name": "生气", "intensity": 0.8, "keywords": ["生气", "怒", "烦", "讨厌"]},
        "surprised":   {"name": "惊讶", "intensity": 0.9, "keywords": ["惊讶", "哇", "天哪", "不会吧"]},
        "scared":      {"name": "害怕", "intensity": 0.7, "keywords": ["害怕", "吓", "恐惧", "危险"]},
        "sleepy":      {"name": "困倦", "intensity": 0.4, "keywords": ["困", "累", "睡", "疲惫"]},
        "curious":     {"name": "好奇", "intensity": 0.6, "keywords": ["好奇", "什么", "为什么", "怎么"]},
        "neutral":     {"name": "平静", "intensity": 0.3, "keywords": []},
    }

    # 当前情绪状态
    _current_emotion = "neutral"
    _current_intensity = 0.3

    def tool_definitions(self):
        return [
            {
                "name": "emotion_set",
                "description": "设置机器人当前表情/情绪",
                "inputSchema": {
                    "type": "object",
                    "required": ["emotion"],
                    "properties": {
                        "emotion": {"type": "string", "enum": list(self.EMOTIONS.keys())},
                        "intensity": {"type": "number", "minimum": 0, "maximum": 1, "default": None},
                        "duration_s": {"type": "number", "default": 5.0, "description": "持续时间（秒），之后恢复 neutral"},
                    },
                },
            },
            {
                "name": "emotion_list",
                "description": "列出所有可用表情",
                "inputSchema": {"type": "object"},
            },
            {
                "name": "emotion_infer",
                "description": "从文本内容推断合适情绪（TTS 情绪反射引擎）",
                "inputSchema": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "text": {"type": "string", "description": "要分析的文本（如 TTS 输出）"},
                    },
                },
            },
        ]

    def handle_tool(self, tool_name, arguments):
        if tool_name == "emotion_set":
            return self._set_emotion(arguments)
        elif tool_name == "emotion_list":
            return self._list_emotions()
        elif tool_name == "emotion_infer":
            return self._infer_emotion(arguments)
        return AdapterResult(False, message=f"未知工具: {tool_name}")

    def _set_emotion(self, args):
        emotion = args.get("emotion", "neutral")
        if emotion not in self.EMOTIONS:
            return AdapterResult(False, message=f"未知表情: {emotion}")

        emo_info = self.EMOTIONS[emotion]
        intensity = args.get("intensity", emo_info["intensity"])
        duration = args.get("duration_s", 5.0)

        # 更新状态
        EmotionAdapter._current_emotion = emotion
        EmotionAdapter._current_intensity = intensity

        if self.backend == "serial":
            cmd = f'{{"cmd":"emotion","name":"{emotion}","intensity":{intensity}}}'
            resp = self._send_serial(cmd)
            return AdapterResult(True, data={"emotion": emotion, "intensity": intensity, "response": resp}, message=f"表情设为: {emo_info['name']}")

        return AdapterResult(
            True,
            data={
                "emotion": emotion,
                "name_cn": emo_info["name"],
                "intensity": intensity,
                "duration_s": duration,
            },
            message=f"表情设为「{emo_info['name']}」(强度 {intensity})，持续 {duration}s",
        )

    def _list_emotions(self):
        emotions = []
        for key, info in self.EMOTIONS.items():
            emotions.append({"id": key, "name": info["name"], "default_intensity": info["intensity"]})

        return AdapterResult(
            True,
            data={
                "emotions": emotions,
                "current": self._current_emotion,
                "current_intensity": self._current_intensity,
            },
            message=f"共 {len(emotions)} 种表情，当前: {self.EMOTIONS.get(self._current_emotion, {}).get('name', '未知')}",
        )

    def _infer_emotion(self, args):
        text = args.get("text", "").lower()

        best_match = "neutral"
        best_score = 0
        scores = {}

        for emo_id, emo_info in self.EMOTIONS.items():
            score = sum(1 for kw in emo_info["keywords"] if kw in text)
            if score > 0:
                scores[emo_id] = score
                if score > best_score:
                    best_score = score
                    best_match = emo_id

        confidence = min(best_score / 3.0, 1.0) if best_score > 0 else 0.0

        return AdapterResult(
            True,
            data={
                "inferred_emotion": best_match,
                "name_cn": self.EMOTIONS[best_match]["name"],
                "confidence": round(confidence, 2),
                "all_scores": scores,
            },
            message=f"推断情绪: {self.EMOTIONS[best_match]['name']} (置信度 {confidence:.0%})" if best_score > 0 else "未检测到明显情绪倾向",
        )
