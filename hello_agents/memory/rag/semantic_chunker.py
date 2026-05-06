"""语义边界分块器

适用于没有明确标题结构的文档：
- 小说、故事等叙事文本
- 法律条文、合同条款
- 技术规范、操作手册
- 学术论文

核心策略：
1. 检测语义边界（对话、段落、主题转换）
2. 构建语义连贯的块
3. 基于 token 限制合并/拆分
"""

from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import re


class BoundaryType(str, Enum):
    """语义边界类型"""

    SENTENCE = "sentence"  # 句子边界
    PARAGRAPH = "paragraph"  # 段落边界
    DIALOGUE = "dialogue"  # 对话边界
    CHAPTER_HINT = "chapter_hint"  # 章节暗示
    LIST_ITEM = "list_item"  # 列表项
    TOPIC_TRANSITION = "topic"  # 主题转换
    STRUCTURAL = "structural"  # 结构边界（如法律条款编号）


@dataclass
class SemanticBoundary:
    """语义边界"""

    position: int  # 在原文中的字符位置
    boundary_type: BoundaryType
    confidence: float  # 置信度 0-1
    label: str = ""  # 边界标签（如对话角色名）


@dataclass
class SemanticChunk:
    """语义块"""

    content: str
    start: int
    end: int
    boundaries: List[BoundaryType]  # 跨越的边界类型
    token_count: int
    metadata: Dict = None


class DialogueDetector:
    """对话检测器 - 识别对话边界"""

    DIALOGUE_PATTERNS = [
        r'^["\"\']([^"\']+)["\"\']',  # "对话内容"
        r"^「([^」]+)」",  # 中文引号对话
        r"^『([^』]+)』",  # 中文双引号
        r'["\"\']([^"\']+)["\"\']\s*$',  # 行尾对话
        r"^\s*[甲乙丙丁戊己庚辛壬癸][：:]\s*",  # 甲说：
        r"^\s*[A-Z][：:]\s+",  # A: B:
        r"^\s*---\s*$",  # 分隔线
    ]

    def detect(self, lines: List[str]) -> List[Tuple[int, str]]:
        """
        检测对话边界

        Returns:
            List of (line_index, speaker_label) tuples
        """
        dialogues = []
        current_speaker = None

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 检测对话开始
            for pattern in self.DIALOGUE_PATTERNS:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    content = match.group(1) if match.lastindex else line
                    if len(content) > 0:
                        current_speaker = self._extract_speaker(line, pattern)
                        dialogues.append((i, current_speaker))
                    break

            # 检测对话结束（长段落后的空行）
            if i > 0 and not line and current_speaker:
                dialogues.append((i, "__END_DIALOGUE__"))
                current_speaker = None

        return dialogues

    def _extract_speaker(self, line: str, pattern: str) -> str:
        """提取说话者"""
        if "甲乙丙丁戊己庚辛壬癸" in pattern:
            match = re.match(r"([甲乙丙丁戊己庚辛壬癸])[：:]", line)
            if match:
                return match.group(1)
        if re.match(r"[A-Z][：:]", line):
            return line[0]
        return "__SPEAKER__"


class StructuralPatternDetector:
    """结构模式检测器 - 检测法律条文等结构化内容"""

    PATTERNS = [
        # 法律条款编号
        (r"^\s*第[一二三四五六七八九十百千零\d]+条", BoundaryType.STRUCTURAL, 0.9),
        # 章节编号
        (
            r"^\s*(?:第[一二三四五六七八九十百千零\d]+[章节编部篇])",
            BoundaryType.CHAPTER_HINT,
            0.8,
        ),
        # 列表项
        (r"^\s*[\d一二三四五六七八九十]+[．.、)]", BoundaryType.LIST_ITEM, 0.7),
        (r"^\s*[-*•]\s+", BoundaryType.LIST_ITEM, 0.6),
        # 字母列表
        (r"^\s*[A-Z][．.、)]", BoundaryType.LIST_ITEM, 0.7),
        # 小节标题（括号内）
        (r"^\s*\([^)]+\)[：:\s]", BoundaryType.STRUCTURAL, 0.5),
    ]

    def detect(self, lines: List[str]) -> List[Tuple[int, BoundaryType, float]]:
        """
        检测结构化边界

        Returns:
            List of (line_index, boundary_type, confidence) tuples
        """
        boundaries = []

        for i, line in enumerate(lines):
            for pattern, btype, confidence in self.PATTERNS:
                if re.search(pattern, line):
                    boundaries.append((i, btype, confidence))
                    break

        return boundaries


