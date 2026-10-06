"""保守的 Python 空白清理，不重排 import、不重写缩进。

运行 python -m examples.tools.custom_tools.code_formatter_tool。保留字符串原文，
检查处理前后 AST 相同。它不是 Black/Ruff 的替代品，也不执行用户代码。
"""

import ast
import io
import tokenize
from hello_agents.tools import Tool, ToolParameter, ToolResponse


class CodeFormatterTool(Tool):
    def __init__(self):
        super().__init__(
            "code_formatter", "清理 Python 非字符串行末空白，报告长行；不重排导入和缩进"
        )

    def get_parameters(self):
        return [
            ToolParameter(name="code", type="string", description="完整 Python 源码"),
            ToolParameter(
                name="max_line_length",
                type="integer",
                description="报告超长行的阈值，不截断代码",
                required=False,
                default=88,
                json_schema={"type": "integer", "minimum": 1},
            ),
        ]

    def run(self, parameters):
        if not isinstance(parameters, dict) or set(parameters) - {
            "code",
            "max_line_length",
        }:
            return ToolResponse.error(
                "INVALID_PARAM", "仅接受 code 和 max_line_length 参数"
            )
        code = parameters.get("code")
        width = parameters.get("max_line_length", 88)
        if (
            not isinstance(code, str)
            or not code.strip()
            or type(width) is not int
            or width < 1
        ):
            return ToolResponse.error(
                "INVALID_PARAM", "code 必须是非空字符串，max_line_length 必须为正整数"
            )
        try:
            before = ast.parse(code, type_comments=True)
            protected = set()
            for token in tokenize.generate_tokens(io.StringIO(code).readline):
                kind = tokenize.tok_name[token.type]
                if (
                    kind == "STRING"
                    or kind.startswith("FSTRING")
                    or kind.startswith("TSTRING")
                ):
                    protected.update(range(token.start[0], token.end[0] + 1))
            lines = code.splitlines(keepends=True)
            cleaned = []
            for number, line in enumerate(lines, 1):
                if number in protected:
                    cleaned.append(line)
                    continue
                ending = (
                    "\r\n"
                    if line.endswith("\r\n")
                    else "\n" if line.endswith("\n") else ""
                )
                body = line[: -len(ending)] if ending else line
                cleaned.append(body.rstrip(" \t") + ending)
            result = "".join(cleaned)
            if not result.endswith("\n"):
                result += "\n"
            after = ast.parse(result, type_comments=True)
            if ast.dump(before, include_attributes=False) != ast.dump(
                after, include_attributes=False
            ):
                return ToolResponse.error(
                    "INVALID_FORMAT", "处理会改变语法树，已拒绝返回修改结果"
                )
        except (SyntaxError, tokenize.TokenError, ValueError) as error:
            return ToolResponse.error("INVALID_FORMAT", f"源码无法解析：{error}")
        return ToolResponse.success(
            "空白检查完成",
            data={
                "formatted_code": result,
                "changed": result != code,
                "long_lines": [
                    i
                    for i, line in enumerate(result.splitlines(), 1)
                    if len(line) > width
                ],
            },
        )


def main():
    source = "def locate():\n  import os\n  return os.getcwd()  \n"
    reply = CodeFormatterTool().run({"code": source})
    assert reply.data["formatted_code"] == source.rstrip() + "\n"
    print(reply.to_json())


if __name__ == "__main__":
    main()
