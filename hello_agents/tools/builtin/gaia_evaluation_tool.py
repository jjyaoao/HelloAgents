"""GAIA评估工具

GAIA (General AI Assistants) 评估工具
用于评估智能体的通用能力
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
from datetime import datetime
from ..base import Tool, ToolParameter
from hello_agents.evaluation.benchmarks.gaia.dataset import GAIADataset
from hello_agents.evaluation.benchmarks.gaia.evaluator import GAIAEvaluator
from hello_agents.evaluation.benchmarks.gaia.metrics import GAIAMetrics


class GAIAEvaluationTool(Tool):
    """GAIA评估工具
    
    用于评估智能体的通用AI助手能力。
    支持三个难度级别：
    - Level 1: 简单任务（0步推理）
    - Level 2: 中等任务（1-5步推理）
    - Level 3: 困难任务（5+步推理）
    """
    
    def __init__(self, local_data_path: Optional[str] = None):
        """初始化GAIA评估工具
        
        Args:
            local_data_path: 本地数据路径（可选）
        """
        super().__init__(
            name="gaia_evaluation",
            description=(
                "评估智能体的通用AI助手能力。使用GAIA (General AI Assistants)基准测试。"
                "支持三个难度级别：Level 1(简单)、Level 2(中等)、Level 3(困难)。"
            )
        )
        self.local_data_path = local_data_path
        self.dataset = None
        self.evaluator = None
        self.metrics_calculator = GAIAMetrics()
    
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="agent",
                type="object",
                description="要评估的智能体实例",
                required=True
            ),
            ToolParameter(
                name="level",
                type="integer",
                description="难度级别：1(简单), 2(中等), 3(困难), None(全部)",
                required=False,
                default=None
            ),
            ToolParameter(
                name="max_samples",
                type="integer",
                description="最大评估样本数，None表示全部",
                required=False,
                default=None
            ),
            ToolParameter(
                name="local_data_dir",
                type="string",
                description="本地数据集目录路径",
                required=False,
                default=None
            )
        ]
    
    def run(
        self,
        agent: Any,
        level: Optional[int] = None,
        max_samples: Optional[int] = None,
        local_data_dir: Optional[str] = None,
        export_results: bool = True,
        generate_report: bool = True
    ) -> Dict[str, Any]:
        """执行GAIA一键评估

        Args:
            agent: 要评估的智能体
            level: 难度级别 (1-3)，None表示全部
            max_samples: 最大样本数，None表示全部
            local_data_dir: 本地数据目录路径
            export_results: 是否导出GAIA格式结果
            generate_report: 是否生成评估报告

        Returns:
            评估结果字典
        """
        print("\n" + "=" * 60)
        print("GAIA一键评估")
        print("=" * 60)

        # 显示配置
        print(f"\n配置:")
        print(f"   智能体: {getattr(agent, 'name', 'Unknown')}")
        print(f"   难度级别: {level or '全部'}")
        print(f"   样本数量: {max_samples or '全部'}")

        try:
            # 步骤1: 运行HelloAgents评估
            print("\n" + "=" * 60)
            print("步骤1: 运行HelloAgents评估")
            print("=" * 60)

            results = self._run_evaluation(agent, level, max_samples, local_data_dir)

            # 步骤2: 导出GAIA格式结果
            if export_results:
                print("\n" + "=" * 60)
                print("步骤2: 导出GAIA格式结果")
                print("=" * 60)

                self._export_results(results)

            # 步骤3: 生成评估报告
            if generate_report:
                print("\n" + "=" * 60)
                print("步骤3: 生成评估报告")
                print("=" * 60)

                self.generate_report(results)

            # 显示最终结果
            print("\n" + "=" * 60)
            print("🎯 最终结果")
            print("=" * 60)
            print(f"   精确匹配率: {results['exact_match_rate']:.2%}")
            print(f"   部分匹配率: {results['partial_match_rate']:.2%}")
            print(f"   正确数: {results['exact_matches']}/{results['total_samples']}")

            return results

        except Exception as e:
            print(f"\n❌ 评估失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "benchmark": "GAIA",
                "agent_name": getattr(agent, 'name', 'Unknown')
            }

    def _run_evaluation(
        self,
        agent: Any,
        level: Optional[int],
        max_samples: Optional[int],
        local_data_dir: Optional[str]
    ) -> Dict[str, Any]:
        """运行评估"""
        # 加载数据集
        self.dataset = GAIADataset(
            level=level,
            local_data_dir=local_data_dir or self.local_data_path
        )
        dataset_items = self.dataset.load()

        if not dataset_items:
            raise ValueError("数据集加载失败或为空")

        # 创建评估器
        self.evaluator = GAIAEvaluator(
            dataset=self.dataset,
            level=level,
            local_data_dir=local_data_dir or self.local_data_path
        )

        # 运行评估
        results = self.evaluator.evaluate(agent, max_samples)

        return results

    def _export_results(self, results: Dict[str, Any]) -> None:
        """导出GAIA格式结果和提交说明"""
        # 创建输出目录
        output_dir = Path("./evaluation_results/gaia_official")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        agent_name = results.get("agent_name", "Unknown").replace("/", "_")
        level = results.get("level_filter")
        level_str = f"_level{level}" if level else "_all"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"gaia{level_str}_result_{timestamp}.jsonl"

        # 导出JSONL结果
        self.evaluator.export_to_gaia_format(
            results,
            output_file,
            include_reasoning=True
        )

        # 生成提交说明文件
        self._generate_submission_guide(results, output_dir, output_file)

    def _generate_submission_guide(
        self,
        results: Dict[str, Any],
        output_dir: Path,
        result_file: Path
    ) -> None:
        """生成提交说明文件

        Args:
            results: 评估结果
            output_dir: 输出目录
            result_file: 结果文件路径
        """
        agent_name = results.get("agent_name", "Unknown")
        level = results.get("level_filter")
        total_samples = results.get("total_samples", 0)
        exact_matches = results.get("exact_matches", 0)
        exact_match_rate = results.get("exact_match_rate", 0)

        # 生成提交说明
        guide_content = f"""# GAIA评估结果提交指南

