# MoneyPrinterPlus 视频合成工作流 — Hermes Agent Skill

## 简介

一份模块化的 AI 视频流水线（Hermes Agent skill），将用户主题转化为带配音、字幕、BGM 的竖屏短视频。
流水线由 5 个独立节点串联：文案生成 → 语音+字幕 → 视频素材 → 背景音乐 → 最终合成。

加载此 skill 后，Hermes Agent 会先展示配置、询问修改，再按序执行 5 个节点。

## 完整配置一览

### 1. 系统配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `video_source` | `pexels` | 视频源：`pexels` 或 `pinterest` |
| `llm_model` | `deepseek-v4-flash` | LLM 模型 |
| `output_resolution` | `1080p` | 输出分辨率：`1080p` 或 `720p` |

### 2. 语音配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `tts_server` | `azure-tts-v1` | TTS 引擎（edge-tts，免费） |
| `voice_name` | `zh-CN-XiaoxiaoNeural` | 配音角色 |
| `voice_rate` | `1.0` | 语速倍率 (0.5~2.0) |

#### 推荐语音包（5 男声 + 5 女声）

| 名字 | 角色 | 风格 | 适合场景 |
|------|------|------|----------|
| `zh-CN-XiaoxiaoNeural` | 晓晓·女 | 温暖亲切 | 情感故事、新闻 |
| `zh-CN-XiaoyiNeural` | 晓伊·女 | 活泼可爱 | 轻松话题 |
| `zh-CN-liaoning-XiaobeiNeural` | 晓北·女 | 东北幽默 | 搞笑内容 |
| `zh-TW-HsiaoChenNeural` | 晓臻·女 | 台湾温柔 | 情感细腻 |
| `zh-HK-HiuGaaiNeural` | 晓佳·女 | 粤语 | 粤语内容 |
| `zh-CN-YunxiNeural` | 云希·男 | 阳光活力 | 知识分享、教程 |
| `zh-CN-YunyangNeural` | 云扬·男 | 专业可靠 | 新闻播报 |
| `zh-CN-YunjianNeural` | 云剑·男 | 激情澎湃 | 体育、评书 |
| `zh-CN-YunxiaNeural` | 云夏·男 | 可爱 | 儿童内容 |
| `zh-TW-YunJheNeural` | 云哲·男 | 台湾温和 | 台湾腔 |

### 3. 字幕配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `text_color` | `#EAEAEA` | 浅灰色，模仿电影字幕 |
| `text_bg_color` | `None` | 透明背景 |
| `stroke_color` | `#000000` | 黑色描边 |
| `stroke_width` | `2` | 描边宽度 |
| `font_size` | `60` (1080p) / `45` (720p) | 字号适配分辨率 |
| `subtitle_position` | `bottom` | 底部位置 |
| 渲染方式 | 句子级 | 完整句子，非逐词 |

### 4. BGM 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `bgm_mood` | `calm` | 音乐风格：`calm`, `upbeat`, `romantic`, `sad`, `dramatic`, `inspiring` |
| `bgm_volume` | `0.2` | BGM 音量（20%） |

---

## 工作流执行步骤

### Step 1: contentNode — 生成文案

```bash
python3 contentNode/main.py \
  --topic "你的视频主题" \
  --output-dir ./output/content
```

**输出**: `./output/content/content.json`
- `title`: 视频标题
- `video_script`: 200-500 字文案
- `search_terms`: 3-5 个英文搜索词

> **替代路径**：如果已有现成文案，跳过 Step 1，直接写为 `.txt` 文件供 ttsNode 读取。

### Step 2: ttsNode — 生成语音 + 字幕

```bash
python3 ttsNode/main.py \
  --script-file ./output/content/content.json \
  --output-dir ./output/tts \
  --voice zh-CN-XiaoxiaoNeural \
  --rate 1.0
```

**输出**:
- `./output/tts/audio.mp3` — TTS 音频
- `./output/tts/subtitle.srt` — 句子级字幕

### Step 3: materialNode — 下载视频素材

```bash
# Pexels（需要设置 PEXELS_API_KEY 环境变量或 --api-key）
python3 materialNode/main.py \
  --source pexels \
  --content-file ./output/content/content.json \
  --output-dir ./output/materials \
  --min-videos 12

# 或 Pinterest（无需 API key）
python3 materialNode/main.py \
  --source pinterest \
  --content-file ./output/content/content.json \
  --output-dir ./output/materials \
  --min-videos 12
```

