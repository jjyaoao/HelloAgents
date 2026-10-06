"""旅行供应链中断：实体抽取、Leiden 社区、局部追查及全局综合。

默认预设抽取/生成响应，真实执行其余索引与检索流程；--live 才调用真实 LLM。
所有供应商、规则和事件均为虚构演练资料，不代表实际旅行建议。
"""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import load_dotenv

from hello_agents import HelloAgentsLLM
from hello_agents.retrieval import (
    RAGStore,
    GraphRAGIndex,
    GraphConfig,
    HelloAgentsGraphModel,
    IndexStaleError,
)


DOCUMENTS = [
    (
        "transport-contract",
        "星河文旅委托运达客运为湖畔营地提供接驳服务。接驳停运会影响湖畔营地的团队抵达。",
        [("星河文旅", "委托", "运达客运"), ("运达客运", "服务", "湖畔营地")],
    ),
    (
        "power-dependency",
        "运达客运的电动接驳车辆依赖滨江充电站。滨江充电站停电会导致运达客运的电动接驳停运。",
        [("运达客运", "依赖", "滨江充电站")],
    ),
    (
        "power-incident",
        "滨江充电站因设备故障停电，恢复时间尚未确认。运达客运已暂停湖畔营地接驳。",
        [("滨江充电站", "导致停运", "运达客运"), ("运达客运", "暂停接驳", "湖畔营地")],
    ),
    (
        "transport-backup",
        "新桥公交可为湖畔营地提供备用接驳，但每天最多接送二十人且必须提前预约。星河文旅需要先核对人数和预约余量。",
        [
            ("新桥公交", "有条件替代", "运达客运"),
            ("新桥公交", "服务", "湖畔营地"),
            ("星河文旅", "核对预约", "新桥公交"),
        ],
    ),
    (
        "hotel-contract",
        "西湖酒店的团队早餐由青禾餐饮配送。西湖酒店不得把无法确认供餐的套餐售为包含早餐。",
        [("西湖酒店", "依赖供餐", "青禾餐饮")],
    ),
    (
        "food-dependency",
        "青禾餐饮依赖江南冷链仓库保存团队早餐食材。江南冷链仓库停用会影响青禾餐饮向西湖酒店供餐。",
        [("青禾餐饮", "依赖", "江南冷链仓库"), ("青禾餐饮", "供应", "西湖酒店")],
    ),
    (
        "food-incident",
        "江南冷链仓库因检修暂停使用。青禾餐饮尚未确认替代仓库，西湖酒店已暂停承诺团队早餐。",
        [
            ("江南冷链仓库", "影响供应", "青禾餐饮"),
            ("青禾餐饮", "影响早餐", "西湖酒店"),
        ],
    ),
    (
        "food-backup",
        "松林餐厅可替代西湖酒店的部分早餐安排，但不能保证无花生交叉接触。花生过敏旅客需要另行核对餐饮方案。",
        [("松林餐厅", "有条件替代", "青禾餐饮"), ("松林餐厅", "提供备选", "西湖酒店")],
    ),
]

# The backup documents do not literally mention the original provider. Remove
# those implicit edges from scripted extraction instead of inventing evidence.
DOCUMENTS = [
    (key, text, [edge for edge in edges if edge[0] in text and edge[2] in text])
    for key, text, edges in DOCUMENTS
]
NAMES = {
    name
    for _, _, edges in DOCUMENTS
    for source, _, target in edges
    for name in (source, target)
}
NAMES |= {"新桥公交", "松林餐厅"}
QUESTION = "目前有哪些中断会沿供应依赖影响旅行服务？分别有哪些已知限制，为什么备用方案不能直接视为问题已经解决？"