class TopicTransitionDetector:
    """主题转换检测器 - 基于词汇重复和句子长度变化"""

    def __init__(self, window_size: int = 5, similarity_threshold: float = 0.3):
        self.window_size = window_size
        self.similarity_threshold = similarity_threshold

    def detect_transitions(self, sentences: List[str]) -> List[Tuple[int, float]]:
        """
        检测主题转换点

        Returns:
            List of (sentence_index, transition_strength) tuples
        """
        if len(sentences) < self.window_size * 2:
            return []

        transitions = []

        for i in range(self.window_size, len(sentences) - self.window_size):
            # 计算前一个窗口和后一个窗口的相似度
            prev_window = sentences[i - self.window_size : i]
            next_window = sentences[i : i + self.window_size]

            similarity = self._compute_window_similarity(prev_window, next_window)

            # 相似度低表示主题转换
            if similarity < self.similarity_threshold:
                transitions.append((i, 1.0 - similarity))

        return transitions

    def _compute_window_similarity(self, prev: List[str], next: List[str]) -> float:
        """计算两个窗口的词汇相似度"""
        prev_words = self._extract_words(prev)
        next_words = self._extract_words(next)

        if not prev_words or not next_words:
            return 0.0

        intersection = prev_words & next_words
        union = prev_words | next_words

        return len(intersection) / len(union) if union else 0.0

    def _extract_words(self, sentences: List[str]) -> Set[str]:
        """提取词汇集合"""
        words = set()
        for sent in sentences:
            # 简单分词：按标点和空格分割
            tokens = re.split(r'[\s，。、！？；：""' "（）【】《》,.\?!;:\[\]()]", sent)
            words.update(t for t in tokens if len(t) > 1)
        return words


class SentenceSplitter:
    """句子分割器"""

    # 中英文句子结束符
    SENTENCE_ENDINGS = r"[。！？.!?]"
    # 常见缩写（不作为句子结束）
    ABBREVIATIONS = {"Mr.", "Mrs.", "Dr.", "Prof.", "vs.", "etc.", "e.g.", "i.e."}

    def split(self, text: str) -> List[Tuple[str, int]]:
        """
        分割句子

        Returns:
            List of (sentence, start_position) tuples
        """
        sentences = []
        positions = []

        # 按段落分割
        paragraphs = text.split("\n\n")
        current_pos = 0

        for para in paragraphs:
            if not para.strip():
                continue

            # 在段落内按句子分割
            sentence_pattern = re.compile(f"({self.SENTENCE_ENDINGS}+)", re.MULTILINE)

            last_end = 0
            for match in sentence_pattern.finditer(para):
                sent = para[last_end : match.end()].strip()
                if sent:
                    sentences.append(sent)
                    positions.append(current_pos + last_end)
                last_end = match.end()

            # 处理段落末尾
            remaining = para[last_end:].strip()
            if remaining:
                sentences.append(remaining)
                positions.append(current_pos + last_end)

            current_pos += len(para) + 2  # +2 for \n\n

        return list(zip(sentences, positions)) if sentences else [(text, 0)]


