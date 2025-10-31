# UniversalLLMJudge & UniversalWinRate 使用指南

## 概述

HelloAgents 提供两个强大的通用评估模块，支持多种内容类型的智能质量评估：

- **UniversalLLMJudge**: 使用大语言模型作为评委，对单个项目进行多维度质量评估
- **UniversalWinRate**: 通过成对对比的方式，计算生成数据相对于参考数据的胜率

### 核心特性

- **两层级接口设计**:
  - **低层级API**: 提供完全的定制能力和控制权
  - **高层级API**: 提供一键式的快速评估体验
- **多模板支持**: 内置数学、代码、写作、问答四种评估模板
- **自定义维度**: 支持创建专门的评估维度和模板
- **智能字段映射**: 自动适配不同数据格式
- **批量处理**: 高效处理大规模数据评估

## 快速开始

###  UniversalLLMJudge

```python
from hello_agents import HelloAgentsLLM, UniversalLLMJudgeTool

# 1. 初始化 LLM 和评估工具
llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
tool = UniversalLLMJudgeTool(template="math", llm=llm)

# 2. 准备数据文件 data.json
# [
#   {"id": "001", "problem": "解方程: 2x + 5 = 15", "answer": "x = 5"},
#   {"id": "002", "problem": "计算: √144", "answer": "12"}
# ]

# 3. 一行代码完成评估
result = tool.run({
    "source_config": {"path": "data.json"},
    "template": "math",
    "output_dir": "results"
})

print(f"平均分: {result['summary']['average_score']}")
```

###  UniversalWinRate

```python
from hello_agents import HelloAgentsLLM, UniversalWinRateEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import EvaluationConfig

# 1. 初始化
llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
config = EvaluationConfig.load_template("writing")
evaluator = UniversalWinRateEvaluator(llm=llm, eval_config=config)

# 2. 准备对比数据
generated = [{"id": "g1", "problem": "描述春天", "answer": "春天来了，花儿开了"}]
reference = [{"id": "r1", "problem": "描述春天", "answer": "春暖花开，万物复苏"}]

# 3. 计算胜率
result = evaluator.evaluate_win_rate(generated, reference, num_comparisons=5)
print(f"生成数据胜率: {result['metrics']['win_rate']:.2%}")
```

## 评估模板

| 模板 | 用途 | 评估维度 |
|------|------|--------|
| **math** | 数学题 | correctness, clarity, completeness, difficulty_match, originality |
| **code** | 代码 | correctness, robustness, efficiency, readability, style_compliance |
| **writing** | 写作 | accuracy, coherence, richness, creativity_style, engagement |
| **qa** | 问答 | correctness, clarity, completeness, helpfulness |

## 自定义维度详解

### 创建自定义评估维度

当内置模板无法满足您的特定需求时，可以使用 `EvaluationConfig.custom()` 创建完全自定义的评估维度：

```python
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import EvaluationConfig
from hello_agents import HelloAgentsLLM, UniversalLLMJudgeEvaluator

# 创建自定义评估配置
custom_config = EvaluationConfig.custom(
    technical_accuracy="技术实现的准确性和专业性",
    innovation_solution="解决方案的创新性和独特性",
    practical_value="实际应用价值和可操作性",
    presentation_clarity="表述的清晰度和逻辑性"
)

# 使用自定义配置
llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
evaluator = UniversalLLMJudgeEvaluator(llm=llm, eval_config=custom_config)

# 评估数据
data = {
    "id": "proj_001",
    "problem": "设计一个智能家居控制系统",
    "answer": "基于IoT和边缘计算的分布式架构..."
}
result = evaluator.evaluate_single(data)

print(f"技术创新性: {result['scores']['innovation_solution']}/5")
print(f"实际价值: {result['scores']['practical_value']}/5")
```

### 自定义维度的设计原则

1. **明确具体**: 每个维度应该有明确的评估标准
2. **相互独立**: 避免维度之间的重叠和交叉
3. **可衡量性**: LLM能够理解和评估的标准
4. **业务相关性**: 与您的具体应用场景紧密相关

### 不同场景的自定义维度示例

#### 软件设计评审
```python
software_design_config = EvaluationConfig.custom(
    architecture_quality="系统架构设计的合理性和扩展性",
    security_consideration="安全考虑和风险防控措施",
    scalability="系统的可扩展性和性能规划",
    maintainability="代码的可维护性和文档完整性"
)
```

