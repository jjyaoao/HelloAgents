"""
GAIA 数据集加载模块

负责从 HuggingFace 加载 GAIA (General AI Assistants) 数据集
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json


class GAIADataset:
    """GAIA 数据集加载器

    从 HuggingFace 加载 GAIA 数据集,支持不同难度级别。

    GAIA是一个通用AI助手评估基准,包含466个真实世界问题,
    需要推理、多模态处理、网页浏览和工具使用等能力。

    难度级别:
    - Level 1: 简单问题 (0步推理, 直接回答)
    - Level 2: 中等问题 (1-5步推理, 需要简单工具使用)
    - Level 3: 复杂问题 (5+步推理, 需要复杂工具链和多步推理)

    Attributes:
        dataset_name: HuggingFace 数据集名称
        split: 数据集分割(validation/test)
        level: 难度级别
        data: 加载的数据列表
    """

    def __init__(
        self,
        dataset_name: str = "gaia-benchmark/GAIA",
        split: str = "validation",
        level: Optional[int] = None,
        local_data_dir: Optional[Union[str, Path]] = None
    ):
        """初始化 GAIA 数据集加载器

        Args:
            dataset_name: HuggingFace 数据集名称
            split: 数据集分割 (validation/test)
            level: 难度级别 (1-3),None表示加载所有级别
            local_data_dir: 本地数据目录路径
        """
        self.dataset_name = dataset_name
        self.split = split
        self.level = level
        self.local_data_dir = Path(local_data_dir) if local_data_dir else None
        self.data = []
        self._is_local = self._check_if_local_source()

    def _check_if_local_source(self) -> bool:
        """检查是否使用本地数据源"""
        if self.local_data_dir and self.local_data_dir.exists():
            return True
        return False

    def load(self) -> List[Dict[str, Any]]:
        """加载数据集

        Returns:
            数据集列表,每个元素包含问题、答案、难度等
        """
        if self._is_local:
            self.data = self._load_from_local()
        else:
            self.data = self._load_from_huggingface()

        # 按级别过滤
        if self.level is not None:
            self.data = [item for item in self.data if item.get("level") == self.level]

        print(f"✅ GAIA数据集加载完成")
        print(f"   数据源: {self.dataset_name}")
        print(f"   分割: {self.split}")
        print(f"   级别: {self.level or '全部'}")
        print(f"   样本数: {len(self.data)}")

        return self.data

    def _load_from_local(self) -> List[Dict[str, Any]]:
        """从本地加载数据集"""
        data = []

        if not self.local_data_dir or not self.local_data_dir.exists():
            print("   ⚠️ 本地数据目录不存在")
            return data

        # 查找JSON文件
        json_files = list(self.local_data_dir.glob("*.json"))
        json_files.extend(self.local_data_dir.glob("**/*.json"))

        # 过滤GAIA相关文件
        gaia_files = [f for f in json_files if "gaia" in f.name.lower()]

        for json_file in gaia_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)

                if isinstance(file_data, list):
                    for item in file_data:
                        data.append(self._standardize_item(item))
                else:
                    data.append(self._standardize_item(file_data))

                print(f"   加载文件: {json_file.name} ({len(file_data)} 样本)")
            except Exception as e:
                print(f"   ⚠️ 加载文件失败: {json_file.name} - {e}")

        return data

    def _load_from_huggingface(self) -> List[Dict[str, Any]]:
        """从HuggingFace下载GAIA数据集

        注意：GAIA是gated dataset，需要HF_TOKEN环境变量
        使用snapshot_download下载整个数据集到本地
        """
        try:
            from huggingface_hub import snapshot_download
            import os
            import json
            from pathlib import Path

            print(f"   正在从HuggingFace下载: {self.dataset_name}")

            # 获取HF token
            hf_token = os.getenv("HF_TOKEN")
            if not hf_token:
                print("   ⚠️ 未找到HF_TOKEN环境变量")
                print("   GAIA是gated dataset，需要在HuggingFace上申请访问权限")
                print("   然后设置环境变量: HF_TOKEN=your_token")
                return []

            # 下载数据集到本地
            print(f"   📥 下载GAIA数据集...")
            # 使用当前工作目录下的data/gaia文件夹
            local_dir = Path.cwd() / "data" / "gaia"
            local_dir.mkdir(parents=True, exist_ok=True)

            try:
                snapshot_download(
                    repo_id=self.dataset_name,
                    repo_type="dataset",
                    local_dir=str(local_dir),
                    token=hf_token,
                    local_dir_use_symlinks=False  # Windows兼容性
                )
                print(f"   ✓ 数据集下载完成: {local_dir}")
            except Exception as e:
                print(f"   ⚠️ 下载失败: {e}")
                print("   请确保:")
                print("   1. 已在HuggingFace上申请GAIA访问权限")
                print("   2. HF_TOKEN正确且有效")
                return []

            # 读取metadata.jsonl文件
            metadata_file = local_dir / "2023" / self.split / "metadata.jsonl"
            if not metadata_file.exists():
                print(f"   ⚠️ 未找到metadata文件: {metadata_file}")
                return []

            # 加载数据
            data = []
            with open(metadata_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    item = json.loads(line)

                    # 跳过占位符
                    if item.get("task_id") == "0-0-0-0-0":
                        continue

                    # 调整文件路径
                    if item.get("file_name"):
                        item["file_name"] = str(local_dir / "2023" / self.split / item["file_name"])

                    # 标准化并添加
                    standardized_item = self._standardize_item(item)
                    data.append(standardized_item)

            print(f"   ✓ 加载了 {len(data)} 个样本")
            return data

        except ImportError:
            print("   ⚠️ huggingface_hub库未安装")
            print("   提示: pip install huggingface_hub")
            return []
        except Exception as e:
            print(f"   ⚠️ 加载失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _standardize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """标准化数据项格式"""
        # GAIA数据集的标准字段
        standardized = {
            "task_id": item.get("task_id", ""),
            "question": item.get("Question", item.get("question", "")),
            "level": item.get("Level", item.get("level", 1)),
            "final_answer": item.get("Final answer", item.get("final_answer", "")),
            "file_name": item.get("file_name", ""),
            "file_path": item.get("file_path", ""),
            "annotator_metadata": item.get("Annotator Metadata", item.get("annotator_metadata", {})),
            "steps": item.get("Steps", item.get("steps", 0)),
            "tools": item.get("Tools", item.get("tools", [])),
            "raw_item": item  # 保留原始数据
        }

        return standardized
    
    def get_sample(self, index: int) -> Dict[str, Any]:
        """获取单个样本

        Args:
            index: 样本索引

        Returns:
            样本数据
        """
        if not self.data:
            self.load()
        return self.data[index] if index < len(self.data) else {}

    def get_by_level(self, level: int) -> List[Dict[str, Any]]:
        """获取指定难度级别的样本

        Args:
            level: 难度级别 (1-3)

        Returns:
            该级别的所有样本
        """
        if not self.data:
            self.load()
        return [item for item in self.data if item.get("level") == level]

    def get_level_distribution(self) -> Dict[int, int]:
        """获取难度级别分布

        Returns:
            字典，键为级别，值为该级别的样本数
        """
        if not self.data:
            self.load()

        distribution = {1: 0, 2: 0, 3: 0}
        for item in self.data:
            level = item.get("level", 1)
            if level in distribution:
                distribution[level] += 1

        return distribution

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据集统计信息

        Returns:
            统计信息字典
        """
        if not self.data:
            self.load()

        level_dist = self.get_level_distribution()

        # 统计需要文件的样本数
        with_files = sum(1 for item in self.data if item.get("file_name"))

        # 统计平均步数
        steps_list = [item.get("steps", 0) for item in self.data if item.get("steps")]
        avg_steps = sum(steps_list) / len(steps_list) if steps_list else 0

        return {
            "total_samples": len(self.data),
            "level_distribution": level_dist,
            "samples_with_files": with_files,
            "average_steps": avg_steps,
            "split": self.split
        }

    def __len__(self) -> int:
        """返回数据集大小"""
        if not self.data:
            self.load()
        return len(self.data)

    def __iter__(self):
        """迭代器"""
        if not self.data:
            self.load()
        return iter(self.data)

