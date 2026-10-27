"""即时事件适配器 — 注册/监听/响应传感器事件和定时任务

支持：
  - 传感器阈值事件（雷达检测到障碍、温度超标等）
  - 定时事件（X 分钟后提醒）
  - 推送事件（外部系统触发的通知）
"""

from adapters.base_adapter import BaseAdapter, AdapterResult
import time
import threading
from collections import defaultdict

class EventAdapter(BaseAdapter):
    """
    即时事件适配器

    工具:
      - event_register:   注册一个事件监听器
      - event_list:       列出所有已注册事件
      - event_trigger:    手动触发一个事件
      - event_unregister: 注销事件监听器
    """

    # 事件存储
    _events = {}  # {event_id: {type, condition, callback_info, active, triggered_count, last_triggered}}
    _event_counter = 0
    _lock = threading.Lock()

    def tool_definitions(self):
        return [
            {
                "name": "event_register",
                "description": "注册一个事件监听器（传感器阈值/定时/推送）",
                "inputSchema": {
                    "type": "object",
                    "required": ["event_type", "name"],
                    "properties": {
                        "event_type": {"type": "string", "enum": ["sensor_threshold", "timer", "push"]},
                        "name": {"type": "string", "description": "事件名称"},
                        "condition": {"type": "object", "description": "触发条件"},
                        "response_action": {"type": "string", "description": "触发后执行的动作描述"},
                    },
                },
            },
            {
                "name": "event_list",
                "description": "列出所有已注册的事件",
                "inputSchema": {"type": "object"},
            },
            {
                "name": "event_trigger",
                "description": "手动触发一个事件（测试用）",
                "inputSchema": {
                    "type": "object",
                    "required": ["event_id"],
                    "properties": {
                        "event_id": {"type": "string"},
                        "payload": {"type": "object"},
                    },
                },
            },
            {
                "name": "event_unregister",
                "description": "注销一个事件监听器",
                "inputSchema": {
                    "type": "object",
                    "required": ["event_id"],
                    "properties": {"event_id": {"type": "string"}},
                },
            },
        ]

    def handle_tool(self, tool_name, arguments):
        if tool_name == "event_register":
            return self._register(arguments)
        elif tool_name == "event_list":
            return self._list_events()
        elif tool_name == "event_trigger":
            return self._trigger(arguments)
        elif tool_name == "event_unregister":
            return self._unregister(arguments)
        return AdapterResult(False, message=f"未知工具: {tool_name}")

    def _register(self, args):
        event_type = args.get("event_type", "timer")
        name = args.get("name", "unnamed_event")
        condition = args.get("condition", {})
        response_action = args.get("response_action", "通知用户")

        with self._lock:
            EventAdapter._event_counter += 1
            event_id = f"evt_{self._event_counter:04d}"

            event = {
                "id": event_id,
                "type": event_type,
                "name": name,
                "condition": condition,
                "response_action": response_action,
                "active": True,
                "created_at": time.time(),
                "triggered_count": 0,
                "last_triggered": None,
            }

            # 定时器特殊处理
            if event_type == "timer":
                delay_s = condition.get("delay_s", 60)
                event["fire_at"] = time.time() + delay_s

            self._events[event_id] = event

        type_names = {
            "sensor_threshold": "传感器阈值",
            "timer": "定时器",
            "push": "推送监听",
        }

        return AdapterResult(
            True,
            data={"event_id": event_id, "event": event},
            message=f"事件已注册 [{type_names.get(event_type, event_type)}]: {name} (ID: {event_id})",
        )

    def _list_events(self):
        events = []
        for eid, event in self._events.items():
            events.append({
                "id": eid,
                "name": event["name"],
                "type": event["type"],
                "active": event["active"],
                "triggered_count": event["triggered_count"],
            })

        active_count = sum(1 for e in self._events.values() if e["active"])

        return AdapterResult(
            True,
            data={"events": events, "total": len(events), "active": active_count},
            message=f"共 {len(events)} 个事件 ({active_count} 个活跃)",
        )

    def _trigger(self, args):
        event_id = args.get("event_id", "")
        payload = args.get("payload", {})

        with self._lock:
            event = self._events.get(event_id)
            if not event:
                return AdapterResult(False, message=f"事件不存在: {event_id}")

            event["triggered_count"] += 1
            event["last_triggered"] = time.time()

        response = event["response_action"]
        return AdapterResult(
            True,
            data={
                "event_id": event_id,
                "event_name": event["name"],
                "triggered_count": event["triggered_count"],
                "response_action": response,
                "payload": payload,
            },
            message=f"⚡ 事件触发: {event['name']} → 执行: {response}",
        )

    def _unregister(self, args):
        event_id = args.get("event_id", "")

        with self._lock:
            event = self._events.pop(event_id, None)

        if not event:
            return AdapterResult(False, message=f"事件不存在: {event_id}")

        return AdapterResult(
            True,
            data={"removed_id": event_id, "name": event["name"]},
            message=f"事件已注销: {event['name']}",
        )
