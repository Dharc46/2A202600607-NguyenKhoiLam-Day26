"""Minh hoạ FUNCTION CALLING thuần với Google Gemini SDK.

Tool `get_weather` được định nghĩa schema thủ công VÀ thực thi ngay trong
chính file app này. Model chỉ QUYẾT ĐỊNH gọi tool nào; app mới là nơi chạy.

Cách chạy:
    pip install -r ../requirements.txt
    export GEMINI_API_KEY=...
    python weather_function_calling.py
"""

import json
import os
from typing import Any

from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"
MAX_TOOL_ROUNDS = 8

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp (🌧️ 🌤️ 💨 💧). "
    "Tóm tắt ngắn gọn, dễ hiểu, và đưa ra lời khuyên thực tế "
    "(ví dụ: mang ô, mặc áo mỏng, ...)."
)

# 1. App tự định nghĩa schema của tool
get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Lấy thời tiết hiện tại của một thành phố",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING, description="Tên thành phố"
            )
        },
        required=["city"],
    ),
)

TOOLS = [types.Tool(function_declarations=[get_weather_declaration])]


# 2. App tự thực thi tool (trong thực tế sẽ gọi API thời tiết thật)
def get_weather(city: str) -> str:
    """Trả về thời tiết (mock) của *city*. Dùng làm tool cho model."""
    mock_data = {
        "Hà Nội": {
            "nhiệt_độ": "29°C",
            "thời_tiết": "trời mưa nhẹ",
            "độ_ẩm": "82%",
            "gió": {"hướng": "Đông Nam", "tốc_độ": "12 km/h"},
        },
        "Hồ Chí Minh": {
            "nhiệt_độ": "33°C",
            "thời_tiết": "mưa rào",
            "độ_ẩm": "75%",
            "gió": {"hướng": "Tây Nam", "tốc_độ": "15 km/h"},
        },
        "Đà Nẵng": {
            "nhiệt_độ": "30°C",
            "thời_tiết": "nhiều mây",
            "độ_ẩm": "78%",
            "gió": {"hướng": "Đông", "tốc_độ": "10 km/h"},
        },
    }
    default = {"nhiệt_độ": "28°C", "thời_tiết": "không có dữ liệu chi tiết"}
    return json.dumps({"city": city, **mock_data.get(city, default)}, ensure_ascii=False)


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Chỉ thực thi các tool mà app đã đăng ký rõ ràng."""
    if name != "get_weather":
        raise ValueError(f"Tool không được hỗ trợ: {name}")

    city = arguments.get("city")
    if not isinstance(city, str) or not city.strip():
        raise ValueError("get_weather yêu cầu `city` là một chuỗi không rỗng")
    return get_weather(city.strip())


def run(prompt: str, client: genai.Client | None = None) -> str:
    """Gửi *prompt* tới Gemini, tự động xử lý function calling và trả về câu trả lời cuối."""
    if not prompt.strip():
        raise ValueError("Prompt không được để trống")

    # Khởi tạo ở thời điểm chạy để file vẫn có thể được import/test mà chưa cần API key.
    client = client or genai.Client()
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]

    # 3. Gọi model — model quyết định có gọi tool hay không
    resp = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            tools=TOOLS,
            system_instruction=SYSTEM_INSTRUCTION,
        ),
    )

    # 4. Vòng lặp: nếu model yêu cầu tool, app TỰ THỰC THI rồi đưa kết quả trả lại
    tool_round = 0
    while resp.function_calls:
        tool_round += 1
        if tool_round > MAX_TOOL_ROUNDS:
            raise RuntimeError("Model yêu cầu quá nhiều vòng gọi tool")

        # Thêm phản hồi của model vào lịch sử hội thoại
        if not resp.candidates or resp.candidates[0].content is None:
            raise RuntimeError("Gemini không trả về nội dung function call hợp lệ")
        contents.append(resp.candidates[0].content)

        function_responses = []
        for fc in resp.function_calls:
            print(f"  [model yêu cầu] {fc.name}({fc.args})")
            result = execute_tool(fc.name, dict(fc.args or {}))
            print(f"  [app thực thi]  -> {result}")
            function_responses.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )

        # Gửi kết quả tool trả về cho model
        contents.append(types.Content(role="user", parts=function_responses))
        resp = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                tools=TOOLS,
                system_instruction=SYSTEM_INSTRUCTION,
            ),
        )

    # 5. Model tổng hợp câu trả lời cuối
    if not resp.text:
        raise RuntimeError("Gemini không trả về câu trả lời cuối")
    return resp.text


if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("Thiếu GEMINI_API_KEY. Hãy thiết lập biến môi trường trước khi chạy.")
    question = "Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"
    print(f"User: {question}\n")
    print("Trả lời:", run(question))
