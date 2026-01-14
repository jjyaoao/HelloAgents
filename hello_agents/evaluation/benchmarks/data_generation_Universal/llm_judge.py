"""
LLM Judge Evaluator

使用LLM作为评委评估数据生成质量，支持自定义维度和字段映射
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import EvaluationConfig


class UniversalLLMJudgeEvaluator:
    """LLM Judge评估器 - 支持自定义维度"""

    def __init__(
        self,
        llm: Optional[HelloAgentsLLM] = None,
        judge_model: str = "gpt-4o",
        eval_config: Optional[EvaluationConfig] = None,
        field_mapping: Optional[Dict[str, str]] = None,
        data_format: str = "standard"
    ):
        """
        初始化LLM Judge评估器

        Args:
            llm: LLM实例，如果为None则创建新实例
            judge_model: 评委模型名称
            eval_config: 评估配置，默认使用标准4个维度
            field_mapping: 字段映射（如{"problem": "题目"}）
            data_format: 数据格式类型（"standard", "csv", "custom"）
        """
        self.llm = llm or HelloAgentsLLM(model=judge_model)
        self.judge_model = judge_model
        self.eval_config = eval_config or EvaluationConfig()
        self.field_mapping = field_mapping
        self.data_format = data_format
        
    def evaluate_single(
        self,
        problem: Dict[str, Any],
        reference: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """评估单个问题"""
        # 适配字段
        problem = self._adapt_fields(problem)
        if reference:
            reference = self._adapt_fields(reference)

        start_time = time.time()

        # 构建评估提示词（支持自定义维度）
        prompt = self._build_evaluation_prompt(problem, reference)

        # 调用LLM进行评估
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages)

        # 解析评估结果
        scores = self._parse_evaluation_response(response)

        # 计算总分
        total_score = sum(scores.values()) / len(scores) if scores else 0.0

        execution_time = time.time() - start_time

        return {
            "problem_id": problem.get("id", "unknown"),
            "scores": scores,
            "total_score": total_score,
            "evaluation_text": response,
            "execution_time": execution_time
        }
    
    def evaluate_batch(
        self,
        problems: List[Dict[str, Any]],
        references: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """批量评估问题"""
        print(f"\n🎯 开始LLM Judge评估")
        print(f"   评估维度: {', '.join(self.eval_config.get_dimension_names())}")
        print(f"   评估数量: {len(problems)}")

        results = []
        for idx, problem in enumerate(problems):
            print(f"\n   评估进度: {idx + 1}/{len(problems)}")

            # 提取问题ID并移除维度信息（如将 writing-accuracy-001 转换为 writing-001）
            problem_id = problem.get('id', 'unknown')
            display_id = self._extract_display_id(problem_id)
            print(f"   📊 {display_id}:")

            reference = references[idx] if references and idx < len(references) else None
            result = self.evaluate_single(problem, reference)
            results.append(result)

            # 显示各维度的评分
            max_scale = self.eval_config.dimensions[0].scale if self.eval_config.dimensions else 5
            for dimension_name, score in result['scores'].items():
                print(f"      • {dimension_name}: {score:.2f}/{max_scale}")

            # 显示平均分
            print(f"      ➜ 平均分: {result['total_score']:.2f}/{max_scale}")

        # 计算统计信息
        metrics = self._compute_metrics(results)

        return {
            "results": results,
            "metrics": metrics,
            "evaluation_date": datetime.now().isoformat(),
            "judge_model": self.judge_model,
            "dimensions": self.eval_config.get_dimension_names(),
            "num_problems": len(problems)
        }
    
    def _build_evaluation_prompt(
        self,
        problem: Dict[str, Any],
        reference: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建评估提示词（支持自定义维度）

        动态生成提示词，包含所有自定义维度
        """
        # 构建主要内容
        prompt = f"""请评估以下内容的质量。

题目：
{problem.get('problem', '')}

答案：
{problem.get('answer', '')}
"""

        if problem.get('solution'):
            prompt += f"\n解答：\n{problem.get('solution', '')}\n"

        if reference:
            prompt += f"""
【参考内容】
题目：
{reference.get('problem', '')}

答案：
{reference.get('answer', '')}
"""
            if reference.get('solution'):
                prompt += f"\n解答：\n{reference.get('solution', '')}\n"

        # 动态生成评估维度说明
        prompt += "\n请从以下维度进行评分（每个维度1-5分）：\n\n"

        # 构建维度列表，使用 <strong> 标记强调维度名称
        for idx, dimension in enumerate(self.eval_config.dimensions, 1):
            prompt += f"{idx}. <strong>{dimension.name}</strong>：{dimension.description}\n"

        # 生成JSON格式说明
        dimension_names = self.eval_config.get_dimension_names()
        json_template = {name: 5 for name in dimension_names}
        json_template["comments"] = "评价理由"

        prompt += f"\n请按以下JSON格式输出评分：\n```json\n{json.dumps(json_template, ensure_ascii=False, indent=4)}\n```"

        return prompt
    
    def _parse_evaluation_response(self, response: str) -> Dict[str, float]:
        """解析LLM评估响应"""
        try:
            # 提取JSON部分
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            data = json.loads(json_str)

            # 提取评分（仅提取维度分数，忽略comments等）
            scores = {}
            dimension_names = self.eval_config.get_dimension_names()

            for dim_name in dimension_names:
                scores[dim_name] = float(data.get(dim_name, 3.0))

            return scores

        except Exception as e:
            print(f"⚠️ 解析评估响应失败: {e}")
            # 返回默认评分
            return {dim: 3.0 for dim in self.eval_config.get_dimension_names()}
    
    def _compute_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算评估指标"""
        if not results:
            return {}

        # 计算各维度平均分
        dimension_names = self.eval_config.get_dimension_names()
        dimension_scores = {dim: [] for dim in dimension_names}
        total_scores = []

        for result in results:
            total_scores.append(result["total_score"])
            for dim in dimension_names:
                if dim in result["scores"]:
                    dimension_scores[dim].append(result["scores"][dim])

        metrics = {
            "average_total_score": sum(total_scores) / len(total_scores),
            "dimension_averages": {
                dim: sum(scores) / len(scores)
                for dim, scores in dimension_scores.items()
                if scores
            },
            "pass_rate": sum(1 for s in total_scores if s >= 3.5) / len(total_scores),
            "excellent_rate": sum(1 for s in total_scores if s >= 4.5) / len(total_scores)
        }

        return metrics

    def _adapt_fields(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """适配字段（如果提供了field_mapping）"""
        if not self.field_mapping:
            return problem

        adapted = {}
        for standard_key, source_key in self.field_mapping.items():
            if source_key in problem:
                adapted[standard_key] = problem[source_key]

        # 保留其他字段
        for key, value in problem.items():
            if key not in self.field_mapping.values():
                adapted[key] = value

        # 确保基本字段存在
        for key in ["id", "problem", "answer"]:
            if key not in adapted and key in problem:
                adapted[key] = problem[key]

        return adapted

    def _extract_display_id(self, problem_id: str) -> str:
        """
        从问题ID中提取显示用的ID，移除维度信息
        例如：writing-accuracy-001 -> writing-001
        """
        parts = problem_id.split('-')
        if len(parts) >= 2:
            # 如果是 writing-accuracy-001 这样的格式
            if parts[-1].isdigit():  # 最后一部分是数字
                # 检查中间部分是否是维度名（通常是单个单词）
                if len(parts) >= 3 and parts[1] in ['accuracy', 'coherence', 'creativity', 'engagement', 'clarity', 'completeness']:
                    # 移除维度部分，保留 writing-001
                    return f"{parts[0]}-{parts[-1]}"
        return problem_id

    def export_results(
        self,
        results: Dict[str, Any],
        output_path: str
    ):
        """导出评估结果"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 评估结果已保存: {output_path}")

