"""
XiaoZhi MCP Server 单元测试

测试 7 大适配器的核心功能 + 工具注册器路由。
全部使用 mock 后端，无需硬件。
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tool_registry import ToolRegistry
from adapters.voice_adapter import VoiceAdapter
from adapters.radar_adapter import RadarAdapter
from adapters.camera_adapter import CameraAdapter
from adapters.eye_adapter import EyeAdapter
from adapters.emotion_adapter import EmotionAdapter
from adapters.navigation_adapter import NavigationAdapter
from adapters.event_adapter import EventAdapter


# ============================================================
# 1. 工具注册器
# ============================================================

def test_registry():
    """测试工具注册器初始化"""
    print("Test 1: 工具注册器...")
    registry = ToolRegistry(backend="mock")

    # 应有 7 个适配器
    assert registry.adapter_count == 7, f"适配器数: {registry.adapter_count}"
    print(f"  ✅ 适配器: {registry.adapter_count}")

    # 应有多个工具
    tools = registry.list_tools()
    assert len(tools) >= 20, f"工具数: {len(tools)}"
    print(f"  ✅ 工具数: {len(tools)}")

    # 全部适配器应已连接
    status = registry.get_status()
    for name, s in status.items():
        assert s["connected"], f"适配器 {name} 未连接"
    print(f"  ✅ 全部 {len(status)} 个适配器已连接")

    return registry


# ============================================================
# 2. 语音适配器
# ============================================================

def test_voice():
    print("Test 2: 语音适配器...")
    adapter = VoiceAdapter(name="voice", backend="mock")

    # 转写
    r = adapter.handle_tool("voice_transcribe", {"audio_ref": "test"})
    assert r.success and "text" in r.data
    print(f"  ✅ STT: '{r.data['text']}'")

    # 意图识别
    r = adapter.handle_tool("voice_intent", {"text": "去厨房"})
    assert r.success and r.data["intent"] == "导航"
    print(f"  ✅ 意图: '{r.data['intent']}' (置信度 {r.data['confidence']})")

    # 意图执行
    r = adapter.handle_tool("voice_execute", {"intent": "观察", "text": "看看桌上有什么"})
    assert r.success and r.data["route_to"] == "camera"
    print(f"  ✅ 路由: 观察 → {r.data['route_to']}")


# ============================================================
# 3. 雷达适配器
# ============================================================

def test_radar():
    print("Test 3: 雷达适配器...")
    adapter = RadarAdapter(name="radar", backend="mock")

    # 扫描
    r = adapter.handle_tool("radar_scan", {"range_m": 5.0})
    assert r.success and "obstacles" in r.data
    print(f"  ✅ 扫描: {r.data['count']} 个障碍物")

    # 安全检查
    r = adapter.handle_tool("radar_check_safe", {"direction": "front", "safe_distance_m": 0.5})
    assert r.success and "is_safe" in r.data
    print(f"  ✅ 前方安全: {'是' if r.data['is_safe'] else '否'} (危险: {r.data['unsafe_count']})")

    # 地图
    r = adapter.handle_tool("radar_get_map", {})
    assert r.success and "points" in r.data
    print(f"  ✅ 地图: {r.data['point_count']} 个点")


# ============================================================
# 4. 摄像头适配器
# ============================================================

def test_camera():
    print("Test 4: 摄像头适配器...")
    adapter = CameraAdapter(name="camera", backend="mock")

    # 拍摄
    r = adapter.handle_tool("camera_capture", {"source": "front"})
    assert r.success and "objects" in r.data
    print(f"  ✅ 拍摄: {r.data['object_count']} 个物体, 场景: {r.data['scene']}")

    # 描述
    r = adapter.handle_tool("camera_describe", {})
    assert r.success and "description" in r.data
    print(f"  ✅ 描述: {r.data['description'][:40]}...")

    # 目标检测（mock 随机，可能找到也可能没找到）
    r = adapter.handle_tool("camera_detect", {"target": "杯子"})
    assert r.success and "found" in r.data
    print(f"  ✅ 检测'杯子': {'找到' if r.data['found'] else '未找到'}")


# ============================================================
# 5. 眼球控制适配器
# ============================================================

def test_eye():
    print("Test 5: 眼球适配器...")
    adapter = EyeAdapter(name="eye", backend="mock")

    # 看向方向
    r = adapter.handle_tool("eye_look", {"direction": "left"})
    assert r.success and r.data["x"] < 0
    print(f"  ✅ 看左: x={r.data['x']}, y={r.data['y']}")

    r = adapter.handle_tool("eye_look", {"direction": "center"})
    assert r.success and r.data["x"] == 0.0
    print(f"  ✅ 居中: x={r.data['x']}, y={r.data['y']}")

    # 自定义坐标
    r = adapter.handle_tool("eye_look", {"direction": "center", "x": 0.5, "y": -0.3})
    assert r.success and r.data["x"] == 0.5
    print(f"  ✅ 自定义: x=0.5, y=-0.3")

    # 动作
    r = adapter.handle_tool("eye_action", {"action": "blink"})
    assert r.success
    print(f"  ✅ 动作: {r.data['action']}")

    # 追踪
    r = adapter.handle_tool("eye_track", {"action": "start", "target": "face"})
    assert r.success and r.data["tracking"] == True
    print(f"  ✅ 追踪: 开始追踪 {r.data['target']}")


# ============================================================
# 6. 表情适配器
# ============================================================

def test_emotion():
    print("Test 6: 表情适配器...")
    adapter = EmotionAdapter(name="emotion", backend="mock")

    # 设置表情
    r = adapter.handle_tool("emotion_set", {"emotion": "happy"})
    assert r.success and r.data["emotion"] == "happy"
    print(f"  ✅ 表情: {r.data['name_cn']} (强度 {r.data['intensity']})")

    # 列出表情
    r = adapter.handle_tool("emotion_list", {})
    assert r.success and len(r.data["emotions"]) == 8
    print(f"  ✅ 表情列表: {len(r.data['emotions'])} 种")

    # 推断情绪
    r = adapter.handle_tool("emotion_infer", {"text": "今天真是太开心了！"})
    assert r.success
    print(f"  ✅ 推断: '{r.data['inferred_emotion']}' → {r.data['name_cn']} (置信度 {r.data['confidence']})")


# ============================================================
# 7. 导航适配器
# ============================================================

def test_navigation():
    print("Test 7: 导航适配器...")
    adapter = NavigationAdapter(name="navigation", backend="mock")

    # 路径规划
    r = adapter.handle_tool("nav_plan", {"destination": "厨房"})
    assert r.success and "steps" in r.data
    print(f"  ✅ 规划: {r.data['estimated_path']} ({r.data['distance_m']}m)")

    # 移动
    r = adapter.handle_tool("nav_move", {"action": "forward", "distance_m": 1.0})
    assert r.success
    print(f"  ✅ 移动: {r.message}")

    # 状态
    r = adapter.handle_tool("nav_status", {})
    assert r.success and "position" in r.data
    print(f"  ✅ 状态: 位置 {r.data['position']}, 朝向 {r.data['heading_deg']}°")

    # 回到原点
    adapter.handle_tool("nav_plan", {"destination": "客厅"})


# ============================================================
# 8. 事件适配器
# ============================================================

def test_event():
    print("Test 8: 事件适配器...")
    adapter = EventAdapter(name="event", backend="mock")

    # 注册事件
    r = adapter.handle_tool("event_register", {
        "event_type": "timer",
        "name": "十分钟提醒",
        "condition": {"delay_s": 600},
        "response_action": "提醒用户喝水",
    })
    assert r.success and "event_id" in r.data
    event_id = r.data["event_id"]
    print(f"  ✅ 注册: {r.data['event']['name']} (ID: {event_id})")

    # 列出事件
    r = adapter.handle_tool("event_list", {})
    assert r.success and r.data["total"] >= 1
    print(f"  ✅ 列表: {r.data['total']} 个事件 ({r.data['active']} 活跃)")

    # 触发事件
    r = adapter.handle_tool("event_trigger", {"event_id": event_id, "payload": {"test": True}})
    assert r.success and r.data["triggered_count"] == 1
    print(f"  ✅ 触发: {r.data['event_name']} → {r.data['response_action']}")

    # 注销事件
    r = adapter.handle_tool("event_unregister", {"event_id": event_id})
    assert r.success
    print(f"  ✅ 注销: {r.message}")


# ============================================================
# 9. 工具注册器端到端
# ============================================================

def test_registry_e2e(registry):
    """通过注册器调用各适配器"""
    print("Test 9: 注册器端到端...")

    # 调用语音工具
    r = registry.call_tool("voice_intent", {"text": "看看前面有什么"})
    assert r["success"] and r["data"]["intent"] == "观察"
    print(f"  ✅ voice_intent → {r['data']['intent']}")

    # 调用雷达工具
    r = registry.call_tool("radar_scan", {"range_m": 3})
    assert r["success"]
    print(f"  ✅ radar_scan → {r['data']['count']} obstacles")

    # 调用未知工具
    r = registry.call_tool("nonexistent_tool", {})
    assert not r["success"]
    print(f"  ✅ 未知工具 → 正确拒绝")

    # 调用表情工具
    r = registry.call_tool("emotion_set", {"emotion": "surprised"})
    assert r["success"]
    print(f"  ✅ emotion_set → {r['data']['name_cn']}")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("XiaoZhi MCP Server — 单元测试")
    print("=" * 60)

    tests = [
        ("工具注册器", test_registry),
        ("语音适配器", test_voice),
        ("雷达适配器", test_radar),
        ("摄像头适配器", test_camera),
        ("眼球适配器", test_eye),
        ("表情适配器", test_emotion),
        ("导航适配器", test_navigation),
        ("事件适配器", test_event),
    ]

    passed = 0
    failed = 0
    registry = None

    for name, test in tests:
        print(f"\n{'─'*40}")
        try:
            if name == "工具注册器":
                registry = test()
            else:
                test()
            passed += 1
        except Exception as e:
            print(f"  ❌ FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # 端到端测试
    print(f"\n{'─'*40}")
    if registry:
        try:
            test_registry_e2e(registry)
            passed += 1
        except Exception as e:
            print(f"  ❌ FAIL: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"结果: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if failed == 0 else 1)
