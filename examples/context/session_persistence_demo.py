"""python -m examples.context.session_persistence_demo [--live]"""

from pathlib import Path
from tempfile import TemporaryDirectory
from hello_agents import SimpleAgent
from examples._support import demo_config, demo_llm, response, ScriptedLLM


def main():
    with TemporaryDirectory() as directory:
        config = demo_config(session_enabled=True, session_dir=directory)
        first = SimpleAgent(
            "旅行助手", demo_llm([response("已记录预算 1500 元。")]), config=config
        )
        print(first.run("我的旅行预算是 1500 元，请记住。"))
        path = first.save_session("travel")
        assert Path(path).is_file()
        llm = demo_llm([response("你的预算是 1500 元。")])
        resumed = SimpleAgent("旅行助手", llm, config=config)
        resumed.load_session(path)
        assert len(resumed.get_history()) == len(first.get_history())
        print(resumed.run("我的预算是多少？"))
        if isinstance(llm, ScriptedLLM):
            assert any(
                "我的旅行预算" in (m.get("content") or "")
                for m in llm.requests[0]["messages"]
            )
        assert resumed.last_run.status == "completed"
        print("新实例已接收上一轮历史；恢复会话数据，不是后台进程。")


if __name__ == "__main__":
    main()
