"""
Win Rate 评估工具

使用方式：
    from hello_agents.tools.builtin import WinRateEvaluationTool
    from hello_agents.evaluation.benchmarks.data_generation_Universal import UniversalDataset

    # 1. 加载数据集（json为例）
    # 本地数据
    generated_dataset = UniversalDataset(
        source_type="local",
        source_config={"path": "generated.json"}
    )

    # 2. 创建评估器
    evaluator = WinRateEvaluationTool(template="math")

    # 3. 运行评估
    results = evaluator.evaluate(generated, reference, num_comparisons=10)

    # 4. 导出结果
    evaluator.export_report(results, output_dir="results")
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional
from datetime import datetime

from hello_agents.evaluation.benchmarks.data_generation_Universal import (
    EvaluationConfig,
    UniversalWinRateEvaluator as BaseWinRateEvaluator,
    UniversalDataset,
)
from hello_agents.core.llm import HelloAgentsLLM


# 保留 UniversalWinRateDataset 用于向后兼容（内部使用 UniversalDataset）
class UniversalWinRateDataset:
    """Win Rate 数据集加载器（推荐使用 UniversalDataset）

    此类仅保留以保证向后兼容性，内部已转换为使用 UniversalDataset。
    新代码应直接使用 UniversalDataset。
    """

    def __init__(
        self,
        generated_path: str,
        reference_path: Optional[str] = None,
        format: str = "custom",
        field_mapping: Optional[Dict[str, str]] = None
    ):
        """
        初始化数据集加载器

        Args:
            generated_path: 生成数据文件路径
            reference_path: 参考数据文件路径 (为None时使用生成数据后一半)
            format: 数据格式（已忽略，改为使用 UniversalDataset 的自动检测）
            field_mapping: 字段映射 {标准字段 -> 源字段}

        Deprecated:
            使用 UniversalDataset 替代：
            generated_dataset = UniversalDataset(
                source_type="local",
                source_config={"path": generated_path},
                field_mapping=field_mapping
            )
            reference_dataset = UniversalDataset(
                source_type="local",
                source_config={"path": reference_path},
                field_mapping=field_mapping
            )
        """
        # 使用 UniversalDataset 替代原实现
        self._generated_dataset = UniversalDataset(
            source_type="local",
            source_config={"path": generated_path},
            field_mapping=field_mapping
        )
        self._reference_path = reference_path
        self._field_mapping = field_mapping
        self.generated_data = None
        self.reference_data = None

    def load(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        加载数据

        Returns:
            (生成数据列表, 参考数据列表)
        """
        # 加载生成数据
        self.generated_data = self._generated_dataset.load()

        # 加载参考数据
        if self._reference_path:
            reference_dataset = UniversalDataset(
                source_type="local",
                source_config={"path": self._reference_path},
                field_mapping=self._field_mapping
            )
            self.reference_data = reference_dataset.load()
        else:
            # 使用生成数据的后一半作为参考
            mid = len(self.generated_data) // 2
            self.reference_data = self.generated_data[mid:]
            self.generated_data = self.generated_data[:mid]

        return self.generated_data, self.reference_data

    def __len__(self) -> Tuple[int, int]:
        """获取数据集大小"""
        if self.generated_data is None or self.reference_data is None:
            self.load()
        return len(self.generated_data), len(self.reference_data)