#### 商业计划评估
```python
business_plan_config = EvaluationConfig.custom(
    market_analysis="市场分析的深度和准确性",
    financial_model="财务模型的合理性和可行性",
    competitive_advantage="竞争优势的明确性和持续性",
    team_capability="团队背景和执行能力的匹配度"
)
```


### 维度权重自定义

虽然默认所有维度权重相等，但您可以通过结果后处理实现自定义权重：

```python
def apply_weighted_scores(result, weights):
    """应用自定义权重到评估结果"""
    weighted_total = 0
    total_weight = 0

    for dimension, weight in weights.items():
        if dimension in result['scores']:
            weighted_total += result['scores'][dimension] * weight
            total_weight += weight

    result['weighted_total_score'] = weighted_total / total_weight if total_weight > 0 else 0
    return result

# 使用权重: 技术准确性40%, 创新性35%, 实用价值25%
weights = {
    'technical_accuracy': 0.4,
    'innovation_solution': 0.35,
    'practical_value': 0.25
}

result = evaluator.evaluate_single(data)
weighted_result = apply_weighted_scores(result, weights)
print(f"加权总分: {weighted_result['weighted_total_score']}")
```

## 模板系统深入分析

### 各模板详细对比

#### Math 模板 - 数学问题评估

**评估维度**:
- `correctness`: 解答的数学正确性
- `clarity`: 解答过程的清晰度和逻辑性
- `completeness`: 解答的完整性和步骤的详尽程度
- `difficulty_match`: 解答难度与题目难度的匹配度
- `originality`: 解法的新颖性和创造性


**主要差异**:
强调逻辑推理的准确性和步骤的完整性，特别关注数学符号和公式的正确使用。

#### Code 模板 - 代码质量评估

**评估维度**:
- `correctness`: 代码的功能正确性和bug数量
- `robustness`: 代码的健壮性和异常处理能力
- `efficiency`: 算法效率和资源消耗
- `readability`: 代码的可读性和命名规范
- `style_compliance`: 编码规范的遵循程度


**主要差异**:
重点关注技术实现质量，包括性能、安全性和可维护性等工程化指标。

#### Writing 模板 - 写作质量评估

**评估维度**:
- `accuracy`: 内容的事实准确性和信息可靠性
- `coherence`: 文章的逻辑连贯性和结构清晰度
- `richness`: 词汇丰富性和表达多样性
- `creativity_style`: 创意性和个人风格特色
- `engagement`: 内容的吸引力和读者参与度


**主要差异**:
注重语言表达的艺术性和感染力，关注读者的主观感受和体验。

#### QA 模板 - 问答质量评估

**评估维度**:
- `correctness`: 回答的事实准确性
- `clarity`: 回答的清晰度和易理解性
- `completeness`: 回答的完整性和覆盖面
- `helpfulness`: 回答的实用价值和帮助程度


**主要差异**:
强调回答的实用性和针对性，关注是否真正解决了用户的问题。


### 模板对比实验

同一份数据使用不同模板会产生显著不同的评估结果：

```python
from hello_agents import HelloAgentsLLM, UniversalLLMJudgeEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import EvaluationConfig

llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
data = {
    "id": "example",
    "problem": "用Python实现一个快速排序算法",
    "answer": """
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
    """
}

# 使用不同模板评估同一份代码
templates = ["code", "math", "writing", "qa"]
results = {}

for template in templates:
    config = EvaluationConfig.load_template(template)
    evaluator = UniversalLLMJudgeEvaluator(llm=llm, eval_config=config)
    result = evaluator.evaluate_single(data)
    results[template] = result['total_score']

    print(f"{template}模板评分: {result['total_score']:.2f}")
    print(f"  维度分数: {result['scores']}")

# 输出示例:
# code模板评分: 4.20  (侧重技术实现)
# math模板评分: 3.80  (侧重算法逻辑)
# writing模板评分: 3.50  (侧重表达清晰)
# qa模板评分: 3.90  (侧重问题解决)
```

**关键观察**:
- **Code模板**给出最高分，因为它专门评估代码实现质量
- **Math模板**关注算法的逻辑正确性，对实现细节不太敏感
- **Writing模板**更关注代码的可读性和文档价值
- **QA模板**评估的是这个回答是否很好地解决了"实现快速排序"这个问题

