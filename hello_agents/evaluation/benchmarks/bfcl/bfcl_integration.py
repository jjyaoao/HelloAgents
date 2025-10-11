"""
BFCL 官方评估工具集成模块

封装BFCL官方评估工具的调用，提供便捷的接口
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
import os


class BFCLIntegration:
    """BFCL官方评估工具集成类
    
    提供以下功能：
    1. 检查BFCL评估工具是否已安装
    2. 安装BFCL评估工具
    3. 运行BFCL官方评估
    4. 解析评估结果
    
    使用示例：
        integration = BFCLIntegration()
        
        # 检查并安装
        if not integration.is_installed():
            integration.install()
        
        # 运行评估
        integration.run_evaluation(
            model_name="HelloAgents",
            category="simple_python",
            result_file="result/HelloAgents/BFCL_v3_simple_python_result.json"
        )
        
        # 解析结果
        scores = integration.parse_results(
            model_name="HelloAgents",
            category="simple_python"
        )
    """
    
    def __init__(self, project_root: Optional[Union[str, Path]] = None):
        """初始化BFCL集成
        
        Args:
            project_root: BFCL项目根目录，如果为None则使用当前目录
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.result_dir = self.project_root / "result"
        self.score_dir = self.project_root / "score"
    
    def is_installed(self) -> bool:
        """检查BFCL评估工具是否已安装
        
        Returns:
            True如果已安装，False否则
        """
        try:
            result = subprocess.run(
                ["bfcl", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def install(self) -> bool:
        """安装BFCL评估工具
        
        Returns:
            True如果安装成功，False否则
        """
        print("📦 正在安装BFCL评估工具...")
        print("   运行: pip install bfcl-eval")
        
        try:
            result = subprocess.run(
                ["pip", "install", "bfcl-eval"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print("✅ BFCL评估工具安装成功")
                return True
            else:
                print(f"❌ 安装失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ 安装超时")
            return False
        except Exception as e:
            print(f"❌ 安装出错: {e}")
            return False
    
    def prepare_result_file(
        self,
        source_file: Union[str, Path],
        model_name: str,
        category: str
    ) -> Path:
        """准备BFCL评估所需的结果文件
        
        BFCL期望的文件路径格式：
        result/{model_name}/BFCL_v3_{category}_result.json
        
        Args:
            source_file: 源结果文件路径
            model_name: 模型名称
            category: 评估类别
            
        Returns:
            目标文件路径
        """
        source_file = Path(source_file)
        
        # 创建目标目录
        target_dir = self.result_dir / model_name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 确定目标文件名
        target_file = target_dir / f"BFCL_v3_{category}_result.json"
        
        # 复制文件
        if source_file.exists():
            import shutil
            shutil.copy2(source_file, target_file)
            print(f"✅ 结果文件已准备")
            print(f"   源文件: {source_file}")
            print(f"   目标文件: {target_file}")
        else:
            print(f"⚠️ 源文件不存在: {source_file}")
        
        return target_file
    
    def run_evaluation(
        self,
        model_name: str,
        category: str,
        result_file: Optional[Union[str, Path]] = None
    ) -> bool:
        """运行BFCL官方评估
        
        Args:
            model_name: 模型名称
            category: 评估类别
            result_file: 结果文件路径（可选，如果提供则先准备文件）
            
        Returns:
            True如果评估成功，False否则
        """
        # 如果提供了结果文件，先准备
        if result_file:
            self.prepare_result_file(result_file, model_name, category)
        
        # 设置环境变量
        env = os.environ.copy()
        env["BFCL_PROJECT_ROOT"] = str(self.project_root)
        
        print(f"\n🔧 运行BFCL官方评估...")
        print(f"   模型: {model_name}")
        print(f"   类别: {category}")
        print(f"   项目根目录: {self.project_root}")
        
        # 构建命令
        cmd = [
            "bfcl", "evaluate",
            "--model", model_name,
            "--test-category", category
        ]
        
        print(f"   命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                env=env
            )
            
            if result.returncode == 0:
                print("✅ BFCL评估完成")
                print(result.stdout)
                return True
            else:
                print(f"❌ 评估失败")
                print(f"   错误信息: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ 评估超时")
            return False
        except Exception as e:
            print(f"❌ 评估出错: {e}")
            return False
    
    def parse_results(
        self,
        model_name: str,
        category: str
    ) -> Optional[Dict[str, Any]]:
        """解析BFCL评估结果
        
        Args:
            model_name: 模型名称
            category: 评估类别
            
        Returns:
            评估结果字典，如果文件不存在则返回None
        """
        # BFCL评估结果路径
        score_file = self.score_dir / model_name / f"BFCL_v3_{category}_score.json"
        
        if not score_file.exists():
            print(f"⚠️ 评估结果文件不存在: {score_file}")
            return None
        
        try:
            with open(score_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            print(f"\n📊 BFCL评估结果")
            print(f"   模型: {model_name}")
            print(f"   类别: {category}")
            
            # 提取关键指标
            if isinstance(results, dict):
                for key, value in results.items():
                    if isinstance(value, (int, float)):
                        print(f"   {key}: {value}")
            
            return results
            
        except Exception as e:
            print(f"❌ 解析结果失败: {e}")
            return None
    
    def get_summary_csv(self) -> Optional[Path]:
        """获取汇总CSV文件路径
        
        BFCL会生成以下CSV文件：
        - data_overall.csv: 总体评分
        - data_live.csv: Live数据集评分
        - data_non_live.csv: Non-Live数据集评分
        - data_multi_turn.csv: 多轮对话评分
        
        Returns:
            data_overall.csv的路径，如果不存在则返回None
        """
        csv_file = self.score_dir / "data_overall.csv"
        
        if csv_file.exists():
            print(f"\n📄 汇总CSV文件: {csv_file}")
            return csv_file
        else:
            print(f"⚠️ 汇总CSV文件不存在: {csv_file}")
            return None
    
    def print_usage_guide(self):
        """打印使用指南"""
        print("\n" + "="*60)
        print("BFCL官方评估工具使用指南")
        print("="*60)
        print("\n1. 安装BFCL评估工具：")
        print("   pip install bfcl-eval")
        print("\n2. 设置环境变量：")
        print(f"   export BFCL_PROJECT_ROOT={self.project_root}")
        print("\n3. 准备结果文件：")
        print("   将评估结果放在: result/{model_name}/BFCL_v3_{category}_result.json")
        print("\n4. 运行评估：")
        print("   bfcl evaluate --model {model_name} --test-category {category}")
        print("\n5. 查看结果：")
        print("   评估结果在: score/{model_name}/BFCL_v3_{category}_score.json")
        print("   汇总结果在: score/data_overall.csv")
        print("\n" + "="*60)

