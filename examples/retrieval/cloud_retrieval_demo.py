"""Qdrant Cloud：一个账号完成文档和记忆检索，不下载嵌入模型。"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from hello_agents.memory import MemoryStore, SemanticMemorySearch
from hello_agents.retrieval import RAGStore, QdrantSearch, QdrantCloudInference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace", type=Path, default=Path("workspace/cloud-retrieval")
    )
    args = parser.parse_args()
    load_dotenv(Path.cwd() / ".env", override=False)
    url, key = os.getenv("QDRANT_URL", ""), os.getenv("QDRANT_API_KEY", "")
    if not url or not key or "your-" in url or "your_" in key:
        parser.error(
            "请先在 .env 配置 QDRANT_URL 和 QDRANT_API_KEY；注册步骤见 docs/cloud-retrieval-guide.md"
        )
    model = os.getenv("QDRANT_EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    try:
        dimension = int(os.getenv("QDRANT_EMBEDDING_DIMENSION", "384"))
        inference = QdrantCloudInference(model=model, dimension=dimension)
    except ValueError as exc:
        parser.error(f"云端嵌入配置有误：{exc}")
    collection = os.getenv("QDRANT_COLLECTION", "hello_agents_cloud")
    connection = dict(url=url, api_key=key, collection=collection)
    args.workspace.mkdir(parents=True, exist_ok=True)

    documents = RAGStore(str(args.workspace / "documents.sqlite"))
    documents.add_document(
        "旅行规则示例：持续下雨时，将湖边步行改成室内博物馆；出发前查询预约情况。",
        source="example:rain-plan",
        document_id="rain-plan",
        version="1",
    )
    with QdrantSearch(documents, inference, **connection) as search:
        print("文档索引新增编码：", search.sync())
        for hit in search.search("下雨了，可以改成什么室内活动？", limit=1):
            print("资料：", hit.content, "来源：", hit.source)

    memories = MemoryStore(
        str(args.workspace / "memory.sqlite"), user_id="demo-user", task_id="travel"
    )
    if not memories.search("", limit=1):
        memories.add(
            "膝盖恢复期间，每天步行不超过五公里。",
            "example:user-preference",
            kind="preference",
        )
    with SemanticMemorySearch(
        memories, inference, hybrid=False, **connection
    ) as recall:
        print("记忆索引新增编码：", recall.sync())
        for record in recall.search("规划行程时，徒步强度有什么限制？", limit=1):
            print("记忆：", record.content, "来源：", record.source)
    print("完成。再次运行相同 workspace 可复用已同步的索引。")


if __name__ == "__main__":
    main()