## 自定义模板创建

### 扩展现有模板

当内置模板与您的需求接近但需要调整时，可以通过继承和扩展来创建新模板：

```python
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import EvaluationConfig

# 基于code模板扩展，添加AI代码特定维度
ai_code_config = EvaluationConfig.custom(
    correctness="代码功能正确性",
    robustness="代码健壮性和异常处理",
    efficiency="算法效率和性能表现",
    readability="代码可读性和命名规范",
    style_compliance="编码规范遵循程度",
    ai_safety="AI安全性和伦理考虑",
    model_efficiency="模型推理效率和资源消耗"
)

# 基于writing模板扩展，专门用于技术文档
tech_writing_config = EvaluationConfig.custom(
    accuracy="技术信息的准确性和时效性",
    coherence="文档结构逻辑性和条理性",
    richness="技术术语使用的准确性和丰富性",
    creativity_style="技术表达的创新性和风格",
    engagement="文档的吸引力和易读性",
    technical_depth="技术深度和专业性",
    practical_guidance="实操指导的价值和可行性"
)
```

### 创建领域专用模板

#### 医疗领域评估模板

```python
medical_config = EvaluationConfig.custom(
    diagnostic_accuracy="诊断准确性和医学依据",
    treatment_appropriateness="治疗方案合理性和安全性",
    patient_safety="患者安全考虑和风险评估",
    clinical_evidence="临床证据支持和科学性",
    ethical_compliance="医学伦理和合规性",
    clarity="医学表述的清晰度和专业性"
)

# 使用医疗模板评估病例分析
from hello_agents import HelloAgentsLLM, UniversalLLMJudgeEvaluator

llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
medical_evaluator = UniversalLLMJudgeEvaluator(llm=llm, eval_config=medical_config)

case_data = {
    "id": "case_001",
    "problem": "患者，男，65岁，胸痛3小时，心电图示ST段抬高",
    "answer": "初步诊断为急性心肌梗死，建议立即进行冠脉造影并准备PCI治疗"
}

result = medical_evaluator.evaluate_single(case_data)
print(f"诊断准确性: {result['scores']['diagnostic_accuracy']}/5")
print(f"治疗方案合理性: {result['scores']['treatment_appropriateness']}/5")
```

#### 法律领域评估模板

```python
legal_config = EvaluationConfig.custom(
    legal_accuracy="法律条文引用的准确性",
    reasoning_logic="法律推理的逻辑严密性",
    evidence_analysis="证据分析的充分性",
    argumentation_strength论证的说服力和强度",
    compliance="法律程序合规性",
    practical_feasibility="法律建议的可行性"
)
```

#### 教育领域评估模板

```python
education_config = EvaluationConfig.custom(
    learning_objectives_alignment="与学习目标的一致性",
    content_accuracy="知识内容的准确性",
    pedagogical_effectiveness="教学方法和策略的有效性",
    student_engagement="学生参与度和互动性",
    assessment_alignment="评估方式与目标的一致性",
    accessibility="内容的可访问性和包容性"
)
```


### 模板共享和复用

```python
# 保存自定义模板配置
def save_custom_template(config, template_name, save_path="custom_templates.json"):
    """保存自定义模板到文件"""
    import json

    templates = {}
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            templates = json.load(f)
    except FileNotFoundError:
        pass

    templates[template_name] = {
        'dimensions': config.dimensions,
        'description': f"Custom template: {template_name}"
    }

    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)

# 加载自定义模板
def load_custom_template(template_name, template_path="custom_templates.json"):
    """从文件加载自定义模板"""
    import json

    with open(template_path, 'r', encoding='utf-8') as f:
        templates = json.load(f)

    if template_name not in templates:
        raise ValueError(f"Template '{template_name}' not found")

    template_data = templates[template_name]
    return EvaluationConfig.custom(**template_data['dimensions'])

# 使用示例
save_custom_template(medical_config, "medical_evaluation")
loaded_config = load_custom_template("medical_evaluation")
```

### 标准字段名

```python
{
    "id": "item_001",      # 项目 ID
    "problem": "...",      # 题目/问题/内容
    "answer": "..."        # 答案/解答/目标
}
```

### 字段映射

当数据格式不同时，使用字段映射自动转换：

