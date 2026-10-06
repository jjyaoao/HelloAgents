"""真实向量检索与版本更新实验；需要显式选择嵌入模型。

使用虚构的旅行服务规则评估关键词、向量与混合召回，不代表真实景区政策。
FastEmbed 首次运行会下载模型；OpenAI 兼容接口从 EMBEDDING_* 环境变量配置。
"""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import load_dotenv

from hello_agents.retrieval import (
    RAGStore,
    QdrantSearch,
    HybridSearch,
    FastEmbedProvider,
    OpenAIEmbeddingProvider,
    IndexStaleError,
)


DOCUMENTS = {
    "rain": "雨天安排：当预报有持续降水时，将湖边步行替换为室内博物馆。室内展馆需要提前预约，预约满额时选择有顶棚的历史街区。",
    "access": "无障碍路线：同行者无法长时间站立时，优先提供电梯、平坦路面与可休息的座椅。避开台阶、山路及长距离换乘。",
    "refund": "订单退改：活动开始前一天十八点前取消可全额退款，超过期限收取百分之二十手续费。供应商主动取消时，不受该期限限制。",
    "diet": "餐饮要求：花生过敏者需明确告知餐厅，询问配料及共用器具情况。仅删除菜名中的花生不能保证避免交叉接触。",
    "invoice": "报销凭证：发票抬头与税号必须来自单位确认的信息。预约确认短信和支付截图不能替代正式发票。",
    "bag": "行李寄存：游客可在服务台寄存拉杆箱，凭寄存凭证领取。贵重物品及身份证件应随身携带，不放入寄存行李。",
    "photo": "展厅摄影：常设展允许非商业用途拍照，禁止闪光灯和三脚架。临时展览的禁拍标识优先于常设展规则。",
    "traffic": "公共交通：安排地铁为主、公交为辅的路线。末班车前预留三十分钟进站；无法赶上末班车时提供出租车备选费用。",
}

QUESTIONS = [
    ("天气不好不能在外面逛，有什么备选？", "rain"),
    ("带着腿脚不便的长辈，线路怎么选？", "access"),
    ("商家不办活动了，我还能拿回全部钱吗？", "refund"),
    ("对坚果中的花生有过敏反应，点餐要注意什么？", "diet"),
    ("单位财务需要的正式票据怎么开？", "invoice"),
    ("退房后拖着箱子不方便，可以放在哪里？", "bag"),
]


def evaluate(backends):
    report = {}
    for name, backend in backends.items():
        hits_at_one, reciprocal, traces = 0, 0.0, []
        for query, expected in QUESTIONS:
            ids = [result.document_id for result in backend.search(query, 3)]
            rank = ids.index(expected) + 1 if expected in ids else None
            hits_at_one += rank == 1
            reciprocal += 1 / rank if rank else 0
            traces.append({"query": query, "expected": expected, "retrieved": ids})
        report[name] = {
            "recall_at_1": hits_at_one / len(QUESTIONS),
            "mrr_at_3": reciprocal / len(QUESTIONS),
            "queries": traces,
        }
    return report


def main():
    load_dotenv(Path.cwd() / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider", choices=["fastembed", "openai"], default="fastembed"
    )
    parser.add_argument("--model", default=os.getenv("EMBEDDING_MODEL"))
    parser.add_argument(
        "--dimension", type=int, default=os.getenv("EMBEDDING_DIMENSION")
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--cache-dir")
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()
    if not args.model or not args.dimension:
        parser.error("请通过 --model 和 --dimension 明确选择嵌入模型及维度")
    client = None
    if args.provider == "openai":
        from openai import OpenAI

        required = ("EMBEDDING_API_KEY", "EMBEDDING_BASE_URL")
        if any(not os.getenv(key) for key in required):
            parser.error("OpenAI 兼容服务需要 EMBEDDING_API_KEY 和 EMBEDDING_BASE_URL")
        client = OpenAI(
            api_key=os.environ["EMBEDDING_API_KEY"],
            base_url=os.environ["EMBEDDING_BASE_URL"],
        )
        embedding = OpenAIEmbeddingProvider(client, args.model, args.dimension)
    else:
        embedding = FastEmbedProvider(
            args.model,
            args.dimension,
            cache_dir=args.cache_dir,
            local_files_only=args.local_files_only,
        )
    try:
        with TemporaryDirectory(prefix="helloagents-rag-") as temporary:
            root = args.workspace or Path(temporary)
            root.mkdir(parents=True, exist_ok=True)
            store = RAGStore(str(root / "documents.db"))
            # 重复运行同一 workspace 也重新建立基线，并保留旧版本供回读。
            baseline_version = f"run-{store.revision + 1}"
            for key, content in DOCUMENTS.items():
                store.add_document(
                    content,
                    f"fixture://travel-rules/{key}",
                    document_id=key,
                    version=baseline_version,
                )
            # 每种 embedding 配置使用独立集合；切换模型可在此选择新集合。
            with QdrantSearch(store, embedding, path=str(root / "qdrant")) as dense:
                dense.sync()
                hybrid = HybridSearch([store, dense])
                report = {
                    "fixture_notice": "虚构旅行规则的小型标注实验；不代表通用检索质量",
                    "embedding": embedding.model_id,
                    "evaluation": evaluate(
                        {"bm25": store, "dense": dense, "hybrid": hybrid}
                    ),
                }
                store.add_document(
                    "雨天安排：持续降水时优先参观室内历史展馆；须先核对预约余量。",
                    "fixture://travel-rules/rain",
                    version=f"{baseline_version}-updated",
                    document_id="rain",
                )
                try:
                    dense.search("雨天怎么办")
                except IndexStaleError:
                    report["stale_index_rejected"] = True
                else:
                    raise AssertionError("资料更新后旧向量索引应被拒绝")
                dense.sync()
                report["updated_evidence"] = [
                    item.to_dict() for item in dense.search("雨天怎么办", 3)
                ]
                output = json.dumps(report, ensure_ascii=False, indent=2)
                if args.workspace:
                    (root / "retrieval-report.json").write_text(
                        output, encoding="utf-8"
                    )
                print(output)
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()
