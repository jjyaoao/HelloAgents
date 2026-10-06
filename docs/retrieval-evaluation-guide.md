# 检索评测与模型重排

先用标注问题比较关键词、向量和混合检索，再决定是否增加重排或图检索。评测采用真实片段 ID，避免把来源正确但证据错误的命中算成成功。

```python
from hello_agents.retrieval.evaluation import evaluate_retrieval

cases = [{"query": "行程取消如何处理？",
          "relevance": {"实际退改条款片段 ID": 3, "实际补充说明片段 ID": 1}}]
report = evaluate_retrieval(backend, cases, k=5)
print(report["mean"])
```

每个问题保存排序结果和耗时。Recall@k 衡量相关片段召回比例；MRR@k 取第一个相关命中的倒数排名；nDCG@k 使用 0 至 10 的分级相关性。没有正相关标注的问题返回 `None`，不混入均值，也不假装得分为 0 或 1。重复候选 ID 会报错。

这些指标不衡量生成答案的正确性。还应人工检查答案中的主张是否被引用证据支持、是否遗漏例外；真实实验另行记录模型 token 和耗时。不要把一组微型演示题的结果称作通用质量保证。

## 添加真实模型重排

```python
from hello_agents.retrieval.pipeline import RetrievalPipeline
from hello_agents.retrieval.rerank import LLMReranker

pipeline = RetrievalPipeline(backend, LLMReranker(llm), candidate_limit=10)
results = pipeline.search("行程取消如何处理？", limit=5)
```

`LLMReranker` 通过正常 LLM 接口请求候选索引的排列，保留原始证据对象，不允许增删或重写内容。非 JSON、缺失索引、重复索引和截断响应均报错；超出输入上限时应降低候选量。它需要真实模型、会增加调用成本，也可能让排序变差，应与不重排的结果在同一组标注问题上比较。使用 `RunBudget` 可以把重排纳入任务计量。
