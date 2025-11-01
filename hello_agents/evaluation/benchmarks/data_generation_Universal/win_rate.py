"""
Win Rate Evaluator

通过成对对比计算胜率，支持自定义维度和字段映射
"""

import json
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import EvaluationConfig


class UniversalWinRateEvaluator:
    """Win Rate评估器 - 支持自定义维度"""

    def __init__(
        self,
        llm: Optional[HelloAgentsLLM] = None,
        judge_model: str = "gpt-4o",
        eval_config: Optional[EvaluationConfig] = None,
        field_mapping: Optional[Dict[str, str]] = None
    ):
        """
        初始化Win Rate评估器

        Args:
            llm: LLM实例
            judge_model: 评委模型名称
            eval_config: 评估配置，支持自定义维度
            field_mapping: 字段映射
        """
        self.llm = llm or HelloAgentsLLM(model=judge_model)
        self.judge_model = judge_model
        self.eval_config = eval_config or EvaluationConfig()
        self.field_mapping = field_mapping
        
    def compare_pair(
        self,
        problem_a: Dict[str, Any],
        problem_b: Dict[str, Any],
        label_a: str = "A",
        label_b: str = "B"
    ) -> Dict[str, Any]:
        """对比两个问题，判断哪个更好"""
        # 适配字段
        problem_a = self._adapt_fields(problem_a)
        problem_b = self._adapt_fields(problem_b)

        start_time = time.time()

        # 构建对比提示词（支持自定义维度）
        prompt = self._build_comparison_prompt(problem_a, problem_b, label_a, label_b)

        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages)

        winner, reason = self._parse_comparison_response(response, label_a, label_b)

        execution_time = time.time() - start_time

        return {
            "problem_a_id": problem_a.get("id", "unknown"),
            "problem_b_id": problem_b.get("id", "unknown"),
            "winner": winner,
            "reason": reason,
            "comparison_text": response,
            "execution_time": execution_time
        }
    
    def evaluate_win_rate(
        self,
        generated_problems: List[Dict[str, Any]],
        reference_problems: List[Dict[str, Any]],
        num_comparisons: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        评估生成数据相对于参考数据的胜率
        
        Args:
            generated_problems: 生成的问题列表
            reference_problems: 参考问题列表（如AIME真题）
            num_comparisons: 对比次数，如果为None则对比所有可能的配对
        
        Returns:
            胜率评估结果
        """
        print(f"\n🏆 开始Win Rate评估")
        print(f"   评委模型: {self.judge_model}")
        print(f"   评估维度: {', '.join(self.eval_config.get_dimension_names())}")
        print(f"   生成数据: {len(generated_problems)} 个")
        print(f"   参考数据: {len(reference_problems)} 个")

        # 确定对比次数
        if num_comparisons is None:
            num_comparisons = min(len(generated_problems), len(reference_problems))

        # 限制对比次数不超过生成题目数量
        num_comparisons = min(num_comparisons, len(generated_problems))

        print(f"   对比次数: {num_comparisons}")

        gen_indices = random.sample(range(len(generated_problems)), num_comparisons)

        print(f"   采样方式: 随机采样")

        # 进行成对对比
        comparisons = []
        wins = 0
        losses = 0
        ties = 0

        for i, gen_idx in enumerate(gen_indices):
            gen_problem = generated_problems[gen_idx]
            # 随机选择一个参考题目
            ref_idx = random.randint(0, len(reference_problems) - 1)
            ref_problem = reference_problems[ref_idx]

            print(f"\n   对比进度: {i + 1}/{num_comparisons}")
            print(f"   生成题目: #{gen_idx + 1}, 参考题目: #{ref_idx + 1}")

            # 随机化题目顺序以避免位置偏向
            if random.random() < 0.5:
                # Generated在前
                result = self.compare_pair(
                    gen_problem,
                    ref_problem,
                    label_a="Problem A",
                    label_b="Problem B"
                )
                # 记录实际顺序
                result["actual_order"] = {"A": "Generated", "B": "Reference"}

                # 转换winner
                if result["winner"] == "Problem A":
                    actual_winner = "Generated"
                elif result["winner"] == "Problem B":
                    actual_winner = "Reference"
                else:
                    actual_winner = "Tie"
            else:
                # Reference在前
                result = self.compare_pair(
                    ref_problem,
                    gen_problem,
                    label_a="Problem A",
                    label_b="Problem B"
                )
                # 记录实际顺序
                result["actual_order"] = {"A": "Reference", "B": "Generated"}

                # 转换winner
                if result["winner"] == "Problem A":
                    actual_winner = "Reference"
                elif result["winner"] == "Problem B":
                    actual_winner = "Generated"
                else:
                    actual_winner = "Tie"

            result["actual_winner"] = actual_winner
            comparisons.append(result)

            # 统计胜负
            if actual_winner == "Generated":
                wins += 1
                print(f"   ✓ Generated胜出")
            elif actual_winner == "Reference":
                losses += 1
                print(f"   ✗ Reference胜出")
            else:
                ties += 1
                print(f"   = 平局")
        
        # 计算胜率
        win_rate = wins / num_comparisons if num_comparisons > 0 else 0
        loss_rate = losses / num_comparisons if num_comparisons > 0 else 0
        tie_rate = ties / num_comparisons if num_comparisons > 0 else 0
        
        metrics = {
            "win_rate": win_rate,
            "loss_rate": loss_rate,
            "tie_rate": tie_rate,
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "total_comparisons": num_comparisons
        }
        
        print(f"\n📊 Win Rate评估结果:")
        print(f"   胜率: {win_rate:.2%}")
        print(f"   败率: {loss_rate:.2%}")
        print(f"   平局率: {tie_rate:.2%}")
        
        return {
            "comparisons": comparisons,
            "metrics": metrics,
            "evaluation_date": datetime.now().isoformat(),
            "judge_model": self.judge_model,
            "dimensions": self.eval_config.get_dimension_names()
        }
    
    def _build_comparison_prompt(
        self,
        problem_a: Dict[str, Any],
        problem_b: Dict[str, Any],
        label_a: str,
        label_b: str
    ) -> str:
        """构建对比提示词（支持自定义维度）"""
        has_solution_a = bool(problem_a.get('solution', '').strip())
        has_solution_b = bool(problem_b.get('solution', '').strip())

        # 构建题目A的文本
        problem_a_text = f"【题目{label_a}】\n"
        problem_a_text += f"问题：{problem_a.get('problem', '')}\n"
        problem_a_text += f"答案：{problem_a.get('answer', '')}"
        if has_solution_a:
            problem_a_text += f"\n解答：{problem_a.get('solution', '')}"

        # 构建题目B的文本
        problem_b_text = f"【题目{label_b}】\n"
        problem_b_text += f"问题：{problem_b.get('problem', '')}\n"
        problem_b_text += f"答案：{problem_b.get('answer', '')}"
        if has_solution_b:
            problem_b_text += f"\n解答：{problem_b.get('solution', '')}"

        # 动态生成维度说明（按自定义维度顺序）
        dimension_list = "\n".join([
            f"{idx}. {dim.name}：{dim.description}"
            for idx, dim in enumerate(self.eval_config.dimensions, 1)
        ])

        prompt = f"""请比较以下两个内容的质量，判断哪个更好。

{problem_a_text}

{problem_b_text}

请从以下方面进行比较：
{dimension_list}

比较要求：
1. 全面分析两个内容在各维度上的差异
2. 对每个维度都要给出具体的对比意见
3. 综合所有维度的表现做出最终判断
4. 只有在两个内容在所有或大多数维度都相当时，才选择"Tie"
5. 提供详细的理由，具体说明差异之处

输出格式（必须是以下JSON格式）：
```json
{{
    "winner": "A" 或 "B" 或 "Tie",
    "reason": "详细的比较分析，说明各维度的差异和最终判断理由"
}}
```

重要：winner字段必须是以下三个之一：A、B 或 Tie
"""
        return prompt
    
    def _parse_comparison_response(
        self,
        response: str,
        label_a: str,
        label_b: str
    ) -> Tuple[str, str]:
        """解析对比响应"""
        try:
            # 提取JSON部分
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            # 修复LaTeX转义问题
            import re
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # 修复LaTeX转义：将 \frac 转为 \\frac
                fixed_json_str = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', json_str)
                data = json.loads(fixed_json_str)

            winner = data.get("winner", "").strip()
            reason = data.get("reason", "No reason provided")

            # 规范化winner值：处理 A/B/Tie 映射到实际的label
            if winner == "A":
                winner = label_a
            elif winner == "B":
                winner = label_b
            elif winner == "Tie":
                winner = "Tie"
            else:
                # 如果返回的是label本身，保留它
                if winner not in [label_a, label_b]:
                    # 无效的winner，默认为Tie
                    winner = "Tie"

            return winner, reason

        except Exception as e:
            print(f"⚠️ 解析对比响应失败: {e}")
            return "Tie", "Failed to parse response"
    
    def _adapt_fields(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """适配字段"""
        if not self.field_mapping:
            return problem

        adapted = {}
        for standard_key, source_key in self.field_mapping.items():
            if source_key in problem:
                adapted[standard_key] = problem[source_key]

        for key, value in problem.items():
            if key not in self.field_mapping.values():
                adapted[key] = value

        for key in ["id", "problem", "answer"]:
            if key not in adapted and key in problem:
                adapted[key] = problem[key]

        return adapted

    def export_results(
        self,
        results: Dict[str, Any],
        output_path: str
    ):
        """导出评估结果"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Win Rate结果已保存: {output_path}")