```python
# 原始数据
{"problem_id": "001", "code": "...", "expected": "..."}

# 字段映射
field_mapping = {
    "id": "problem_id",
    "problem": "code",
    "answer": "expected"
}
```

## 使用示例

### 低层级（直接使用评估器）

```python
from hello_agents import HelloAgentsLLM, UniversalLLMJudgeEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import EvaluationConfig

# 初始化
llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
config = EvaluationConfig.load_template("math")
evaluator = UniversalLLMJudgeEvaluator(llm=llm, eval_config=config)

# 评估单项
data = {"id": "001", "problem": "2+2=?", "answer": "4"}
result = evaluator.evaluate_single(data)
print(f"分数: {result['total_score']}")
print(f"维度分数: {result['scores']}")
```

### 带字段映射

```python
# 数据使用非标准字段名
data = {"item_id": "001", "code": "def add(a,b): return a+b", "expected": "sum"}

# 添加字段映射
field_mapping = {"id": "item_id", "problem": "code", "answer": "expected"}

evaluator = UniversalLLMJudgeEvaluator(
    llm=llm,
    eval_config=EvaluationConfig.load_template("code"),
    field_mapping=field_mapping
)

result = evaluator.evaluate_single(data)
```

### 高层级（使用工具）

```python
from hello_agents import HelloAgentsLLM, UniversalLLMJudgeTool

llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
tool = UniversalLLMJudgeTool(template="math", llm=llm)

# 一行代码完成所有步骤
result = tool.run({
    "source_config": {"path": "data.json"},
    "field_mapping": {"problem": "problem", "answer": "answer"},
    "template": "math",
    "max_samples": 100,
    "output_dir": "results"
})
```

### Win Rate 对比评估

```python
from hello_agents import HelloAgentsLLM, UniversalWinRateEvaluator

llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
config = EvaluationConfig.load_template("writing")

field_mapping = {"problem": "content", "answer": "target"}

evaluator = UniversalWinRateEvaluator(
    llm=llm,
    eval_config=config,
    field_mapping=field_mapping
)

# 对比生成数据和参考数据
generated = [{"id": "g1", "content": "...", "target": "..."}]
reference = [{"id": "r1", "content": "...", "target": "..."}]

result = evaluator.evaluate_win_rate(generated, reference, num_comparisons=10)
print(f"胜率: {result['win_rate']}")
```

## API层级深度对比分析

### 详细特性对比

| 特性 | 低层级API | 高层级API |
|------|-----------|-----------|
| **核心类** | `UniversalLLMJudgeEvaluator`<br/>`UniversalWinRateEvaluator` | `UniversalLLMJudgeTool` |
| **灵活性** | ⭐⭐⭐⭐⭐ 完全控制 | ⭐⭐⭐ 预设配置 |
| **易用性** | ⭐⭐⭐ 需要手动配置 | ⭐⭐⭐⭐⭐ 一键执行 |
| **数据处理** | 手动加载和预处理 | 自动加载和验证 |
| **结果输出** | 手动处理和保存 | 自动生成报告 |
| **错误处理** | 需要自行实现 | 内置降级策略 |
| **批量处理** | 手动循环实现 | 自动并行处理 |
| **进度跟踪** | 需要自行实现 | 内置进度条 |
| **配置管理** | 完全可定制 | 预设模板选择 |

### 使用场景建议

#### 选择低层级API的情况：

```python
# 场景1: 需要精细控制评估过程
from hello_agents import HelloAgentsLLM, UniversalLLMJudgeEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import EvaluationConfig

llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
custom_config = EvaluationConfig.custom(
    technical_quality="技术实现质量",
    innovation="创新程度",
    feasibility="可行性分析"
)

evaluator = UniversalLLMJudgeEvaluator(llm=llm, eval_config=custom_config)

# 可以对每个评估步骤进行精细控制
def batch_evaluate_with_retry(data_list, max_retries=3):
    results = []
    for data in data_list:
        for attempt in range(max_retries):
            try:
                result = evaluator.evaluate_single(data)
                # 自定义后处理逻辑
                result['custom_score'] = calculate_custom_score(result)
                results.append(result)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    # 自定义错误处理
                    results.append(create_error_result(data, str(e)))
    return results
```

#### 选择高层级API的情况：

