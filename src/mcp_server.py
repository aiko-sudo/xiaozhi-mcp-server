#!/usr/bin/env python3
"""
XiaoZhi MCP Server — 小智 AI 智能外设管理中间件

MCP Server 主程序，提供 7 大类外设管理工具。
支持 stdio 传输（标准 MCP 协议）和 CLI 直接调用两种模式。

用法:
  # MCP stdio 模式（对接小智 Server / Hermes / Claude Desktop）
  python mcp_server.py

  # Mock 模式（无硬件测试）
  python mcp_server.py --mock

  # CLI 模式（直接调用工具）
  python mcp_server.py --cli --tool radar_scan --args '{"range_m":5}'

  # 列出所有工具
  python mcp_server.py --list-tools
"""

import sys
import os
import json
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tool_registry import ToolRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("xiaozhi-mcp")


def run_cli(registry: ToolRegistry, tool_name: str, args_json: str):
    """CLI 模式：直接调用工具"""
    try:
        arguments = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError:
        arguments = {}

    result = registry.call_tool(tool_name, arguments)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def run_list_tools(registry: ToolRegistry):
    """列出所有工具"""
    tools = registry.list_tools()
    print(f"\n{'='*60}")
    print(f"XiaoZhi MCP Server — 共 {len(tools)} 个工具")
    print(f"{'='*60}\n")

    # 按适配器分组
    from collections import defaultdict
    groups = defaultdict(list)
    for tool in tools:
        # 从工具名前缀推断分组
        prefix = tool["name"].split("_")[0]
        groups[prefix].append(tool)

    group_names = {
        "voice": "🗣 语音指令",
        "radar": "📡 雷达数据",
        "camera": "📷 摄像头",
        "eye": "👁 眼球控制",
        "emotion": "😊 表情管理",
        "nav": "🗺 导航规划",
        "event": "⚡ 即时事件",
    }

    for prefix, name in group_names.items():
        if prefix in groups:
            print(f"\n{'─'*40}")
            print(f"  {name}")
            print(f"{'─'*40}")
            for tool in groups[prefix]:
                desc = tool["description"]
                req = tool["inputSchema"].get("required", [])
                print(f"  • {tool['name']}({', '.join(req)})")
                print(f"    {desc}")

    print(f"\n{'='*60}")
    print(f"适配器状态:")
    for name, status in registry.get_status().items():
        backend = status.get("backend", "?")
        connected = "✅" if status.get("connected") else "❌"
        print(f"  {connected} {name}: {backend}")
    print()


def run_mcp_stdio(registry: ToolRegistry):
    """MCP stdio 传输模式"""
    logger.info("启动 MCP stdio 服务器...")

    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
        import asyncio

        app = Server("xiaozhi-mcp")

        @app.list_tools()
        async def list_tools():
            tools = []
            for td in registry.list_tools():
                tools.append(Tool(
                    name=td["name"],
                    description=td["description"],
                    inputSchema=td["inputSchema"],
                ))
            logger.info(f"列出 {len(tools)} 个工具")
            return tools

        @app.call_tool()
        async def call_tool(name, arguments):
            logger.info(f"工具调用: {name}({arguments})")
            result = registry.call_tool(name, dict(arguments))
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        async def main():
            async with stdio_server() as (r, w):
                await app.run(r, w, app.create_initialization_options())

        asyncio.run(main())

    except ImportError:
        logger.error("mcp 包未安装。请运行: pip install mcp")
        logger.error("或使用 CLI 模式: python mcp_server.py --cli --tool <tool_name>")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="XiaoZhi MCP Server")
    parser.add_argument("--mock", action="store_true", help="Mock 模式（无硬件）")
    parser.add_argument("--backend", default="mock", choices=["mock", "serial", "http"], help="通信后端")
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--cli", action="store_true", help="CLI 模式（直接调用工具）")
    parser.add_argument("--tool", default=None, help="CLI 模式：工具名")
    parser.add_argument("--args", default="{}", help="CLI 模式：参数 JSON")
    parser.add_argument("--list-tools", action="store_true", help="列出所有工具")
    parser.add_argument("--status", action="store_true", help="显示适配器状态")
    args = parser.parse_args()

    # 加载配置
    config = {}
    if args.config:
        import yaml
        with open(args.config) as f:
            config = yaml.safe_load(f) or {}

    backend = "mock" if args.mock else args.backend

    # 初始化工具注册器
    registry = ToolRegistry(backend=backend, config=config)
    logger.info(f"工具注册器初始化完成: {registry.adapter_count} 适配器, {registry.tool_count} 工具, backend={backend}")

    if args.list_tools:
        run_list_tools(registry)
        return

    if args.status:
        print(json.dumps(registry.get_status(), ensure_ascii=False, indent=2))
        return

    if args.cli:
        if not args.tool:
            print("错误: CLI 模式需要 --tool 参数")
            sys.exit(1)
        run_cli(registry, args.tool, args.args)
        return

    # 默认: MCP stdio 模式
    run_mcp_stdio(registry)


if __name__ == "__main__":
    main()