## 📊 评估结果摘要

- **模型名称**: {agent_name}
- **评估级别**: {level or '全部'}
- **总样本数**: {total_samples}
- **精确匹配数**: {exact_matches}
- **精确匹配率**: {exact_match_rate:.2%}

## 📁 提交文件

**结果文件**: `{result_file.name}`

此文件包含：
- 每个任务的task_id
- 模型的答案（model_answer）
- 推理轨迹（reasoning_trace）

## 🚀 如何提交到GAIA排行榜

### 步骤1: 访问GAIA排行榜

打开浏览器，访问：
```
https://huggingface.co/spaces/gaia-benchmark/leaderboard
```

### 步骤2: 准备提交信息

在提交表单中填写以下信息：

1. **Model Name（模型名称）**: `{agent_name}`
2. **Model Family（模型家族）**: 例如 `GPT`, `Claude`, `Qwen` 等
3. **Model Type（模型类型）**:
   - `Open-source` (开源)
   - `Proprietary` (专有)
4. **Results File（结果文件）**: 上传 `{result_file.name}`

### 步骤3: 上传结果文件

1. 点击 "Choose File" 按钮
2. 选择文件: `{result_file.absolute()}`
3. 确认文件格式为 `.jsonl`

### 步骤4: 提交

1. 检查所有信息是否正确
2. 点击 "Submit" 按钮
3. 等待评估结果（通常需要几分钟）

## 📋 结果文件格式说明

GAIA要求的JSONL格式（每行一个JSON对象）：

```json
{{"task_id": "xxx", "model_answer": "答案", "reasoning_trace": "推理过程"}}
```

**字段说明**：
- `task_id`: 任务ID（与GAIA数据集对应）
- `model_answer`: 模型的最终答案
- `reasoning_trace`: 模型的推理过程（可选）

## ⚠️ 注意事项

1. **答案格式**：
   - 数字：不使用逗号分隔符，不使用单位符号
   - 字符串：不使用冠词，使用小写
   - 列表：逗号分隔，按字母顺序排列

2. **文件大小**：
   - 确保文件不超过10MB
   - 如果文件过大，考虑移除reasoning_trace

3. **提交频率**：
   - 建议先在小样本上测试
   - 确认结果正确后再提交完整评估

## 📞 获取帮助

如果遇到问题：
1. 查看GAIA官方文档：https://huggingface.co/gaia-benchmark
2. 在HuggingFace论坛提问
3. 检查结果文件格式是否正确

---

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**工具版本**: HelloAgents GAIA Evaluation Tool v1.0
"""

        # 保存提交说明
        guide_file = output_dir / f"SUBMISSION_GUIDE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(guide_content)

        print(f"📄 提交说明已生成: {guide_file}")

    def generate_report(
        self,
        results: Dict[str, Any],
        output_file: Optional[Union[str, Path]] = None
    ) -> str:
        """生成评估报告

        Args:
            results: 评估结果
            output_file: 输出文件路径（可选）

        Returns:
            Markdown格式的报告
        """
        # 生成报告内容
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        agent_name = results.get("agent_name", "Unknown")
        level = results.get("level_filter")
        total_samples = results.get("total_samples", 0)
        exact_matches = results.get("exact_matches", 0)
        partial_matches = results.get("partial_matches", 0)
        exact_match_rate = results.get("exact_match_rate", 0)
        partial_match_rate = results.get("partial_match_rate", 0)
        level_metrics = results.get("level_metrics", {})
        detailed_results = results.get("detailed_results", [])

        # 构建报告
        report = f"""# GAIA评估报告