```python
# 场景2: 快速原型和验证
from hello_agents import HelloAgentsLLM, UniversalLLMJudgeTool

llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
tool = UniversalLLMJudgeTool(template="code", llm=llm)

# 一行代码完成端到端评估
result = tool.run({
    "source_config": {"path": "code_samples.json"},
    "template": "code",
    "output_dir": "evaluation_results",
    "max_samples": 100,
    "field_mapping": {"problem": "question", "answer": "solution"}
})

print(f"评估完成，平均分: {result['summary']['average_score']}")
```


### API选择决策树

```
需要评估大量数据？
├─ 是 → 需要快速获得结果？
│   ├─ 是 → 使用高层级API (UniversalLLMJudgeTool)
│   └─ 否 → 使用低层级API (UniversalLLMJudgeEvaluator)
└─ 否 → 需要自定义评估维度？
    ├─ 是 → 使用低层级API + 自定义配置
    └─ 否 → 两者皆可，高层级API更简单
```

## 字段映射最佳实践

```python
# ✅ 好：清晰映射
field_mapping = {
    "id": "item_id",
    "problem": "question",
    "answer": "solution"
}

# ❌ 差：字段名不匹配或缺少
field_mapping = {
    "problem": "Question"  # 源数据中实际是 "question"
}
```

## 常见问题

**Q: 如何获取模板的所有维度？**
```python
config = EvaluationConfig.load_template("math")
print(config.get_dimension_names())
```

**Q: 字段映射区分大小写吗？**
是的，请准确匹配源数据的字段名。

**Q: 缺少必需字段会怎样？**
评估会失败。必需字段：`id`、`problem`、`answer`。

**Q: 可以自定义评估维度吗？**
当前使用预定义模板。可修改 Prompt 进行高级定制。

## 输出格式

### LLM Judge 结果
```python
{
    "problem_id": "001",
    "scores": {
        "correctness": 4.5,
        "clarity": 4.0,
        ...
    },
    "total_score": 4.3
}
```

### Win Rate 结果
```python
{
    "win_rate": 0.55,
    "loss_rate": 0.30,
    "tie_rate": 0.15,
    "wins": 11,
    "losses": 6,
    "ties": 3
}
```

## 实战案例和最佳实践

### 案例1: 教育平台作业自动批改

```python
# 场景: 在线教育平台的数学作业自动批改系统
from hello_agents import HelloAgentsLLM, UniversalLLMJudgeEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import EvaluationConfig

class MathGradingSystem:
    def __init__(self):
        self.llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
        # 使用数学模板，添加教学相关维度
        self.config = EvaluationConfig.custom(
            correctness="解题步骤和答案的数学正确性",
            clarity="解题过程的逻辑清晰度和表达规范",
            completeness="解题步骤的完整性和详细程度",
            methodology="解题方法的合理性和创新性",
            learning_outcome="体现出的数学理解和掌握程度"
        )
        self.evaluator = UniversalLLMJudgeEvaluator(
            llm=self.llm,
            eval_config=self.config,
            field_mapping={
                "id": "student_id",
                "problem": "question",
                "answer": "student_answer"
            }
        )

    def grade_homework(self, homework_data):
        """批改作业并生成详细反馈"""
        results = []

        for submission in homework_data:
            # 基础评估
            evaluation = self.evaluator.evaluate_single(submission)

            # 生成个性化反馈
            feedback = self.generate_feedback(evaluation, submission)
            evaluation['feedback'] = feedback

            # 计算改进建议
            if evaluation['total_score'] < 3.5:
                evaluation['improvement_tips'] = self.generate_improvement_tips(evaluation)

            results.append(evaluation)

        return results

    def generate_feedback(self, evaluation, submission):
        """根据评估结果生成反馈"""
        scores = evaluation['scores']

        feedback = []
        if scores['correctness'] >= 4.0:
            feedback.append("✅ 答案正确，计算无误")
        elif scores['correctness'] >= 3.0:
            feedback.append("⚠️ 基本正确，但存在一些计算错误")
        else:
            feedback.append("❌ 答案有误，需要重新检查计算过程")

        if scores['methodology'] >= 4.0:
            feedback.append("🎯 解题方法很好，思路清晰")

        return " ".join(feedback)

    def generate_improvement_tips(self, evaluation):
        """为低分学生生成改进建议"""
        tips = []
        scores = evaluation['scores']

        if scores['clarity'] < 3.5:
            tips.append("建议详细写出每一步的计算过程")
        if scores['completeness'] < 3.5:
            tips.append("请检查是否有遗漏的解题步骤")

        return tips

# 使用示例
grading_system = MathGradingSystem()
homework_submissions = [
    {
        "student_id": "stu001",
        "question": "解方程: 2x² - 8x + 6 = 0",
        "student_answer": "使用求根公式: x = [8 ± √(64-48)]/4 = [8 ± 4]/4, 所以 x = 3 或 x = 1"
    }
]

results = grading_system.grade_homework(homework_submissions)
for result in results:
    print(f"学生{result['problem_id']}: {result['total_score']:.1f}分")
    print(f"反馈: {result['feedback']}")
```