class UniversalWinRateTool:
    """Win Rate 评估工具 - 通用版本

    支持多种数据源和评估模板的胜率对比工具。
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

    def evaluate(
        self,
        generated: List[Dict[str, Any]],
        reference: List[Dict[str, Any]],
        num_comparisons: int = 0
    ) -> Dict[str, Any]:
        """
        运行评估

        Args:
            generated: 生成数据列表
            reference: 参考数据列表
            num_comparisons: 对比次数 (0=min(len(generated), len(reference)))

        Returns:
            评估结果
        """
        # 确定对比次数
        if num_comparisons <= 0:
            num_comparisons = min(len(generated), len(reference))

        # 创建评估器
        evaluator = BaseWinRateEvaluator(
            llm=self.llm,
            eval_config=self.eval_config,
            field_mapping=self.field_mapping
        )

        # 运行评估
        self.results = evaluator.evaluate_win_rate(
            generated_problems=generated,
            reference_problems=reference,
            num_comparisons=num_comparisons
        )

        return self.results

    def run(self, params: Dict[str, Any]) -> str:
        """
        运行完整的评估工作流（高级接口）

        Args:
            params: 参数字典，包含：
                - generated_config: 生成数据源配置 (必需)
                  {"path": "path/to/generated.json"}
                - reference_config: 参考数据源配置 (必需)
                  {"path": "path/to/reference.json"}
                - generated_field_mapping: 生成数据字段映射 (可选)
                  {"problem": "question", "answer": "answer"}
                - reference_field_mapping: 参考数据字段映射 (可选)
                - template: 评估模板 (可选，覆盖初始化时的模板)
                - num_comparisons: 对比次数 (可选，默认: min(len(generated), len(reference)))
                - output_dir: 输出目录 (可选，默认: "evaluation_results")
                - judge_model: 评估模型 (可选，覆盖初始化时的模型)

        Returns:
            包含评估结果的 JSON 字符串
        """
        import os
        from datetime import datetime

        # 解析参数
        generated_config = params.get("generated_config")
        reference_config = params.get("reference_config")
        generated_field_mapping = params.get("generated_field_mapping", self.field_mapping)
        reference_field_mapping = params.get("reference_field_mapping", {})

        template = params.get("template", self.template)
        num_comparisons = params.get("num_comparisons", 0)
        output_dir = params.get("output_dir", "evaluation_results")

        # 验证必需参数
        if not generated_config or "path" not in generated_config:
            raise ValueError("generated_config must contain 'path' key")
        if not reference_config or "path" not in reference_config:
            raise ValueError("reference_config must contain 'path' key")

        # 为输出目录添加时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(output_dir, f"win_rate_{timestamp}")

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        print("\n" + "="*70)
        print("🎯 Win Rate 评估")
        print("="*70)

        # 步骤 1: 加载生成数据
        print(f"\n📥 步骤 1: 加载生成数据")
        print(f"   来源: {generated_config['path']}")
        generated_dataset = UniversalDataset(
            source_config=generated_config,
            field_mapping=generated_field_mapping
        )
        generated = generated_dataset.load()
        print(f"   ✓ 已加载 {len(generated)} 条生成数据")

        # 步骤 2: 加载参考数据
        print(f"\n📥 步骤 2: 加载参考数据")
        print(f"   来源: {reference_config['path']}")
        reference_dataset = UniversalDataset(
            source_config=reference_config,
            field_mapping=reference_field_mapping
        )
        reference = reference_dataset.load()
        print(f"   ✓ 已加载 {len(reference)} 条参考数据")

        # 步骤 3: 配置评估器
        print(f"\n⚙️  步骤 3: 配置评估器")
        self.template = template
        self.field_mapping = generated_field_mapping
        self.eval_config = EvaluationConfig.load_template(template)
        print(f"   模板: {template}")
        print(f"   评估维度: {', '.join(self.eval_config.get_dimension_names())}")

        # 步骤 4: 运行评估
        print(f"\n🚀 步骤 4: 开始 Win Rate 对比评估")
        results = self.evaluate(generated, reference, num_comparisons=num_comparisons)
        print(f"   ✓ 评估完成")

        # 步骤 5: 导出报告
        print(f"\n💾 步骤 5: 导出评估报告")
        report_path = self.export_report(results, output_dir=output_dir)
        print(f"   ✓ 报告已保存: {report_path}")

        print("\n" + "="*70)
        print("✅ Win Rate 评估完成")
        print("="*70)

        # 返回结果
        metrics = results.get("metrics", {})
        return json.dumps({
            "status": "success",
            "template": template,
            "judge_model": self.llm.model,
            "num_generated": len(generated),
            "num_reference": len(reference),
            "num_comparisons": metrics.get("total_comparisons", 0),
            "win_rate": metrics.get("win_rate", 0),
            "loss_rate": metrics.get("loss_rate", 0),
            "tie_rate": metrics.get("tie_rate", 0),
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
        comparisons = results.get("comparisons", [])

        # 获取统计数据
        win_rate = metrics.get('win_rate', 0)
        loss_rate = metrics.get('loss_rate', 0)
        tie_rate = metrics.get('tie_rate', 0)
        total_comparisons = metrics.get('total_comparisons', 0)
        wins = metrics.get('wins', 0)
        losses = metrics.get('losses', 0)
        ties = metrics.get('ties', 0)

        # 生成质量评级
        win_rate_pct = win_rate * 100
        if win_rate_pct >= 50:
            quality_level = "优秀"
            quality_icon = "⭐⭐⭐⭐⭐"
            quality_desc = "生成数据质量优于参考数据（胜率≥50%）。"
        elif win_rate_pct >= 40:
            quality_level = "良好"
            quality_icon = "⭐⭐⭐⭐"
            quality_desc = "生成数据质量接近参考数据（胜率40%-50%）。"
        elif win_rate_pct >= 30:
            quality_level = "中等"
            quality_icon = "⭐⭐⭐"
            quality_desc = "生成数据质量低于参考数据，但差距不大（胜率30%-40%）。"
        elif win_rate_pct >= 20:
            quality_level = "及格"
            quality_icon = "⭐⭐"
            quality_desc = "生成数据质量明显低于参考数据（胜率20%-30%）。"
        else:
            quality_level = "待改进"
            quality_icon = "⭐"
            quality_desc = "生成数据质量远低于参考数据（胜率<20%）。"

        # 生成Markdown报告
        report_lines = [
            "# Win Rate 评估报告\n\n",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"**评估模板**: {self.template}\n",
            f"**对比次数**: {total_comparisons}\n\n",
            "## 胜率统计\n\n",
            "| 指标 | 数值 | 百分比 |\n",
            "|------|------|--------|\n",
            f"| 生成数据胜出 | {wins}次 | {win_rate:.1%} |\n",
            f"| 参考数据胜出 | {losses}次 | {loss_rate:.1%} |\n",
            f"| 平局 | {ties}次 | {tie_rate:.1%} |\n\n",
            f"<strong>Win Rate</strong>: {win_rate:.1%}\n\n",
            f"{'✅' if quality_level in ['优秀', '良好'] else '⚠️'} <strong>{quality_level}</strong>: {quality_desc}\n\n",
            "## 对比详情\n\n",
        ]

        for i, comp in enumerate(comparisons, 1):
            report_lines.append(f"### 对比 {i}\n\n")
            report_lines.append(f"- **赢家**: {comp.get('actual_winner', comp.get('winner', 'N/A'))}\n")
            report_lines.append(f"- **原因**: {comp.get('reason', 'N/A')}\n\n")

        # 保存Markdown报告
        report_path = output_path / "win_rate_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.writelines(report_lines)

        # 保存JSON结果
        results_file = output_path / "win_rate_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        return str(report_path)

    def get_available_templates(self) -> List[str]:
        """获取所有可用模板"""
        return EvaluationConfig.get_available_templates()
