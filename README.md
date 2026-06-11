# MoneyPrinterPlus 🎬

> **模块化 AI 短视频流水线** — 输入主题，输出带配音+字幕+BGM 的竖屏视频。

## 灵感来源

本项目受 [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) 启发。原项目提供了完整的 Web UI + API 后端，而 **MoneyPrinterPlus 将其核心能力拆解为 5 个独立、可组合的 CLI 节点**，更适合自动化工作流和二次开发。

## 核心优势

| 对比项 | MoneyPrinterTurbo | MoneyPrinterPlus 🆕 |
|--------|-------------------|---------------------|
| **架构** | 单体 Web UI + API | 5 个独立 CLI 节点 |
| **集成方式** | 手动操作 Web UI 或调用 API | 任意组合，脚本化/自动化调用 |
| **调试** | 黑盒，中间结果不可见 | 每节点独立可测，输入输出透明 |
| **可扩展性** | 修改需改 Web UI + API 代码 | 替换任意节点，不影响其他流程 |
| **依赖** | 全量安装（Streamlit + FastAPI + 多个 LLM SDK） | 最小依赖（edge-tts + moviepy + openai + requests） |
| **运行环境** | 需要持久后端服务 | 纯 CLI，一次运行即完成 |
| **失败恢复** | 全内存状态，后端重启丢任务 | 每步持久化到磁盘，断点续跑 |

## 流水线概览

```
用户主题 → contentNode → ttsNode → materialNode → bgmNode → videoNode → final-1.mp4
          (LLM 文案)  (TTS+字幕)  (素材下载)    (BGM 选择)  (MoviePy 合成)
```

### 节点说明

| 节点 | 功能 | 输入 | 输出 |
|------|------|------|------|
| **contentNode** | LLM 生成视频文案和搜索关键词 | 用户主题 | `content.json`（含 title, video_script, search_terms） |
| **ttsNode** | edge-tts 语音合成 + 句子级字幕 | 文案文件 | `audio.mp3` + `subtitle.srt` |
| **materialNode** | 从 Pexels/Pinterest 下载竖屏视频素材 | 搜索关键词 | `video_manifest.json` + MP4 文件 |
| **bgmNode** | 选取/管理背景音乐曲库 | BGM 风格 | `bgm_selected.json` |
| **videoNode** | MoviePy 合成：拼接素材 + 字幕叠加 + 音轨混音 | 上游全部输出 | `final-1.mp4` |

## 快速开始

```bash
# 1. 安装
git clone https://github.com/Chr1s-T/MoneyPrinterPlus.git
cd MoneyPrinterPlus
uv sync

# 2. 设置 Pexels API key（素材下载需要）
# 注册: https://www.pexels.com/api/
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

> 详细配置和参数说明见 [WORKFLOW.md](./WORKFLOW.md)。

## 环境要求

- **Python**: >= 3.12
- **FFmpeg**: 系统安装（`apt install ffmpeg` 或自动下载）
- **中文字体**: 字幕渲染需要，可通过 `--font` 指定，或将字体文件放入 `fonts/` 目录（项目自带 Charm 英文字体，含微软雅黑请自行放入 `fonts/MicrosoftYaHeiBold.ttc`）
- **BGM 曲库**: 项目自带 29 首 Pixabay 免费背景音乐（`resource/songs/`），首次运行 `python3 bgmNode/main.py --init --library-dir ./bgm_library` 即可使用
- **API Key**: Pexels API key（素材下载用，免费注册 https://www.pexels.com/api/）

## 依赖

```
edge-tts      → TTS 语音合成（免费，Microsoft Edge TTS 引擎）
moviepy       → 视频合成（基于 FFmpeg）
openai        → LLM 文案生成（兼容 DeepSeek/OpenAI 等 API）
pillow        → 字幕渲染
requests      → 素材下载
playwright    → （可选）Pinterest 素材源
```

## 节点独立使用

每个节点都可以独立运行，方便调试和集成到其他工作流：

```bash
# 只用 TTS 生成语音
python3 ttsNode/main.py --script "你好世界" --output-dir ./tts

# 只用素材下载
python3 materialNode/main.py --keywords "beautiful girl" --source pexels --output-dir ./materials

# 只合成（已有素材）
python3 videoNode/main.py --videos ./materials/*.mp4 --audio ./tts/audio.mp3 --output-dir ./video
```

## 字幕样式

默认使用电影风格字幕：
- 浅灰色文字 `#EAEAEA`
- 透明背景（无黑底）
- 黑色描边保证可读
- 句子级显示（非逐词）
- 自动换行，不出屏

## License

MIT
