"""Client test cho versioned_server.py — gọi cả tool v1, v2 và đọc server metadata."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def text_result(result: object) -> str:
    if getattr(result, "isError", False):
        raise RuntimeError("MCP server trả về lỗi khi gọi tool")
    parts = [item.text for item in result.content if item.type == "text"]
    if not parts:
        raise RuntimeError("MCP server không trả về nội dung dạng text")
    return "\n".join(parts)


async def main() -> None:
    server_path = Path(__file__).with_name("versioned_server.py").resolve()
    params = StdioServerParameters(command=sys.executable, args=[str(server_path)])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Đọc server metadata
            info = await session.read_resource("server://info")
            if not info.contents or not hasattr(info.contents[0], "text"):
                raise RuntimeError("Resource server://info không chứa text")
            meta = json.loads(info.contents[0].text)
            print(f"Server: {meta['name']} v{meta['version']}")
            print(f"Deprecated tools: {meta['deprecated_tools']}")
            print(f"Migration: {meta['migration_guide']}\n")

            # 2. Liệt kê tools
            tools = await session.list_tools()
            print("Tools:")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")
            print()

            # 3. Gọi tool v1 (deprecated nhưng vẫn hoạt động)
            r1 = await session.call_tool("get_weather", {"city": "Hanoi"})
            print(f"[v1] get_weather('Hanoi'):\n  {text_result(r1)}\n")

            # 4. Gọi tool v2
            r2 = await session.call_tool("get_weather_v2", {
                "city": "Hanoi",
                "include_forecast": True,
                "units": "celsius",
            })
            print(f"[v2] get_weather_v2('Hanoi', forecast=True):")
            print(f"  {json.dumps(json.loads(text_result(r2)), indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    configure_console()
    asyncio.run(main())
