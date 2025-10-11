"""
BFCL 评估器模块

负责评估智能体在 BFCL 基准测试上的表现
"""

from typing import Dict, Any, List, Optional, Union
import json
import ast
import re
import time
from pathlib import Path
from hello_agents.evaluation.benchmarks.bfcl.dataset import BFCLDataset
from hello_agents.evaluation.benchmarks.bfcl.metrics import BFCLMetrics


class BFCLEvaluator:
    """BFCL 评估器

    评估智能体的工具调用能力,包括:
    - 简单函数调用
    - 多函数调用
    - 并行函数调用
    - 无关检测

    支持两种评估模式:
    - AST评估: 抽象语法树匹配
    - 执行评估: 实际函数执行结果对比

    Attributes:
        dataset: BFCL 数据集
        metrics: 评估指标计算器
        evaluation_mode: 评估模式 ('ast' 或 'execution')
    """

    def __init__(
        self,
        dataset: Optional[BFCLDataset] = None,
        category: Optional[str] = None,
        evaluation_mode: str = "ast",
        local_data_dir: Optional[str] = None
    ):
        """初始化 BFCL 评估器

        Args:
            dataset: BFCL 数据集,如果为 None 则自动创建
            category: 评估类别
            evaluation_mode: 评估模式 ('ast' 或 'execution')
            local_data_dir: 本地数据目录
        """
        self.dataset = dataset or BFCLDataset(
            category=category,
            local_data_dir=local_data_dir
        )
        self.metrics = BFCLMetrics()
        self.evaluation_mode = evaluation_mode
        self.category = category
        
    def evaluate(self, agent: Any, max_samples: Optional[int] = None) -> Dict[str, Any]:
        """评估智能体

        Args:
            agent: 要评估的智能体
            max_samples: 最大评估样本数,None表示评估全部

        Returns:
            评估结果字典,包含各项指标
        """
        print(f"\n🔧 开始 BFCL 评估...")
        print(f"   智能体: {getattr(agent, 'name', 'Unknown')}")
        print(f"   评估模式: {self.evaluation_mode}")
        print(f"   类别: {self.category or '全部'}")

        # 加载数据集
        dataset = self.dataset.load()
        if not dataset:
            print("   ⚠️ 数据集为空,跳过评估")
            return self._create_empty_results(agent)

        # 限制样本数量
        if max_samples:
            dataset = dataset[:max_samples]

        print(f"   样本数量: {len(dataset)}")

        # 执行评估
        results = []
        categories = {}

        for i, sample in enumerate(dataset):
            if i % 10 == 0:
                print(f"   进度: {i+1}/{len(dataset)}")

            try:
                sample_result = self.evaluate_sample(agent, sample)
                results.append(sample_result)

                # 按类别统计（使用评估器的category，而不是样本的category）
                category = self.category if self.category else sample.get("category", "unknown")
                if category not in categories:
                    categories[category] = {"total": 0, "correct": 0, "results": []}

                categories[category]["total"] += 1
                if sample_result["success"]:
                    categories[category]["correct"] += 1
                categories[category]["results"].append(sample_result)

            except Exception as e:
                print(f"   ⚠️ 样本 {i} 评估失败: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "predicted": None,
                    "expected": sample.get("ground_truth"),
                    "score": 0.0
                })

        # 计算总体指标
        total_samples = len(results)
        correct_samples = sum(1 for r in results if r["success"])
        overall_accuracy = correct_samples / total_samples if total_samples > 0 else 0.0

        # 计算分类指标
        category_metrics = {}
        for cat, cat_data in categories.items():
            accuracy = cat_data["correct"] / cat_data["total"] if cat_data["total"] > 0 else 0.0
            category_metrics[cat] = {
                "total": cat_data["total"],
                "correct": cat_data["correct"],
                "accuracy": accuracy
            }

        final_results = {
            "benchmark": "BFCL",
            "agent_name": getattr(agent, 'name', 'Unknown'),
            "evaluation_mode": self.evaluation_mode,
            "category": self.category,
            "total_samples": total_samples,
            "correct_samples": correct_samples,
            "overall_accuracy": overall_accuracy,
            "category_metrics": category_metrics,
            "detailed_results": results
        }

        print(f"✅ BFCL 评估完成")
        print(f"   总体准确率: {overall_accuracy:.2%}")
        for cat, metrics in category_metrics.items():
            print(f"   {cat}: {metrics['accuracy']:.2%} ({metrics['correct']}/{metrics['total']})")

        return final_results
    
    def evaluate_sample(self, agent: Any, sample: Dict[str, Any]) -> Dict[str, Any]:
        """评估单个样本

        Args:
            agent: 要评估的智能体
            sample: 样本数据

        Returns:
            单个样本的评估结果
        """
        try:
            # 准备输入
            question = sample.get("question", "")
            functions = sample.get("function", [])
            ground_truth = sample.get("ground_truth", [])

            # 构建函数调用提示
            prompt = self._build_function_calling_prompt(question, functions)

            # 调用智能体
            start_time = time.time()
            response = agent.run(prompt)
            execution_time = time.time() - start_time

            # 解析响应中的函数调用
            predicted_calls = self._extract_function_calls(response)

            # 评估结果
            if self.evaluation_mode == "ast":
                success, score = self._evaluate_ast_matching(predicted_calls, ground_truth)
            else:
                success, score = self._evaluate_execution(predicted_calls, ground_truth, functions)

            return {
                "success": success,
                "score": score,
                "predicted": predicted_calls,
                "expected": ground_truth,
                "response": response,
                "question": question,  # 添加question字段用于导出
                "execution_time": execution_time,
                "sample_id": sample.get("id", ""),
                "category": self.category if self.category else sample.get("category", "unknown")
            }

        except Exception as e:
            return {
                "success": False,
                "score": 0.0,
                "predicted": None,
                "expected": sample.get("ground_truth", []),
                "question": sample.get("question", ""),  # 添加question字段
                "error": str(e),
                "sample_id": sample.get("id", ""),
                "category": self.category if self.category else sample.get("category", "unknown")
            }

    def _create_empty_results(self, agent: Any) -> Dict[str, Any]:
        """创建空的评估结果"""
        return {
            "benchmark": "BFCL",
            "agent_name": getattr(agent, 'name', 'Unknown'),
            "evaluation_mode": self.evaluation_mode,
            "category": self.category,
            "total_samples": 0,
            "correct_samples": 0,
            "overall_accuracy": 0.0,
            "category_metrics": {},
            "detailed_results": []
        }

    def _build_function_calling_prompt(self, question: str, functions: List[Dict]) -> str:
        """构建函数调用提示"""
        if not functions:
            return question

        prompt = f"你是一个智能助手，可以调用以下函数来帮助回答问题：\n\n"

        # 添加函数定义
        for i, func in enumerate(functions, 1):
            func_name = func.get("name", f"function_{i}")
            func_desc = func.get("description", "")
            func_params = func.get("parameters", {})

            prompt += f"函数 {i}: {func_name}\n"
            prompt += f"描述: {func_desc}\n"

            if func_params:
                prompt += f"参数: {json.dumps(func_params, ensure_ascii=False, indent=2)}\n"

            prompt += "\n"

        prompt += f"请根据以下问题，选择合适的函数进行调用：\n{question}\n\n"
        prompt += "请以JSON格式返回函数调用，例如：\n"
        prompt += '[{"name": "function_name", "arguments": {"param1": "value1"}}]'

        return prompt

    def _extract_function_calls(self, response: str) -> List[Dict[str, Any]]:
        """从响应中提取函数调用"""
        try:
            # 尝试直接解析JSON
            if response.strip().startswith('[') and response.strip().endswith(']'):
                return json.loads(response.strip())

            # 使用正则表达式查找JSON数组
            json_pattern = r'\[.*?\]'
            matches = re.findall(json_pattern, response, re.DOTALL)

            for match in matches:
                try:
                    calls = json.loads(match)
                    if isinstance(calls, list):
                        return calls
                except json.JSONDecodeError:
                    continue

            # 查找单个函数调用
            single_call_pattern = r'\{.*?"name".*?\}'
            matches = re.findall(single_call_pattern, response, re.DOTALL)

            calls = []
            for match in matches:
                try:
                    call = json.loads(match)
                    if "name" in call:
                        calls.append(call)
                except json.JSONDecodeError:
                    continue

            return calls

        except Exception:
            return []

    def _evaluate_ast_matching(self, predicted: List[Dict], expected: List) -> tuple[bool, float]:
        """AST匹配评估

        支持两种ground truth格式：
        1. BFCL v4格式：[{"func_name": {"param": [value1, value2]}}]
        2. 字符串格式：["func_name(param=value)"]
        """
        if not expected:
            return len(predicted) == 0, 1.0 if len(predicted) == 0 else 0.0

        try:
            # 检测ground truth格式
            if expected and isinstance(expected[0], dict):
                # BFCL v4格式
                return self._evaluate_bfcl_v4_format(predicted, expected)
            else:
                # 字符串格式（旧版）
                return self._evaluate_string_format(predicted, expected)

        except Exception as e:
            print(f"   ⚠️ 评估出错: {e}")
            return False, 0.0

    def _evaluate_bfcl_v4_format(self, predicted: List[Dict], expected: List[Dict]) -> tuple[bool, float]:
        """评估BFCL v4格式的ground truth

        BFCL v4格式：
        predicted: [{"name": "func_name", "arguments": {"param": value}}]
        expected: [{"func_name": {"param": [value1, value2]}}]
        """
        if len(predicted) != len(expected):
            return False, 0.0

        matches = 0
        for pred_call in predicted:
            if not isinstance(pred_call, dict) or "name" not in pred_call:
                continue

            pred_func_name = pred_call["name"]
            pred_args = pred_call.get("arguments", {})

            # 在expected中查找匹配的函数调用
            for exp_call in expected:
                if not isinstance(exp_call, dict):
                    continue

                # expected格式：{"func_name": {"param": [values]}}
                for exp_func_name, exp_params in exp_call.items():
                    if exp_func_name != pred_func_name:
                        continue

                    # 比较参数
                    if self._compare_parameters(pred_args, exp_params):
                        matches += 1
                        break

        success = matches == len(expected)
        score = matches / len(expected) if expected else 0.0
        return success, score

    def _compare_parameters(self, pred_params: Dict, exp_params: Dict) -> bool:
        """比较预测参数和期望参数

        Args:
            pred_params: {"param": value}
            exp_params: {"param": [value1, value2]}  # 数组表示多个可接受的值
        """
        # 检查所有必需参数
        for param_name, expected_values in exp_params.items():
            if param_name not in pred_params:
                # 参数缺失，检查是否有空字符串作为默认值
                if not isinstance(expected_values, list) or "" not in expected_values:
                    return False
                continue

            pred_value = pred_params[param_name]

            # expected_values是数组，包含所有可接受的值
            if isinstance(expected_values, list):
                # 检查pred_value是否在可接受的值列表中
                if pred_value not in expected_values:
                    # 尝试类型转换后比较
                    if str(pred_value) not in [str(v) for v in expected_values]:
                        return False
            else:
                # 单个值比较
                if pred_value != expected_values and str(pred_value) != str(expected_values):
                    return False

        return True

    def _evaluate_string_format(self, predicted: List[Dict], expected: List[str]) -> tuple[bool, float]:
        """评估字符串格式的ground truth（旧版）"""
        # 将预测结果转换为字符串形式
        predicted_strs = []
        for call in predicted:
            if isinstance(call, dict) and "name" in call:
                func_name = call["name"]
                args = call.get("arguments", {})
                # 构建函数调用字符串
                if args:
                    args_str = ", ".join([f"{k}={repr(v)}" for k, v in args.items()])
                    call_str = f"{func_name}({args_str})"
                else:
                    call_str = f"{func_name}()"
                predicted_strs.append(call_str)

        # 简单的字符串匹配评估
        if len(predicted_strs) != len(expected):
            return False, 0.0

        # 检查每个函数调用是否匹配
        matches = 0
        for pred_str in predicted_strs:
            for exp_str in expected:
                if self._ast_strings_match(pred_str, exp_str):
                    matches += 1
                    break

        success = matches == len(expected)
        score = matches / len(expected) if expected else 0.0

        return success, score

    def _ast_strings_match(self, pred: str, expected: str) -> bool:
        """比较两个函数调用字符串是否在AST层面匹配"""
        try:
            # 尝试解析为AST并比较
            pred_ast = ast.parse(pred, mode='eval')
            exp_ast = ast.parse(expected, mode='eval')
            return ast.dump(pred_ast) == ast.dump(exp_ast)
        except:
            # 如果AST解析失败，使用字符串相似度
            return pred.strip() == expected.strip()

    def _evaluate_execution(self, predicted: List[Dict], expected: List[str], functions: List[Dict]) -> tuple[bool, float]:
        """执行评估（简化版本）"""
        # 这里实现简化的执行评估
        # 在实际应用中，需要安全的代码执行环境
        return self._evaluate_ast_matching(predicted, expected)

    def export_to_bfcl_format(
        self,
        results: Dict[str, Any],
        output_path: Union[str, Path],
        include_inference_log: bool = True
    ) -> None:
        """导出评估结果为BFCL官方格式

        BFCL官方格式示例：
        {
            "id": "simple_python_0",
            "model_result": [
                {
                    "name": "calculate_triangle_area",
                    "arguments": {"base": 10, "height": 5, "unit": "units"}
                }
            ],
            "inference_log": [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }

        Args:
            results: evaluate()方法返回的评估结果
            output_path: 输出文件路径
            include_inference_log: 是否包含推理日志
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 转换为BFCL格式
        bfcl_results = []

        for detail in results.get("detailed_results", []):
            # 将predicted转换为字符串格式的函数调用
            predicted = detail.get("predicted", [])
            result_string = ""

            if predicted:
                call = predicted[0]  # 通常只有一个函数调用
                if isinstance(call, dict) and "name" in call:
                    func_name = call["name"]
                    args = call.get("arguments", {})

                    # 构建函数调用字符串
                    if args:
                        args_str = ", ".join([f"{k}={repr(v)}" for k, v in args.items()])
                        result_string = f"{func_name}({args_str})"
                    else:
                        result_string = f"{func_name}()"

            bfcl_item = {
                "id": detail.get("sample_id", ""),
                "result": result_string  # BFCL期望的是单个字符串
            }

            # 添加推理日志（如果需要）
            if include_inference_log:
                question = detail.get("question", "")
                response = detail.get("response", "")

                bfcl_item["inference_log"] = [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": response}
                ]

            bfcl_results.append(bfcl_item)

        # 写入JSONL格式（每行一个JSON对象）
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in bfcl_results:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        print(f"\n✅ BFCL格式结果已导出")
        print(f"   输出文件: {output_path}")
        print(f"   样本数: {len(bfcl_results)}")
        print(f"   包含推理日志: {include_inference_log}")

        # 提示如何使用BFCL官方评估
        print(f"\n📝 使用BFCL官方评估工具：")
        print(f"   1. 安装: pip install bfcl-eval")
        print(f"   2. 设置环境变量: export BFCL_PROJECT_ROOT=.")
        print(f"   3. 将结果文件复制到: result/HelloAgents/")
        print(f"   4. 运行评估: bfcl evaluate --model HelloAgents --test-category {self.category}")

