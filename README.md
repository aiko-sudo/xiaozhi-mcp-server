# XiaoZhi Peripheral MCP — 模拟原型

基于 Python 和 MCP 的外设适配器模拟服务，提供语音、雷达、摄像头、眼球、表情、导航和事件共 22 个模拟工具。

> **WIP：仅可用于模拟，不得用于真机控制或判断实际障碍物安全。** 注册器默认使用 mock，真实串口和 HTTP 后端因尚未通过安全验收而禁用。返回中的 `backend=mock`、`simulated=true` 表示数据和动作均为模拟。设备断连不得静默替换为模拟数据。

## 使用

需要 Python 3.10+；MCP stdio 模式需要安装 `mcp`，测试另需 `pytest`、`pyserial` 和 `requests`。实际依赖授权以各依赖项目为准。

```sh
python3 tests/test_adapters.py
python3 -m pytest -q tests/test_fail_closed.py
python3 src/mcp_server.py --list-tools
python3 src/mcp_server.py --mock
```

最后一条运行 MCP stdio 服务，需由 MCP 客户端启动；模拟结果不可用于真实决策。命令行示例：

```sh
python3 src/mcp_server.py --cli --tool radar_scan --args '{"range_m":5}'
```

## 验证范围

适配器测试、失败关闭回归和 MCP 客户端 stdio 握手/模拟调用已验证；未完成真实硬件、小智服务端、ROS2 或外网设备联调，不保证安全控制。

本项目为独立实验原型，与小智项目及相关厂商无官方关联。许可证见 [LICENSE](LICENSE)。
