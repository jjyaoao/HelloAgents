"""
LLM Judge 评估工具

使用方式：
    from hello_agents.tools.builtin import LLMJudgeEvaluationTool
    from hello_agents.evaluation.benchmarks.data_generation_Universal import UniversalDataset

    # 1. 加载数据集（json为例）
    # 本地数据
    dataset = UniversalDataset(
        source_type="local",
        source_config={"path": "data.json"}
    )

    # 2. 创建评估器
    evaluator = LLMJudgeEvaluationTool(template="math")

    # 3. 运行评估
    results = evaluator.evaluate(data, max_samples=10)

    # 4. 导出结果
    evaluator.export_report(results, output_dir="results")
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from hello_agents.evaluation.benchmarks.data_generation_Universal import (
    EvaluationConfig,
    LLMJudgeEvaluator as BaseLLMJudgeEvaluator,
    UniversalDataset,
)
from hello_agents.core.llm import HelloAgentsLLM


# 保留 LLMJudgeDataset 用于向后兼容（已过时，内部使用 UniversalDataset）
class LLMJudgeDataset:
    """LLM Judge 数据集加载器（已过时，推荐使用 UniversalDataset）

    此类仅保留以保证向后兼容性，内部已转换为使用 UniversalDataset。
    新代码应直接使用 UniversalDataset。
    """

    def __init__(
        self,
        data_path: str,
        format: str = "auto",
        field_mapping: Optional[Dict[str, str]] = None
    ):
        """
        初始化数据集加载器

        Args:
            data_path: 数据文件路径
            format: 数据格式 ("json", "csv" 或 "auto")
            field_mapping: 字段映射 {标准字段 -> 源字段}

        Deprecated:
            使用 UniversalDataset 替代：
            dataset = UniversalDataset(
                source_config={"path": data_path, "format": "auto"},
                field_mapping=field_mapping
            )
        """
        # 使用 UniversalDataset 替代原实现
        self._universal_dataset = UniversalDataset(
            source_config={"path": data_path, "format": format},
            field_mapping=field_mapping
        )
        self._data = None

    def load(self) -> List[Dict[str, Any]]:
        """
        加载数据

        Returns:
            数据列表
        """
        self._data = self._universal_dataset.load()
        return self._data

    def __len__(self) -> int:
        """获取数据集大小"""
        if self._data is None:
            self.load()
        return len(self._data)


class LLMJudgeEvaluationTool:
    """LLM Judge 评估工具 - 通用版本

    支持多种数据源和评估模板的高级评估工具。
    """

    def __init__(
        self,
        template: str = "math",
        llm: HelloAgentsLLM = None,
        field_mapping: Optional[Dict[str, str]] = None
    ):
        """
        初始化评估工具

        Args:
            template: 评估模板 ("math" / "code" / "writing" / "qa")
            llm: LLM实例（必需，应由调用者创建）
            field_mapping: 字段映射
        """
        if llm is None:
            raise ValueError("llm参数不能为空，请传入HelloAgentsLLM实例")
        self.template = template
        self.llm = llm
        self.field_mapping = field_mapping or {"problem": "problem", "answer": "answer"}
        self.eval_config = EvaluationConfig.load_template(template)
        self.results = None

    def evaluate(self, data: List[Dict[str, Any]], max_samples: int = 0) -> Dict[str, Any]:
        """
        运行评估

        Args:
            data: 数据列表
            max_samples: 最多评估样本数 (0=全部)

        Returns:
            评估结果
        """
        # 限制样本数
        data_to_evaluate = data[:max_samples] if max_samples > 0 else data

        # 创建评估器
        evaluator = BaseLLMJudgeEvaluator(
            llm=self.llm,
            eval_config=self.eval_config,
            field_mapping=self.field_mapping
        )

        # 运行评估
        self.results = evaluator.evaluate_batch(data_to_evaluate)
        return self.results

    def run(self, params: Dict[str, Any]) -> str:
        """
        Run complete evaluation workflow (high-level interface - local data only)

        Args:
            params: Parameter dictionary containing:
                - source_config: Data source config (required)
                  {"path": "path/to/data.json"}
                - field_mapping: Field mapping for data (optional)
                  {"problem": "question", "answer": "answer"}
                - reference_config: Reference data config (optional for comparison)
                  {"path": "path/to/reference.json"}
                - reference_field_mapping: Field mapping for reference data (optional)
                - template: Evaluation template (optional, overrides init template)
                - max_samples: Max samples to evaluate (optional, default: 0 = all)
                - output_dir: Output directory (optional, default: "evaluation_results")
                - judge_model: Judge model (optional, overrides init model)

        Returns:
            JSON string with evaluation results
        """
        import os
        from datetime import datetime

        # Parse parameters
        source_config = params.get("source_config")
        field_mapping = params.get("field_mapping", self.field_mapping)

        reference_config = params.get("reference_config")
        reference_field_mapping = params.get("reference_field_mapping", {})

        template = params.get("template", self.template)
        max_samples = params.get("max_samples", 0)
        output_dir = params.get("output_dir", "evaluation_results")

        # Validate required parameters
        if not source_config or "path" not in source_config:
            raise ValueError("source_config must contain 'path' key")

        # Add timestamp to output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(output_dir, f"llm_judge_{timestamp}")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        print("\n" + "="*70)
        print("🎯 LLM Judge 评估")
        print("="*70)

        # Step 1: Load evaluation data
        print(f"\n📥 步骤 1: 加载评估数据")
        print(f"   Source: {source_config['path']}")
        dataset = UniversalDataset(
            source_config=source_config,
            field_mapping=field_mapping
        )
        data = dataset.load()

        # Step 2: Load reference data (optional)
        ref_data = None
        if reference_config and "path" in reference_config:
            print(f"\n📥 步骤 2: 加载参考数据")
            print(f"   Source: {reference_config['path']}")
            reference_dataset = UniversalDataset(
                source_config=reference_config,
                field_mapping=reference_field_mapping
            )
            ref_data = reference_dataset.load()

        # Step 3: Configure evaluator
        print(f"\n⚙️  步骤 3: 配置评估器")
        self.template = template
        self.field_mapping = field_mapping
        self.eval_config = EvaluationConfig.load_template(template)
        print(f"   Template: {template}")
        print(f"   Judge Model: {self.llm.model}")

        # Step 4: Run evaluation
        print(f"\n🚀 步骤 4: 开始评估")
        results = self.evaluate(data, max_samples=max_samples)
        print(f"   ✓ 评估完成")

        # Step 5: Export report
        print(f"\n💾 步骤 5: 导出评估报告")
        report_path = self.export_report(results, output_dir=output_dir)
        print(f"   ✓ 报告已保存: {report_path}")

        print("\n" + "="*70)
        print("✅ LLM Judge 评估完成")
        print("="*70)

        # Return results
        return json.dumps({
            "status": "success",
            "template": template,
            "judge_model": self.llm.model,
            "num_samples": len(data),
            "metrics": results.get("metrics", {}),
            "output_dir": output_dir
        }, ensure_ascii=False, indent=2)

    def export_report(self, results: Optional[Dict[str, Any]] = None, output_dir: str = "evaluation_results") -> str:
        """
        导出评估报告

        Args:
            results: 评估结果 (使用最后一次evaluate的结果)
            output_dir: 输出目录

        Returns:
            报告文件路径
        """
        if results is None:
            results = self.results

        if results is None:
            raise ValueError("没有评估结果，请先运行 evaluate() 方法")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        metrics = results.get("metrics", {})

        # 生成Markdown报告
        report_lines = [
            "# LLM Judge 评估报告\n\n",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"**评估模板**: {self.template}\n",
            f"**评估样本数**: {len(results.get('results', []))}\n\n",
            "## 总体评分\n\n",
            f"- <strong>平均总分</strong>: {metrics.get('average_total_score', 0):.2f}/5.0\n",
            f"- <strong>通过率</strong>: {metrics.get('pass_rate', 0):.1%} (≥3.5分)\n",
            f"- <strong>优秀率</strong>: {metrics.get('excellent_rate', 0):.1%} (≥4.5分)\n\n",
            "## 各维度评分\n\n",
        ]

        # 生成维度评分表格
        dimension_averages = metrics.get("dimension_averages", {})
        if dimension_averages:
            report_lines.append("| 维度 | 平均分 | 评级 |\n")
            report_lines.append("|------|--------|------|\n")

            for dim, score in dimension_averages.items():
                # 根据分数生成评级
                if score >= 4.5:
                    rating = "优秀 ⭐⭐⭐⭐⭐"
                elif score >= 4.0:
                    rating = "良好 ⭐⭐⭐⭐"
                elif score >= 3.5:
                    rating = "中等 ⭐⭐⭐"
                elif score >= 3.0:
                    rating = "及格 ⭐⭐"
                else:
                    rating = "待改进 ⭐"

                report_lines.append(f"| {dim} | {score:.2f}/5.0 | {rating} |\n")

            report_lines.append("\n")

        # 保存Markdown报告
        report_path = output_path / "llm_judge_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.writelines(report_lines)

        # 保存JSON结果
        results_file = output_path / "llm_judge_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        return str(report_path)

    def get_available_templates(self) -> List[str]:
        """获取所有可用模板"""
        return EvaluationConfig.get_available_templates()
