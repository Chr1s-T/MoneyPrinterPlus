# MoneyPrinterPlus 🎬

> **AI Video Generation Pipeline — Modular CLI workflow for short-form portrait videos**
> **AI 短视频自动生成流水线 — 模块化 CLI 工作流**

[English](#english) | [中文](#chinese)

---

<a name="english"></a>

## 🇬🇧 English

**MoneyPrinterPlus** is a modular, node-based CLI pipeline that turns a topic into a fully-produced short video with voiceover, subtitles, and background music.

```
Topic → contentNode → ttsNode → materialNode → bgmNode → videoNode → final-1.mp4
       (LLM script) (TTS+subs) (video assets)  (BGM pick)  (MoviePy compose)
```

### Compatible AI Agents

This pipeline is designed to work with **any AI coding agent** that can execute CLI commands and read markdown workflow files:

| Agent | How to use |
|-------|-----------|
| **Hermes Agent** | Load the `video-pipeline-workflow` skill — agent auto-runs the full pipeline |
| **OpenClaw** | Load from SKILL.md — follows the workflow step by step |
| **Claude Code** | Reference WORKFLOW.md — execute each node via CLI |
| **Cline / Roo Code** | Read SKILL.md as a rule, then execute the pipeline |
| **Codex CLI** | Follow WORKFLOW.md commands sequentially |
| **Cursor / Windsurf** | Reference the markdown docs as context |
| **Any CLI-capable agent** | Run the bash commands directly |

### Why MoneyPrinterPlus?

Inspired by [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) (a full Web UI + API server), this project **decomposes video creation into 5 independent CLI nodes** — each testable, replaceable, and scriptable.

| Feature | MoneyPrinterTurbo | MoneyPrinterPlus |
|---------|-------------------|------------------|
| Architecture | Monolithic Web UI + API | 5 independent CLI nodes |
| Integration | Manual UI / REST API | Any AI agent or shell script |
| Debugging | Black box | Each node independently testable |
| Extensibility | Modify full stack | Swap any node without touching others |
| Dependencies | Heavy (Streamlit + FastAPI + many SDKs) | Minimal (edge-tts + moviepy + openai + requests) |
| Runtime | Persistent backend required | CLI — one-shot execution |
| Failure recovery | In-memory state (lost on restart) | Persistent to disk, resume-able |

### Quick Start

```bash
# 1. Install
git clone https://github.com/Chr1s-T/MoneyPrinterPlus.git
cd MoneyPrinterPlus
pip install -r requirements.txt  # or: uv sync

# 2. Set API keys
export PEXELS_API_KEY="your_pexels_key"   # https://www.pexels.com/api/
export DEEPSEEK_API_KEY="your_deepseek_key"  # or any OpenAI-compatible API

# 3. Generate a video
python3 contentNode/main.py --topic "Your topic" --output-dir output/content
python3 ttsNode/main.py --script-file output/content/content.json --output-dir output/tts
python3 materialNode/main.py --source pexels --content-file output/content/content.json --output-dir output/materials --min-videos 12
python3 bgmNode/main.py --pick --library-dir bgm_library --mood calm --output-dir output/bgm
python3 videoNode/main.py \
  --video-manifest output/materials/video_manifest.json \
  --audio output/tts/audio.mp3 \
  --subtitle output/tts/subtitle.srt \
  --bgm output/bgm/bgm_selected.json \
  --output-dir output/video
```

### Pipeline Overview

| Node | Function | Input | Output |
|------|----------|-------|--------|
| **contentNode** | LLM generates script + keywords | User topic | `content.json` |
| **ttsNode** | edge-tts TTS + sentence-level SRT | Script file | `audio.mp3` + `subtitle.srt` |
| **materialNode** | Download portrait videos (Pexels/Pinterest) | Keywords | `video_manifest.json` + MP4s |
| **bgmNode** | Select BGM from local library | Mood tag | `bgm_selected.json` |
| **videoNode** | MoviePy compose: clips + subs + audio + BGM | All above | `final-1.mp4` |

### Subtitles Style

- Cinema-style: `#EAEAEA` light gray, transparent background, black stroke
- Sentence-level display (not word-by-word)
- Auto-wrapping, safe margins (7% bottom, 5% top)

### Requirements

- **Python**: >= 3.12
- **FFmpeg**: system install (`apt install ffmpeg`)
- **Chinese font**: put any `.ttc`/`.ttf` in `fonts/` or use `--font`
- **BGM**: 29 free Pixabay tracks included in `resource/songs/`
- **API Keys**: Pexels (free), LLM provider of your choice

### License

MIT

---

<a name="chinese"></a>

## 🇨🇳 中文

**MoneyPrinterPlus** 是一个模块化的 AI 视频生成流水线，将用户主题转化为带配音、字幕、BGM 的竖屏短视频。

```
主题 → contentNode → ttsNode → materialNode → bgmNode → videoNode → final-1.mp4
     (LLM 文案)   (TTS+字幕)  (素材下载)    (BGM 选择)  (MoviePy 合成)
```

### 支持的 AI Agent

本流水线设计为与**任何能执行 CLI 命令的 AI Agent** 配合使用：

| Agent | 使用方式 |
|-------|---------|
| **Hermes Agent** | 加载 `video-pipeline-workflow` skill，自动执行完整流程 |
| **OpenClaw** | 加载 SKILL.md，按步骤执行 |
| **Claude Code** | 参考 WORKFLOW.md，逐节点 CLI 执行 |
| **Cline / Roo Code** | 将 SKILL.md 作为 rule 载入，按流程执行 |
| **Codex CLI** | 按 WORKFLOW.md 顺序执行命令 |
| **Cursor / Windsurf** | 将文档作为上下文参考 |
| **任意 CLI Agent** | 直接运行 bash 命令 |

### 灵感来源

受 [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) 启发。原项目是完整的 Web UI + API 后端，**MoneyPrinterPlus 将核心能力拆解为 5 个独立 CLI 节点**，更适合 AI Agent 自动化调用。

### 相比 MoneyPrinterTurbo 的优势

| 对比项 | MoneyPrinterTurbo | MoneyPrinterPlus |
|--------|-------------------|------------------|
| **定位** | Web UI + API 后端 | 任意 AI Agent 可调用的 CLI 流水线 |
| **集成方式** | 手动操作 UI 或调 API | Agent 自动编排，一键执行 |
| **调试** | 黑盒，中间结果不可见 | 每节点独立可测，输入输出透明 |
| **可扩展性** | 修改需改全栈代码 | 替换任意节点不影响其他流程 |
| **依赖** | 全量安装（Streamlit + FastAPI + 多 LLM SDK） | 最小依赖（edge-tts + moviepy + openai + requests） |
| **运行环境** | 需要持久后端服务 | 纯 CLI，一次运行即完成 |
| **失败恢复** | 全内存状态，后端重启丢任务 | 每步持久化到磁盘，断点续跑 |

### 快速开始

```bash
# 1. 安装
git clone https://github.com/Chr1s-T/MoneyPrinterPlus.git
cd MoneyPrinterPlus
pip install -r requirements.txt  # 或: uv sync

# 2. 设置 API key
export PEXELS_API_KEY="你的Pexels密钥"      # 免费注册: https://www.pexels.com/api/
export DEEPSEEK_API_KEY="你的DeepSeek密钥"   # 或任意 OpenAI 兼容 API

# 3. 一键生成视频
python3 contentNode/main.py --topic "你的主题" --output-dir output/content
python3 ttsNode/main.py --script-file output/content/content.json --output-dir output/tts
python3 materialNode/main.py --source pexels --content-file output/content/content.json --output-dir output/materials --min-videos 12
python3 bgmNode/main.py --pick --library-dir bgm_library --mood calm --output-dir output/bgm
python3 videoNode/main.py \
  --video-manifest output/materials/video_manifest.json \
  --audio output/tts/audio.mp3 \
  --subtitle output/tts/subtitle.srt \
  --bgm output/bgm/bgm_selected.json \
  --output-dir output/video
```

> 完整配置和参数说明见 [WORKFLOW.md](./WORKFLOW.md) | 详细工作流交互见 [SKILL.md](./SKILL.md)

### 节点说明

| 节点 | 功能 | 输入 | 输出 |
|------|------|------|------|
| **contentNode** | LLM 生成文案和搜索关键词 | 用户主题 | `content.json` |
| **ttsNode** | edge-tts 语音合成 + 句子级字幕 | 文案文件 | `audio.mp3` + `subtitle.srt` |
| **materialNode** | Pexels/Pinterest 下载竖屏素材 | 搜索关键词 | `video_manifest.json` + MP4 |
| **bgmNode** | 选取/管理 BGM 曲库 | 音乐风格 | `bgm_selected.json` |
| **videoNode** | MoviePy 合成：拼接+字幕+混音 | 上游全部输出 | `final-1.mp4` |

### 字幕样式

- 电影风格：`#EAEAEA` 浅灰色、透明背景、黑色描边
- 句子级显示（非逐词）
- 自动换行 + 安全边距（底部 7%、顶部 5%）

### 环境要求

- **Python**: >= 3.12
- **FFmpeg**: 系统安装（`apt install ffmpeg`）
- **中文字体**: 放入 `fonts/` 目录或通过 `--font` 指定（已含 Charm 英文字体）
- **BGM**: 项目自带 29 首 Pixabay 免费背景音乐（`resource/songs/`）
- **API Key**: Pexels（免费）+ 任意 LLM API

### 节点独立使用

```bash
# 只用 TTS
python3 ttsNode/main.py --script "你好世界" --output-dir ./tts

# 只下载素材
python3 materialNode/main.py --keywords "beautiful girl" --source pexels --output-dir ./materials

# 只合成
python3 videoNode/main.py --videos ./materials/*.mp4 --audio ./tts/audio.mp3 --output-dir ./video
```

### License

MIT
