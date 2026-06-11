# MoneyPrinterPlus 🎬 — Hermes Agent Skill

> **Hermes Agent skill：AI 短视频自动生成流水线**  
> 输入主题，输出带配音+字幕+BGM 的竖屏视频。5 个独立节点按序执行，每步可测可恢复。

## 这是什么

**MoneyPrinterPlus** 是一个 [Hermes Agent](https://hermes-agent.nousresearch.com) skill，将视频创作拆解为 5 个可组合的 CLI 节点：

```
用户主题 → contentNode → ttsNode → materialNode → bgmNode → videoNode → final-1.mp4
          (LLM 文案)  (TTS+字幕)  (素材下载)    (BGM 选择)  (MoviePy 合成)
```

Hermes Agent 加载此 skill 后，即可按工作流自动执行完整流水线。

### 节点一览

| 节点 | 功能 | 输入 | 输出 |
|------|------|------|------|
| **contentNode** | LLM 生成视频文案和搜索关键词 | 用户主题 | `content.json` |
| **ttsNode** | edge-tts 语音合成 + 句子级字幕 | 文案 | `audio.mp3` + `subtitle.srt` |
| **materialNode** | Pexels/Pinterest 下载竖屏视频素材 | 搜索关键词 | `video_manifest.json` + MP4 |
| **bgmNode** | 选取/管理背景音乐曲库 | BGM 风格 | `bgm_selected.json` |
| **videoNode** | MoviePy 合成：拼接素材 + 字幕 + 混音 | 上游全部输出 | `final-1.mp4` |

## 灵感来源

受 [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) 启发。原项目是完整的 Web UI + API 后端，**MoneyPrinterPlus 将其核心能力拆解为独立 CLI 节点**，更适合 Hermes Agent 这类 AI Agent 自动化调用。

### 相比 MoneyPrinterTurbo 的优势

| 对比项 | MoneyPrinterTurbo | MoneyPrinterPlus 🆕 |
|--------|-------------------|---------------------|
| **定位** | Web UI + API 后端 | Hermes Agent skill / CLI 流水线 |
| **集成方式** | 手动操作 UI 或调 API | AI Agent 自动编排，一键执行 |
| **调试** | 黑盒，中间结果不可见 | 每节点独立可测，输入输出透明 |
| **可扩展性** | 修改需改全栈代码 | 替换任意节点，不影响其他流程 |
| **依赖** | 全量安装（Streamlit + FastAPI + 多 LLM SDK） | 最小依赖（edge-tts + moviepy + openai + requests） |
| **运行环境** | 需要持久后端服务 | 纯 CLI，一次运行即完成 |
| **失败恢复** | 全内存状态，后端重启丢任务 | 每步持久化到磁盘，断点续跑 |

## 快速开始

### 作为 Hermes Agent skill 使用

在 Hermes Agent 中加载 skill 后，告诉 agent：

> "用 MoneyPrinterPlus 生成一个关于 xxx 主题的视频"

Agent 会自动展示配置、询问修改、按序执行 5 个节点。

### 纯 CLI 使用

```bash
# 1. 安装
git clone https://github.com/Chr1s-T/MoneyPrinterPlus.git
cd MoneyPrinterPlus
uv sync

# 2. 设置 Pexels API key（素材下载需要）
export PEXELS_API_KEY="your_key_here"

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

> 详细参数说明和工作流交互流程见 [WORKFLOW.md](./WORKFLOW.md)。

## 环境要求

- **Python**: >= 3.12
- **FFmpeg**: 系统安装（`apt install ffmpeg` 或自动下载）
- **中文字体**: 字幕渲染需要，可通过 `--font` 指定，或将字体文件放入 `fonts/` 目录（已含 Charm 英文字体，含微软雅黑请放入 `fonts/MicrosoftYaHeiBold.ttc`）
- **BGM 曲库**: 项目自带 29 首 Pixabay 免费 BGM（`resource/songs/`），运行 `python3 bgmNode/main.py --init --library-dir ./bgm_library` 初始化即可
- **API Key**: Pexels API key（免费注册 https://www.pexels.com/api/）

## 依赖

```
edge-tts      → TTS 语音合成（免费，Microsoft Edge TTS 引擎）
moviepy       → 视频合成（基于 FFmpeg）
openai        → LLM 文案生成（兼容 DeepSeek/OpenAI）
pillow        → 字幕渲染
requests      → 素材下载
playwright    → （可选）Pinterest 素材源
```

## 字幕样式

默认电影风格字幕：
- 浅灰色 `#EAEAEA`、透明背景、黑色描边
- 句子级显示（非逐词）、自动换行

## License

MIT
