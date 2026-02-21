---
name: Podcast Generate
description: Generate podcast episodes from user-provided content or by searching the web for specified topics. If user uploads a text file/article, creates a dual-host dialogue podcast (or single-host upon request). If no content is provided, searches the web for information about the user-specified topic and generates a podcast. Duration scales with content size (3-20 minutes, ~240 chars/min). Uses z-ai-web-dev-sdk for LLM script generation and TTS audio synthesis. Outputs both a podcast script (Markdown) and a complete audio file (WAV).
license: MIT
---

# Podcast Generate Skill（TypeScript 版本）

根据用户提供的资料或联网搜索结果，自动生成播客脚本与音频。

该 Skill 适用于：
- 长文内容的快速理解和播客化
- 知识型内容的音频化呈现
- 热点话题的深度解读和讨论
- 实时信息的搜索和播客制作

---

## 能力说明

### 本 Skill 可以做什么
- **从文件生成**：接收一篇资料（txt/md/docx/pdf等文本格式），生成对谈播客脚本和音频
- **联网搜索生成**：根据用户指定的主题，联网搜索最新信息，生成播客脚本和音频
- 自动控制时长，根据内容长度自动调整（3-20 分钟）
- 生成 Markdown 格式的播客脚本（可人工编辑）
- 使用 z-ai TTS 合成高质量音频并拼接为最终播客

### 本 Skill 当前不做什么
- 不生成 mp3 / 字幕 / 时间戳
- 不支持三人及以上播客角色
- 不加入背景音乐或音效

---

## 文件与职责说明

本 Skill 由以下文件组成：

- `generate.ts`
  统一入口（支持文件模式和搜索模式）
  - **文件模式**：读取用户上传的文本文件 → 生成播客
  - **搜索模式**：调用 web-search skill 获取资料 → 生成播客
  - 使用 z-ai-web-dev-sdk 进行 LLM 脚本生成
  - 使用 z-ai-web-dev-sdk 进行 TTS 音频生成
  - 自动拼接音频片段
  - 只输出最终文件

- `readme.md`
  使用说明文档

- `SKILL.md`
  当前文件，描述 Skill 能力、边界与使用约定

- `package.json`
  Node.js 项目配置与依赖

- `tsconfig.json`
  TypeScript 编译配置

---

## 输入与输出约定

### 输入（二选一）

**方式 1：文件上传**
- 一篇资料文件（txt / md / docx / pdf 等文本格式）
- 资料长度不限，Skill 会自动压缩为合适长度

**方式 2：联网搜索**
- 用户指定一个搜索主题
- 自动调用 web-search skill 获取相关内容
- 整合多个搜索结果作为资料来源

### 输出（只输出 2 个文件）

- `podcast_script.md`
  播客脚本（Markdown 格式，可人工编辑）

- `podcast.wav`
  最终拼接完成的播客音频

**不输出中间文件**（如 segments.jsonl、meta.json 等）

---

## 运行方式

### 依赖环境
- Node.js 18+
- z-ai-web-dev-sdk（已安装）
- web-search skill（用于联网搜索模式）

**不需要** z-ai CLI

### 安装依赖
```bash
npm install
```

---

## 使用示例

### 从文件生成播客

```bash
npm run generate -- --input=test_data/material.txt --out_dir=out
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

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input` | 输入资料文件路径（与 --topic 二选一） | - |
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
- **文件模式**：读取用户上传文件 → 生成播客
- **搜索模式**：调用 web-search skill → 获取资料 → 生成播客
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

## 输出示例

### podcast_script.md（片段）
```markdown
**小谱**：大家好，欢迎收听今天的播客。今天我们来聊一个有趣的话题……

**锤锤**：是啊，这个话题真的很有意思。我最近也在关注……

**小谱**：说到这里，我想给大家举个例子……
```

---

## License

MIT
