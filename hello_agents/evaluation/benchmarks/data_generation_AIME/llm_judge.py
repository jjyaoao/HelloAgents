"""
LLM Judge Evaluator

使用LLM作为评委评估数据生成质量
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from hello_agents.core.llm import HelloAgentsLLM


class LLMJudgeEvaluator:
    """LLM Judge评估器"""
    
    # 评估维度
    EVALUATION_DIMENSIONS = [
        "correctness",      # 正确性
        "clarity",          # 清晰度
        "difficulty_match", # 难度匹配
        "completeness"      # 完整性
    ]
    
    def __init__(
        self,
        llm: Optional[HelloAgentsLLM] = None,
        judge_model: str = "gpt-4o"
    ):
        """
        初始化LLM Judge评估器
        
        Args:
            llm: LLM实例，如果为None则创建新实例
            judge_model: 评委模型名称
        """
        self.llm = llm or HelloAgentsLLM(model=judge_model)
        self.judge_model = judge_model
        
    def evaluate_single(
        self,
        problem: Dict[str, Any],
        reference: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        评估单个问题
        
        Args:
            problem: 待评估的问题
            reference: 参考问题（可选，用于对比）
        
        Returns:
            评估结果，包含各维度评分和总分
        """
        start_time = time.time()
        
        # 构建评估提示词
        prompt = self._build_evaluation_prompt(problem, reference)

        # 调用LLM进行评估
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages)
        
        # 解析评估结果
        scores = self._parse_evaluation_response(response)
        
        # 计算总分
        total_score = sum(scores.values()) / len(scores)
        
        execution_time = time.time() - start_time
        
        return {
            "problem_id": problem.get("problem_id", "unknown"),
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
        """
        批量评估问题
        
        Args:
            problems: 待评估的问题列表
            references: 参考问题列表（可选）
        
        Returns:
            评估结果汇总
        """
        print(f"\n🎯 开始LLM Judge评估")
        print(f"   评委模型: {self.judge_model}")
        print(f"   评估数量: {len(problems)}")
        print(f"   评估维度: {', '.join(self.EVALUATION_DIMENSIONS)}")
        
        results = []
        for idx, problem in enumerate(problems):
            print(f"\n   评估进度: {idx + 1}/{len(problems)}")
            
            reference = references[idx] if references and idx < len(references) else None
            result = self.evaluate_single(problem, reference)
            results.append(result)
            
            # 显示评分
            print(f"   ✓ {problem.get('problem_id', 'unknown')}: {result['total_score']:.2f}/5.0")
        
        # 计算统计信息
        metrics = self._compute_metrics(results)
        
        return {
            "results": results,
            "metrics": metrics,
            "evaluation_date": datetime.now().isoformat(),
            "judge_model": self.judge_model,
            "num_problems": len(problems)
        }
    
    def _build_evaluation_prompt(
        self,
        problem: Dict[str, Any],
        reference: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建评估提示词"""
        prompt = f"""你是一位专业的数学题目评估专家。请评估以下AIME风格数学题目的质量。

【待评估题目】
问题: {problem.get('problem', '')}
答案: {problem.get('answer', '')}
解答: {problem.get('solution', '')}
"""
        
        if reference:
            prompt += f"""
【参考题目（AIME真题）】
问题: {reference.get('problem', '')}
答案: {reference.get('answer', '')}
解答: {reference.get('solution', '')}
"""
        
        prompt += """
请从以下四个维度评估题目质量（每个维度1-5分）：

1. **正确性 (Correctness)**: 数学逻辑是否正确，答案是否准确
2. **清晰度 (Clarity)**: 问题表述是否清晰，解答是否易懂
3. **难度匹配 (Difficulty Match)**: 难度是否符合AIME标准（6-9/15）
4. **完整性 (Completeness)**: 解答步骤是否完整，是否包含必要的推理

请按以下JSON格式输出评分：
```json
{
    "correctness": 5,
    "clarity": 4,
    "difficulty_match": 4,
    "completeness": 5,
    "comments": "详细评价..."
}
```
"""
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
            
            # 解析JSON
            data = json.loads(json_str)
            
            # 提取评分
            scores = {}
            for dim in self.EVALUATION_DIMENSIONS:
                scores[dim] = float(data.get(dim, 3.0))  # 默认3分
            
            return scores
            
        except Exception as e:
            print(f"⚠️ 解析评估响应失败: {e}")
            # 返回默认评分
            return {dim: 3.0 for dim in self.EVALUATION_DIMENSIONS}
    
    def _compute_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算评估指标"""
        if not results:
            return {}
        
        # 计算各维度平均分
        dimension_scores = {dim: [] for dim in self.EVALUATION_DIMENSIONS}
        total_scores = []
        
        for result in results:
            total_scores.append(result["total_score"])
            for dim in self.EVALUATION_DIMENSIONS:
                dimension_scores[dim].append(result["scores"][dim])
        
        metrics = {
            "average_total_score": sum(total_scores) / len(total_scores),
            "dimension_averages": {
                dim: sum(scores) / len(scores)
                for dim, scores in dimension_scores.items()
            },
            "pass_rate": sum(1 for s in total_scores if s >= 3.5) / len(total_scores),
            "excellent_rate": sum(1 for s in total_scores if s >= 4.5) / len(total_scores)
        }
        
        return metrics
    
    def export_results(
        self,
        results: Dict[str, Any],
        output_path: str
    ):
        """导出评估结果"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 评估结果已保存: {output_path}")