### 案例2: 内容营销质量评估

```python
# 场景: 营销团队内容质量自动化评估
from hello_agents import HelloAgentsLLM, UniversalWinRateEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import EvaluationConfig

class ContentQualityEvaluator:
    def __init__(self):
        self.llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")

        # 专门用于营销内容的评估配置
        self.marketing_config = EvaluationConfig.custom(
            brand_alignment="品牌调性契合度",
            audience_engagement="目标受众吸引力",
            value_proposition="价值主张清晰度",
            call_to_action="行动召唤效果",
            seo_optimization="SEO优化程度",
            originality="内容原创性和独特性"
        )

        self.evaluator = UniversalLLMJudgeEvaluator(
            llm=self.llm,
            eval_config=self.marketing_config
        )

    def benchmark_content(self, new_content, competitor_contents):
        """与竞品内容进行对比评估"""
        win_rate_evaluator = UniversalWinRateEvaluator(
            llm=self.llm,
            eval_config=self.marketing_config
        )

        # 计算相对于竞品的胜率
        win_rate_result = win_rate_evaluator.evaluate_win_rate(
            generated_data=new_content,
            reference_data=competitor_contents,
            num_comparisons=10
        )

        # 详细评估新内容
        detailed_evaluations = []
        for content in new_content:
            evaluation = self.evaluator.evaluate_single(content)
            detailed_evaluations.append(evaluation)

        return {
            'competitive_advantage': win_rate_result,
            'detailed_analysis': detailed_evaluations,
            'recommendations': self.generate_content_recommendations(detailed_evaluations)
        }

    def generate_content_recommendations(self, evaluations):
        """基于评估结果生成内容改进建议"""
        recommendations = []

        # 计算各维度平均分
        avg_scores = {}
        for evaluation in evaluations:
            for dimension, score in evaluation['scores'].items():
                if dimension not in avg_scores:
                    avg_scores[dimension] = []
                avg_scores[dimension].append(score)

        for dimension, scores in avg_scores.items():
            avg_score = sum(scores) / len(scores)
            if avg_score < 3.5:
                if dimension == 'brand_alignment':
                    recommendations.append("建议加强品牌元素的使用，确保与品牌调性保持一致")
                elif dimension == 'audience_engagement':
                    recommendations.append("内容吸引力不足，建议增加互动元素和情感共鸣点")
                elif dimension == 'call_to_action':
                    recommendations.append("行动召唤不够明确，建议加强CTA的设计和位置")

        return recommendations

# 使用示例
content_evaluator = ContentQualityEvaluator()

# 新营销内容
new_articles = [
    {
        "id": "article_001",
        "problem": "撰写关于人工智能发展趋势的营销文章",
        "answer": "AI正在改变我们的生活方式。从智能家居到自动驾驶..."
    }
]

# 竞品内容
competitor_articles = [
    {
        "id": "comp_001",
        "problem": "人工智能发展趋势分析",
        "answer": "人工智能技术正以前所未有的速度发展，深度学习..."
    }
]

benchmark_result = content_evaluator.benchmark_content(new_articles, competitor_articles)
print(f"相对竞品胜率: {benchmark_result['competitive_advantage']['metrics']['win_rate']:.2%}")
print("改进建议:", benchmark_result['recommendations'])
```




## 通过本指南，您应该能够：
1. 根据需求选择合适的评估模板和API层级
2. 创建自定义评估维度和专用模板
3. 处理不同格式的数据源
4. 实现高质量的自动化评估系统