class SemanticChunker:
    """
    语义边界分块器

    综合多种策略检测语义边界，适合处理：
    - 小说、叙事文本（对话边界）
    - 法律条文（结构边界）
    - 学术论文（主题转换）
    """

    def __init__(
        self,
        min_chunk_tokens: int = 100,
        max_chunk_tokens: int = 800,
        overlap_tokens: int = 100,
        enable_dialogue: bool = True,
        enable_structure: bool = True,
        enable_topic: bool = True,
    ):
        self.min_chunk_tokens = min_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens

        # 初始化各检测器
        self.dialogue_detector = DialogueDetector() if enable_dialogue else None
        self.structure_detector = (
            StructuralPatternDetector() if enable_structure else None
        )
        self.topic_detector = TopicTransitionDetector() if enable_topic else None
        self.sentence_splitter = SentenceSplitter()

    def chunk(self, text: str) -> List[SemanticChunk]:
        """
        执行语义分块

        Args:
            text: 输入文本

        Returns:
            语义块列表
        """
        if not text.strip():
            return []

        # Step 1: 检测所有语义边界
        boundaries = self._detect_all_boundaries(text)

        # Step 2: 按边界切分
        chunks = self._split_by_boundaries(text, boundaries)

        # Step 3: 合并小块，拆分大块
        chunks = self._optimize_chunks(chunks)

        return chunks

    def _detect_all_boundaries(self, text: str) -> List[SemanticBoundary]:
        """检测所有语义边界"""
        boundaries: List[SemanticBoundary] = []
        lines = text.split("\n")

        # 1. 对话边界
        if self.dialogue_detector:
            dialogues = self.dialogue_detector.detect(lines)
            for line_idx, speaker in dialogues:
                pos = sum(len(lines[i]) + 1 for i in range(line_idx))
                boundaries.append(
                    SemanticBoundary(
                        position=pos,
                        boundary_type=BoundaryType.DIALOGUE,
                        confidence=0.8,
                        label=speaker,
                    )
                )

        # 2. 结构边界
        if self.structure_detector:
            structures = self.structure_detector.detect(lines)
            for line_idx, btype, confidence in structures:
                pos = sum(len(lines[i]) + 1 for i in range(line_idx))
                boundaries.append(
                    SemanticBoundary(
                        position=pos, boundary_type=btype, confidence=confidence
                    )
                )

        # 3. 段落边界（空行）
        for i, line in enumerate(lines):
            if not line.strip():
                pos = sum(len(lines[j]) + 1 for j in range(i))
                boundaries.append(
                    SemanticBoundary(
                        position=pos,
                        boundary_type=BoundaryType.PARAGRAPH,
                        confidence=0.9,
                    )
                )

        # 4. 主题转换边界
        if self.topic_detector:
            sentences = self.sentence_splitter.split(text)
            sent_texts = [s[0] for s in sentences]
            transitions = self.topic_detector.detect_transitions(sent_texts)

            for sent_idx, strength in transitions:
                if sent_idx < len(sentences):
                    boundaries.append(
                        SemanticBoundary(
                            position=sentences[sent_idx][1],
                            boundary_type=BoundaryType.TOPIC_TRANSITION,
                            confidence=min(strength, 0.8),
                        )
                    )

        # 按位置排序
        boundaries.sort(key=lambda b: b.position)
        return boundaries

    def _split_by_boundaries(
        self, text: str, boundaries: List[SemanticBoundary]
    ) -> List[SemanticChunk]:
        """根据边界切分文本"""
        if not boundaries:
            return [
                SemanticChunk(
                    content=text,
                    start=0,
                    end=len(text),
                    boundaries=[],
                    token_count=self._estimate_tokens(text),
                    metadata={},
                )
            ]

        chunks = []
        start = 0

        for boundary in boundaries:
            # 跳过太近的边界
            if boundary.position - start < 50:  # 最小块大小
                continue

            chunk_text = text[start : boundary.position].strip()
            if chunk_text:
                chunks.append(
                    SemanticChunk(
                        content=chunk_text,
                        start=start,
                        end=boundary.position,
                        boundaries=[
                            b.boundary_type
                            for b in boundaries
                            if start <= b.position < boundary.position
                        ],
                        token_count=self._estimate_tokens(chunk_text),
                        metadata={},
                    )
                )

            start = boundary.position

        # 最后一个块
        if start < len(text):
            remaining = text[start:].strip()
            if remaining:
                chunks.append(
                    SemanticChunk(
                        content=remaining,
                        start=start,
                        end=len(text),
                        boundaries=[],
                        token_count=self._estimate_tokens(remaining),
                        metadata={},
                    )
                )

        return chunks

    def _optimize_chunks(self, chunks: List[SemanticChunk]) -> List[SemanticChunk]:
        """优化块大小"""
        if not chunks:
            return []

        optimized = []
        current = chunks[0]

        for i in range(1, len(chunks)):
            next_chunk = chunks[i]

            # 合并条件：小块且不超过最大限制
            if (
                current.token_count < self.min_chunk_tokens
                and current.token_count + next_chunk.token_count
                <= self.max_chunk_tokens
            ):
                # 合并
                current.content += "\n\n" + next_chunk.content
                current.end = next_chunk.end
                current.token_count += next_chunk.token_count
                current.boundaries.extend(next_chunk.boundaries)
            else:
                # 保存当前块
                if current.content.strip():
                    optimized.append(current)

                # 检查是否需要拆分大块
                if current.token_count > self.max_chunk_tokens:
                    split = self._split_large_chunk(current)
                    optimized.extend(split)
                else:
                    optimized.append(current)

                current = next_chunk

        # 处理最后一个块
        if current.content.strip():
            if current.token_count > self.max_chunk_tokens:
                split = self._split_large_chunk(current)
                optimized.extend(split)
            else:
                optimized.append(current)

        return optimized

    def _split_large_chunk(self, chunk: SemanticChunk) -> List[SemanticChunk]:
        """拆分过大的块"""
        sentences = self.sentence_splitter.split(chunk.content)
        splits = []
        current_content = []
        current_tokens = 0

        for sent, _ in sentences:
            sent_tokens = self._estimate_tokens(sent)

            if current_tokens + sent_tokens > self.max_chunk_tokens and current_content:
                splits.append(
                    SemanticChunk(
                        content=" ".join(current_content),
                        start=chunk.start,
                        end=chunk.end,
                        boundaries=[BoundaryType.SENTENCE],
                        token_count=current_tokens,
                        metadata={},
                    )
                )
                # 保留 overlap
                overlap_content = (
                    current_content[-2:]
                    if len(current_content) > 2
                    else current_content
                )
                current_content = overlap_content + [sent]
                current_tokens = sum(self._estimate_tokens(s) for s in current_content)
            else:
                current_content.append(sent)
                current_tokens += sent_tokens

        # 处理剩余内容
        if current_content:
            splits.append(
                SemanticChunk(
                    content=" ".join(current_content),
                    start=chunk.start,
                    end=chunk.end,
                    boundaries=[BoundaryType.SENTENCE],
                    token_count=current_tokens,
                    metadata={},
                )
            )

        return splits

    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数量"""
        # 简单估算：中文按字符，英文按单词
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        english_words = len(re.findall(r"[a-zA-Z]+", text))
        other = len(text) - chinese_chars - english_words

        return chinese_chars + english_words + other // 4


def chunk_by_semantic_boundaries(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    enable_dialogue: bool = True,
    enable_structure: bool = True,
    enable_topic: bool = True,
) -> List[Dict]:
    """
    语义边界分块的便捷函数

    与现有 pipeline 兼容的接口

    Returns:
        List of chunk dicts with content, start, end, heading_path
    """
    chunker = SemanticChunker(
        min_chunk_tokens=chunk_size // 4,
        max_chunk_tokens=chunk_size,
        overlap_tokens=chunk_overlap,
        enable_dialogue=enable_dialogue,
        enable_structure=enable_structure,
        enable_topic=enable_topic,
    )

    chunks = chunker.chunk(text)

    return [
        {
            "content": chunk.content,
            "start": chunk.start,
            "end": chunk.end,
            "heading_path": None,  # 无标题结构
            "boundary_types": [b.value for b in chunk.boundaries],
            "token_count": chunk.token_count,
            "chunking_strategy": "semantic",
        }
        for chunk in chunks
    ]


def auto_select_chunking_strategy(text: str) -> str:
    """
    自动选择分块策略

    检测文本特征，选择最合适的分块方式：
    - 有明确标题 -> 标题分块
    - 对话密集 -> 语义边界分块
    - 结构化内容 -> 语义边界分块
    - 其他 -> 混合策略
    """
    lines = text.split("\n")

    # 计算标题行比例
    heading_lines = sum(1 for line in lines if line.strip().startswith("#"))
    heading_ratio = heading_lines / len(lines) if lines else 0

    # 计算对话标记密度
    dialogue_markers = sum(1 for line in lines if re.search(r'["\"\'「」『』]', line))
    dialogue_ratio = dialogue_markers / len(lines) if lines else 0

    # 计算结构化模式
    structural_patterns = [
        r"^\s*第[一二三四五六七八九十百千零\d]+条",
        r"^\s*(?:第[一二三四五六七八九十百千零\d]+[章节编部篇])",
        r"^\s*[\d]+[．.、)]",
    ]
    structural_count = sum(
        1 for line in lines for p in structural_patterns if re.search(p, line)
    )
    structural_ratio = structural_count / len(lines) if lines else 0

    # 决策逻辑
    if heading_ratio > 0.05:
        return "heading_based"
    elif dialogue_ratio > 0.1:
        return "semantic_dialogue"
    elif structural_ratio > 0.1:
        return "semantic_structural"
    elif heading_ratio > 0.02 and structural_ratio > 0.05:
        return "heading_based"
    else:
        return "semantic_hybrid"


def smart_chunk(
    text: str, chunk_size: int = 800, chunk_overlap: int = 100, strategy: str = "auto"
) -> List[Dict]:
    """
    智能分块函数

    自动检测文本特征并选择最佳分块策略

    Args:
        text: 输入文本
        chunk_size: 目标块大小（tokens）
        chunk_overlap: 块重叠大小（tokens）
        strategy: 分块策略，"auto" 或指定策略

    Returns:
        分块列表
    """
    # 自动选择策略
    if strategy == "auto":
        strategy = auto_select_chunking_strategy(text)

    if strategy == "heading_based":
        # 使用现有的标题分块
        from .pipeline import _split_paragraphs_with_headings, _chunk_paragraphs

        para = _split_paragraphs_with_headings(text)
        chunks = _chunk_paragraphs(
            para, chunk_tokens=max(1, chunk_size), overlap_tokens=max(0, chunk_overlap)
        )

        return [
            {
                "content": c["content"],
                "start": c["start"],
                "end": c["end"],
                "heading_path": c.get("heading_path"),
                "chunking_strategy": "heading_based",
            }
            for c in chunks
        ]
    else:
        # 使用语义边界分块
        return chunk_by_semantic_boundaries(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            enable_dialogue=(strategy == "semantic_dialogue"),
            enable_structure=(strategy in ["semantic_structural", "semantic_hybrid"]),
            enable_topic=(strategy in ["semantic_hybrid"]),
        )
