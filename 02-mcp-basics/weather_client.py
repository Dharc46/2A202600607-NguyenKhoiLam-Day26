"""MCP CLIENT minh hoạ — kết nối tới weather_server.py qua giao thức MCP.

Điểm mấu chốt: client KHÔNG hard-code tool. Nó hỏi server "anh có tool gì?"
(list_tools) tại runtime, rồi gọi tool (call_tool) để SERVER thực thi và trả
kết quả về qua MCP.

Ví dụ này không cần ANTHROPIC_API_KEY — nó cho thấy lớp giao thức MCP hoạt
động độc lập với model. (Trong thực tế, một LLM sẽ dùng Function Calling để
quyết định khi nào gọi tool đã khám phá được.)

Cách chạy (cùng thư mục với weather_server.py, client tự khởi động server):
    pip install -r ../requirements.txt
    python weather_client.py
"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def configure_console() -> None:
    """Cho phép in tiếng Việt ổn định trên console Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


async def main() -> None:
    # Dùng đúng interpreter đang chạy client (tránh lỗi "python" không tồn tại)
    server_path = Path(__file__).with_name("weather_server.py").resolve()
    params = StdioServerParameters(command=sys.executable, args=[str(server_path)])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. KHÁM PHÁ tool mà server công bố (không hard-code)
            tools = await session.list_tools()
            print("Tools server cung cấp:")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")

            # 2. Gọi tool — SERVER thực thi rồi trả kết quả về qua MCP
            for city in ["Hanoi", "Danang", "Haiphong"]:
                result = await session.call_tool("get_weather", {"city": city})
                print(f"\ncall_tool get_weather(city={city!r}):")
                if result.isError:
                    raise RuntimeError(f"get_weather thất bại với city={city!r}")

                text_parts = [
                    item.text for item in result.content if item.type == "text"
                ]
                if not text_parts:
                    raise RuntimeError("Server không trả về nội dung dạng text")
                print("  ->", "\n".join(text_parts))


if __name__ == "__main__":
    configure_console()
    asyncio.run(main())