**输出**: `./output/materials/video_manifest.json` + 多个 MP4 文件

> **关键词选择**：Pexels 素材质量取决于关键词。参考下表：

| 视频主题 | 推荐关键词（英文） |
|---------|-------------------|
| 情感/搭讪 | `beautiful girl`, `attractive woman`, `fashion model`, `party girl` |
| 励志/成功 | `successful man`, `business meeting`, `office work`, `city skyline` |
| 知识/教程 | `teacher`, `student studying`, `library`, `scientist` |
| 美食/生活 | `cooking`, `food preparation`, `restaurant`, `kitchen` |
| 旅游/风景 | `travel`, `nature`, `beach`, `mountain`, `city travel` |

**素材数量**：`ceil(音频时长 / 5) * 1.5`，60s 音频建议至少 12-15 个。

### Step 4: bgmNode — 选择背景音乐

```bash
# 首次需要初始化曲库（提供 MP3 目录）
python3 bgmNode/main.py \
  --init \
  --library-dir ./bgm_library \
  --source-dir ./path/to/your/music

# 选取 BGM
python3 bgmNode/main.py \
  --pick \
  --library-dir ./bgm_library \
  --mood calm \
  --output-dir ./output/bgm
```

**输出**: `./output/bgm/bgm_selected.json`

### Step 5: videoNode — 视频合成

```bash
python3 videoNode/main.py \
  --video-manifest ./output/materials/video_manifest.json \
  --audio ./output/tts/audio.mp3 \
  --subtitle ./output/tts/subtitle.srt \
  --bgm ./output/bgm/bgm_selected.json \
  --output-dir ./output/video \
  --resolution 1080p \
  --font-size 60 \
  --bgm-volume 0.2
```

**输出**: `./output/video/final-1.mp4`

---

## 完整一键流程

```bash
# 1. 生成文案
python3 contentNode/main.py --topic "主题" --output-dir output/content

# 2. 语音 + 字幕
python3 ttsNode/main.py --script-file output/content/content.json --output-dir output/tts

# 3. 下载素材
python3 materialNode/main.py --source pexels --content-file output/content/content.json --output-dir output/materials --min-videos 12

# 4. BGM
python3 bgmNode/main.py --pick --library-dir bgm_library --mood calm --output-dir output/bgm

# 5. 合成
python3 videoNode/main.py \
  --video-manifest output/materials/video_manifest.json \
  --audio output/tts/audio.mp3 \
  --subtitle output/tts/subtitle.srt \
  --bgm output/bgm/bgm_selected.json \
  --output-dir output/video
```

---

## 数据流

```
用户主题
   │
   ▼
┌─────────────┐     content.json      ┌──────────┐
│ contentNode  │ ────────────────────→ │  ttsNode  │
│ (LLM 生成)   │   {title,             │ (TTS+SRT) │
└─────────────┘     video_script,      └──────────┘
                     search_terms}        │
                          │               ├─ audio.mp3
                          │               └─ subtitle.srt
                          │
                          ▼
                    ┌──────────────┐
                    │ materialNode  │
                    │ (素材下载)    │
                    └──────────────┘
                          │              ┌──────────┐
                          ▼              │ bgmNode   │
                    ┌──────────────┐     │ (BGM 选择)│
                    │  videoNode    │ ←──┘           │
                    │ (MoviePy 合成)│    └──────────┘
                    └──────────────┘
                          │
                          ▼
                    final-1.mp4 🎬
```

---

## 环境准备

```bash
# 1. 安装依赖
cd MoneyPrinterPlus
uv sync

# 2. 设置 API key（Pexels 素材需要）
export PEXELS_API_KEY="你的 Pexels API key"

# 3. 准备中文字体
# 视频字幕需要中文字体，通过 --font 指定：
# python3 videoNode/main.py ... --font /path/to/your/font.ttc

# 4. 准备 BGM 曲库
# 将 MP3 文件放在一个目录，然后：
python3 bgmNode/main.py --init --library-dir ./bgm_library --source-dir ./my-music
```
