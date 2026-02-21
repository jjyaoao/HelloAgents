# Podcast Generate Skill（TypeScript 线上版本）

将一篇资料自动转化为对谈播客，时长根据内容长度自动调整（3-20 分钟，约240字/分钟）：
- 自动提炼核心内容
- 生成可编辑的播客脚本
- 使用 z-ai TTS 合成音频

这是一个使用 **z-ai-web-dev-sdk** 的 TypeScript 版本，适用于线上环境。

---

## 快速开始

### 一键生成（脚本 + 音频）

```bash
npm run generate -- --input=test_data/material.txt --out_dir=out
```

**最终输出：**
- `out/podcast_script.md` - 播客脚本（Markdown 格式）
- `out/podcast.wav` - 最终播客音频

---

## 目录结构

```text
podcast-generate/
├── readme.md               # 使用说明（本文件）
├── SKILL.md                # Skill 能力与接口约定
├── package.json            # Node.js 依赖配置
├── tsconfig.json           # TypeScript 编译配置
├── generate.ts             # ⭐ 统一入口（唯一需要的文件）
└── test_data/
    └── material.txt        # 示例输入资料
```

---

## 环境要求

- **Node.js 18+**
- **z-ai-web-dev-sdk**（已安装在环境中）

**不需要** z-ai CLI，本代码完全使用 SDK。

---

## 安装

```bash
npm install
```

---

## 使用方式

### 方式 1：从文件生成

```bash
npm run generate -- --input=material.txt --out_dir=out
```

### 方式 2：联网搜索生成

```bash
npm run generate -- --topic="最新AI新闻" --out_dir=out
npm run generate -- --topic="量子计算应用" --out_dir=out --duration=8
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input` | 输入资料文件路径，支持 txt/md/docx/pdf 等文本格式（与 --topic 二选一） | - |
| `--topic` | 搜索主题关键词（与 --input 二选一） | - |
| `--out_dir` | 输出目录（必需） | - |
| `--mode` | 播客模式：dual / single-male / single-female | dual |
| `--duration` | 手动指定分钟数（3-20）；0 表示自动 | 0 |
| `--host_name` | 主持人/主播名称 | 小谱 |
| `--guest_name` | 嘉宾名称 | 锤锤 |
| `--voice_host` | 主持音色 | xiaochen |
| `--voice_guest` | 嘉宾音色 | chuichui |
| `--speed` | 语速（0.5-2.0） | 1.0 |
| `--pause_ms` | 段间停顿毫秒数 | 200 |

---

## 使用示例

### 双人对谈播客（默认）

```bash
npm run generate -- --input=material.txt --out_dir=out
```

### 单人男声播客

```bash
npm run generate -- --input=material.txt --out_dir=out --mode=single-male
```

### 指定 5 分钟时长

```bash
npm run generate -- --input=material.txt --out_dir=out --duration=5
```

### 自定义角色名称

```bash
npm run generate -- --input=material.txt --out_dir=out --host_name=张三 --guest_name=李四
```

### 使用不同音色

```bash
npm run generate -- --input=material.txt --out_dir=out --voice_host=tongtong --voice_guest=douji
```

### 联网搜索生成播客

```bash
# 根据主题搜索并生成播客
npm run generate -- --topic="最新AI技术突破" --out_dir=out

# 指定搜索主题和时长
npm run generate -- --topic="量子计算应用场景" --out_dir=out --duration=8

# 搜索并生成单人播客
npm run generate -- --topic="气候变化影响" --out_dir=out --mode=single-male
```

---

## 可用音色

| 音色 | 特点 |
|------|------|
| xiaochen | 沉稳专业 |
| chuichui | 活泼可爱 |
| tongtong | 温暖亲切 |
| jam | 英音绅士 |
| kazi | 清晰标准 |
| douji | 自然流畅 |
| luodo | 富有感染力 |

---

## 技术架构

### generate.ts（统一入口）
- **LLM**：使用 `z-ai-web-dev-sdk` (`chat.completions.create`)
- **TTS**：使用 `z-ai-web-dev-sdk` (`audio.tts.create`)
- **不需要** z-ai CLI
- 自动拼接音频片段
- 只输出最终文件，中间文件自动清理

### LLM 调用
- System prompt：播客脚本编剧角色
- User prompt：包含资料 + 硬性约束 + 呼吸感要求
- 输出校验：字数、结构、角色标签
- 自动重试：最多 3 次

### TTS 调用
- 使用 `zai.audio.tts.create()`
- 支持自定义音色、语速
- 自动拼接多个 wav 片段
- 临时文件自动清理

---

## License

MIT