class FixtureGraphModel:
    """Scripted model substitute: no semantic extraction or LLM reasoning is claimed."""

    model_id = "travel-supply-graph-fixture-v1"

    def __init__(self):
        self.calls = Counter()

    def generate(self, stage, payload, **kwargs):
        self.calls[stage] += 1
        if stage == "extract":
            text = payload["content"]
            names = sorted(name for name in NAMES if name in text)
            entities = [
                {
                    "key": name,
                    "name": name,
                    "kind": "organization",
                    "scope": "杭州演练",
                    "aliases": [],
                    "description": name + "参与旅行供应链。",
                    "quote": text,
                }
                for name in names
            ]
            edges = next(
                (edges for _, original, edges in DOCUMENTS if original == text), []
            )
            return {
                "entities": entities,
                "relations": [
                    {
                        "source": a,
                        "target": b,
                        "predicate": predicate,
                        "description": text,
                        "quote": text,
                    }
                    for a, predicate, b in edges
                ],
            }
        if stage == "report":
            return {
                "title": "旅行供应链演练社区",
                "claims": [
                    {"text": item["quote"], "citations": [item["id"]]}
                    for item in payload["evidence"]
                ],
            }
        if stage == "map":
            return {
                "claims": (
                    [] if "外星" in payload["question"] else payload["report"]["claims"]
                )
            }
        merged = {}
        for claim in payload["claims"]:
            merged.setdefault(claim["text"], set()).update(claim["citations"])
        return {
            "claims": [
                {"text": text, "citations": sorted(ids)} for text, ids in merged.items()
            ]
        }


def main():
    load_dotenv(Path.cwd() / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--levels", type=int, default=2)
    parser.add_argument("--max-output-tokens", type=int, default=3000)
    args = parser.parse_args()
    if args.live:
        required = [
            key
            for key in ("LLM_MODEL_ID", "LLM_API_KEY", "LLM_BASE_URL")
            if not os.getenv(key)
        ]
        if required:
            parser.error("请设置 " + ", ".join(required))
        model = HelloAgentsGraphModel(
            HelloAgentsLLM(),
            call_kwargs=json.loads(os.getenv("GRAPH_LLM_KWARGS", "{}")),
        )
        mode = "real-llm"
    else:
        model, mode = FixtureGraphModel(), "scripted-model-real-leiden"
        print(
            "离线模式：抽取与生成使用预设响应；Leiden、SQLite、版本检查和引用验证均实际运行。"
        )
    with TemporaryDirectory(prefix="helloagents-graph-") as temporary:
        root = args.workspace or Path(temporary)
        root.mkdir(parents=True, exist_ok=True)
        store = RAGStore(str(root / "documents.sqlite"))
        for key, text, _ in DOCUMENTS:
            store.add_document(text, "fixture://travel-supply/" + key, document_id=key)
        index = GraphRAGIndex(
            store,
            str(root / "graph.sqlite"),
            model,
            config=GraphConfig(
                levels=args.levels, max_output_tokens=args.max_output_tokens
            ),
        )
        built = index.build()
        repeated = index.build()
        local = index.local_search("滨江充电站停电会影响哪些服务？", 5)
        answer = index.global_search(QUESTION)
        baseline = store.search(QUESTION, limit=3)
        labeled_documents = {
            "power-dependency",
            "power-incident",
            "transport-backup",
            "food-dependency",
            "food-incident",
            "food-backup",
        }
        baseline_documents = {item.document_id for item in baseline}
        cited_documents = {item["document_id"] for item in answer.citations}
        report = {
            "mode": mode,
            "fixture_notice": "虚构旅行供应链演练；引用校验不等于语义事实核验",
            "build": built.to_dict(),
            "repeated_build_reused": repeated.reused_generation,
            "local": [item.to_dict() for item in local],
            "local_diagnostics": index.last_local_diagnostics,
            "global": answer.to_dict(),
            "evidence_comparison": {
                "labeled_documents": sorted(labeled_documents),
                "bm25_top3_documents": sorted(baseline_documents),
                "global_cited_documents": sorted(cited_documents),
                "bm25_top3_evidence_recall": len(baseline_documents & labeled_documents)
                / len(labeled_documents),
                "global_cited_evidence_recall": len(cited_documents & labeled_documents)
                / len(labeled_documents),
                "note": "同一小型演练的证据覆盖诊断；两种路径的调用量和成本不同，不是公平性能基准",
            },
        }
        output = json.dumps(report, ensure_ascii=False, indent=2)
        if args.workspace:
            (root / "graphrag-report.json").write_text(output, encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
