"""中英混排的轻量词项切分；用于关键词检索，不是语义分词模型。"""

import re
from typing import List


def lexical_terms(text: str) -> List[str]:
    """英文/数字按词切分，汉字使用单字及相邻双字，保留无空格文本的重叠。"""
    terms = []
    for part in re.findall(r"[\u3400-\u9fff]+|[a-z0-9_]+", text.lower()):
        if re.fullmatch(r"[\u3400-\u9fff]+", part):
            terms.extend(part)
            terms.extend(part[i : i + 2] for i in range(len(part) - 1))
        else:
            terms.append(part)
    return terms


def count_tokens(text: str) -> int:
    """本地估算 token 数；不保证与具体模型或服务端计数一致。"""
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Unicode 字符数作为保守的教学估算，仍非服务端精确值。
        return max(1, len(text)) if text else 0
