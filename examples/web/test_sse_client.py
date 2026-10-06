"""先启动 SSE 服务，再运行 python -m examples.web.test_sse_client；无需 requests。"""

import json
from urllib.request import Request, urlopen


def main():
    request = Request(
        "http://127.0.0.1:8000/agent/stream",
        data=json.dumps({"input": "你好", "agent_type": "simple"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    finished = False
    with urlopen(request, timeout=120) as stream:
        for raw in stream:
            line = raw.decode("utf-8").strip()
            if line.startswith("data:"):
                event = json.loads(line[5:])
                print(event)
                if event["type"] == "error":
                    raise RuntimeError(event["data"])
                finished |= event["type"] == "agent_finish"
    assert finished, "连接关闭前未收到完成事件"


if __name__ == "__main__":
    main()
