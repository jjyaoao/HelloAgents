"""
本地数据集加载器（Local Dataset Loader）

仅支持加载本地数据源：
- JSON 文件
- CSV 文件

支持灵活的字段映射，将源数据字段映射到标准字段。

使用方式：
    from hello_agents.evaluation.benchmarks.data_generation_Universal import UniversalDataset

    # 本地 JSON 数据
    dataset = UniversalDataset(
        source_config={"path": "data.json"},
        field_mapping={"problem": "question", "answer": "answer"}
    )
    data = dataset.load()

    # 本地 CSV 数据
    dataset = UniversalDataset(
        source_config={"path": "data.csv", "format": "csv"},
        field_mapping={"problem": "q", "answer": "a"}
    )
    data = dataset.load()
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


# ============================================================================
# 数据加载器基类
# ============================================================================

class DataLoader:
    """数据加载器基类"""

    def load(self) -> List[Dict[str, Any]]:
        """加载数据，返回数据列表"""
        raise NotImplementedError


# ============================================================================
# 具体数据加载器实现
# ============================================================================

class LocalDataLoader(DataLoader):
    """本地数据加载器（JSON/CSV）"""

    def __init__(self, path: str, format: str = "json"):
        """
        初始化本地数据加载器

        Args:
            path: 文件路径（JSON或CSV）
            format: 文件格式 ("json" 或 "csv")，默认自动检测
        """
        self.path = path
        
        # 自动检测格式
        if format == "auto":
            if path.endswith(".json"):
                self.format = "json"
            elif path.endswith(".csv"):
                self.format = "csv"
            else:
                self.format = "json"  # 默认 JSON
        else:
            self.format = format.lower()

        if not os.path.exists(path):
            raise FileNotFoundError(f"Data file not found: {path}")

    def load(self) -> List[Dict[str, Any]]:
        """加载本地数据"""
        print(f"\n[Loading] Local data: {self.path}")

        if self.format == "json":
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        elif self.format == "csv":
            import csv
            data = []
            with open(self.path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
        else:
            raise ValueError(f"Unsupported format: {self.format}")

        if isinstance(data, dict):
            data = [data]

        print(f"[OK] Loaded {len(data)} records")
        return data


# ============================================================================
# 通用数据集加载器（主类）
# ============================================================================

class UniversalDataset:
    """本地数据集加载器

    支持：
    - 本地 JSON 文件
    - 本地 CSV 文件
    - 灵活的字段映射
    """

    def __init__(
        self,
        source_config: Dict[str, Any],
        field_mapping: Optional[Dict[str, str]] = None
    ):
        """
        初始化本地数据集加载器

        Args:
            source_config: 数据源配置参数
                - path: 文件路径（必需）
                - format: 文件格式，"json"、"csv" 或 "auto"（可选，默认自动检测）
            field_mapping: 字段映射 {标准字段 -> 源字段}
                          例如: {"problem": "question", "answer": "answer"}
                          如果为 None，使用原始字段名
        """
        self.source_config = source_config
        self.field_mapping = field_mapping
        self.data = None
        self.raw_data = None

        # 验证并创建加载器
        self.loader = self._create_loader()

    def _create_loader(self) -> DataLoader:
        """工厂方法：创建本地数据加载器"""
        config = self.source_config.copy()
        
        if "path" not in config:
            raise ValueError("source_config must contain 'path' key")
        
        return LocalDataLoader(
            path=config["path"],
            format=config.get("format", "auto")
        )

    def load(self) -> List[Dict[str, Any]]:
        """
        加载数据

        Returns:
            适配后的数据列表
        """
        print("\n" + "="*70)
        print("Loading Dataset from Local Source")
        print("="*70)

        # 加载原始数据
        self.raw_data = self.loader.load()

        # 应用字段映射（如果指定）
        self.data = self._apply_field_mapping(self.raw_data)

        if self.field_mapping:
            print(f"[OK] Field mapping applied")

        print(f"\n[Done] Successfully loaded {len(self.data)} records")
        print("="*70 + "\n")

        return self.data

    def _apply_field_mapping(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        应用字段映射

        Args:
            data: 原始数据

        Returns:
            映射后的数据
        """
        if not self.field_mapping:
            return data

        mapped_data = []
        for item in data:
            new_item = {}

            # 应用字段映射：{标准字段 -> 源字段}
            for standard_key, source_key in self.field_mapping.items():
                if source_key in item:
                    new_item[standard_key] = item[source_key]
                else:
                    # 如果源字段不存在，保留 None
                    new_item[standard_key] = None

            # 保留未映射的原始字段
            for key, value in item.items():
                if key not in self.field_mapping.values():
                    new_item[key] = value

            mapped_data.append(new_item)

        return mapped_data

    def __len__(self) -> int:
        """获取数据集大小"""
        if self.data is None:
            self.load()
        return len(self.data)

    def __getitem__(self, index: int) -> Dict[str, Any]:
        """支持索引访问"""
        if self.data is None:
            self.load()
        return self.data[index]

    def __iter__(self):
        """支持迭代"""
        if self.data is None:
            self.load()
        return iter(self.data)

    @staticmethod
    def get_supported_formats() -> Dict[str, str]:
        """获取所有支持的文件格式"""
        return {
            "json": "JSON files (.json)",
            "csv": "CSV files (.csv)",
            "auto": "Auto-detect format from file extension"
        }

    @staticmethod
    def print_supported_formats():
        """打印支持的文件格式"""
        formats = UniversalDataset.get_supported_formats()
        print("\n" + "="*70)
        print("Supported file formats:")
        print("="*70)
        for fmt, description in formats.items():
            print(f"  - {fmt:10} : {description}")
        print("="*70 + "\n")