**生成时间**: {timestamp}

## 📊 评估概览

- **智能体**: {agent_name}
- **难度级别**: {level or '全部'}
- **总样本数**: {total_samples}
- **精确匹配数**: {exact_matches}
- **部分匹配数**: {partial_matches}
- **精确匹配率**: {exact_match_rate:.2%}
- **部分匹配率**: {partial_match_rate:.2%}

## 📈 详细指标

### 分级准确率

"""

        # 添加分级统计
        for level_name, metrics in level_metrics.items():
            level_num = level_name.replace("Level_", "")
            total = metrics.get("total", 0)
            exact = metrics.get("exact_matches", 0)
            partial = metrics.get("partial_matches", 0)
            exact_rate = metrics.get("exact_match_rate", 0)
            partial_rate = metrics.get("partial_match_rate", 0)

            report += f"- **Level {level_num}**: {exact_rate:.2%} 精确 / {partial_rate:.2%} 部分 ({exact}/{total})\n"

        # 添加样本详情（前10个）
        report += "\n## 📝 样本详情（前10个）\n\n"
        report += "| 任务ID | 级别 | 预测答案 | 正确答案 | 精确匹配 | 部分匹配 |\n"
        report += "|--------|------|----------|----------|----------|----------|\n"

        for i, detail in enumerate(detailed_results[:10]):
            task_id = detail.get("task_id", "")
            level_num = detail.get("level", "")
            predicted = str(detail.get("predicted", ""))[:50]  # 限制长度
            expected = str(detail.get("expected", ""))[:50]
            exact = "✅" if detail.get("exact_match") else "❌"
            partial = "✅" if detail.get("partial_match") else "❌"

            report += f"| {task_id} | {level_num} | {predicted} | {expected} | {exact} | {partial} |\n"

        # 添加准确率可视化
        report += "\n## 📊 准确率可视化\n\n"
        report += "```\n"
        bar_length = 50
        filled = int(exact_match_rate * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        report += f"精确匹配: {bar} {exact_match_rate:.2%}\n"

        filled_partial = int(partial_match_rate * bar_length)
        bar_partial = "█" * filled_partial + "░" * (bar_length - filled_partial)
        report += f"部分匹配: {bar_partial} {partial_match_rate:.2%}\n"
        report += "```\n"

        # 添加建议
        report += "\n## 💡 建议\n\n"
        if exact_match_rate >= 0.9:
            report += "- ✅ 表现优秀！智能体在GAIA基准上表现出色。\n"
        elif exact_match_rate >= 0.7:
            report += "- 👍 表现良好，但仍有提升空间。\n"
            report += "- 💡 建议优化提示词和推理策略。\n"
        elif exact_match_rate >= 0.5:
            report += "- ⚠️ 表现一般，需要改进。\n"
            report += "- 💡 建议检查工具使用和多步推理能力。\n"
        else:
            report += "- ❌ 表现较差，需要大幅改进。\n"
            report += "- 💡 建议从简单级别开始，逐步提升。\n"

        # 保存报告
        if output_file is None:
            output_dir = Path("./evaluation_reports")
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"gaia_report_{timestamp_str}.md"
        else:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📄 报告已生成: {output_file}")

        return report

    def get_dataset_info(self, level: Optional[int] = None) -> Dict[str, Any]:
        """获取数据集信息
        
        Args:
            level: 难度级别
            
        Returns:
            数据集信息字典
        """
        try:
            dataset = GAIADataset(level=level, local_data_path=self.local_data_path)
            items = dataset.load()
            
            # 获取统计信息
            stats = dataset.get_statistics()
            level_dist = dataset.get_level_distribution()
            
            return {
                "level": level,
                "total_samples": len(items),
                "level_distribution": level_dist,
                "statistics": stats,
                "sample_keys": list(items[0].keys()) if items else [],
                "levels_available": [1, 2, 3]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def validate_agent(self, agent: Any) -> bool:
        """验证智能体是否具备必要的接口
        
        Args:
            agent: 要验证的智能体
            
        Returns:
            是否有效
        """
        # 检查agent是否有run方法
        if not hasattr(agent, 'run'):
            return False
        
        # 检查run方法是否可调用
        if not callable(getattr(agent, 'run')):
            return False
        
        return True
    

