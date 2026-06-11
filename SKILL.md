---
name: video-pipeline-workflow
description: "MoneyPrinterPlus 完整工作流 — 交互式配置 + 5 节点视频合成流水线。先展示配置、询问修改，再按 contentNode → ttsNode → materialNode → bgmNode → videoNode 顺序执行。"
---

# MoneyPrinterPlus 视频合成工作流

## 项目路径

克隆项目后进入项目目录。

## 完整配置一览

运行前必须展示以下配置给用户，并询问是否需要修改。

### 1. 系统配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `video_source` | `pexels` | 视频源：`pexels` 或 `pinterest` |
| `edge_tts_timeout` | `30` | TTS 超时秒数，0=禁用 |
| `pexels_api_keys` | `[通过环境变量设置]` | Pexels API key（设置 PEXELS_API_KEY 环境变量） |
| `llm_provider` | `deepseek` | LLM 提供商 |
| `llm_model` | `deepseek-v4-flash` | LLM 模型 |
| `material_directory` | `./materials` | 素材缓存目录 |
| `output_resolution` | `1080p` | 输出分辨率：`1080p` 或 `720p` |

### 2. 语音配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `tts_server` | `azure-tts-v1` | TTS 引擎，见下方可选引擎 |
| `voice_name` | `zh-CN-XiaoxiaoNeural` | 配音角色，见下方推荐列表 |
| `voice_rate` | `1.0` | 语速倍率 (0.5~2.0) |

#### TTS 引擎可选

| 引擎 | 说明 | 费用 |
|------|------|------|
| `azure-tts-v1` | edge-tts（基于 Microsoft Edge TTS） | 免费 |
| `azure` | Azure Speech Service（需配置 speech_key + speech_region） | 付费 |

#### 推荐语音包（5 男声 + 5 女声）

**女声：**

| 名字 | 角色 | 风格 | 适合场景 |
|------|------|------|----------|
| `zh-CN-XiaoxiaoNeural` | 晓晓 | 温暖亲切 | 🌟 **默认推荐**，情感故事、新闻 |
| `zh-CN-XiaoyiNeural` | 晓伊 | 活泼可爱 | 轻松话题、萌系内容 |
| `zh-CN-liaoning-XiaobeiNeural` | 晓北 | 东北幽默 | 搞笑、接地气内容 |
| `zh-TW-HsiaoChenNeural` | 晓臻 | 台湾温柔 | 情感细腻、温柔风格 |
| `zh-HK-HiuGaaiNeural` | 晓佳 | 粤语友好 | 粤语内容 |

**男声：**

| 名字 | 角色 | 风格 | 适合场景 |
|------|------|------|----------|
| `zh-CN-YunxiNeural` | 云希 | 阳光活力 | 🌟 **默认推荐**，知识分享、教程 |
| `zh-CN-YunyangNeural` | 云扬 | 专业可靠 | 新闻播报、严肃话题 |
| `zh-CN-YunjianNeural` | 云剑 | 激情澎湃 | 体育、评书、劲爆内容 |
| `zh-CN-YunxiaNeural` | 云夏 | 可爱萌系 | 儿童内容、动漫风格 |
| `zh-TW-YunJheNeural` | 云哲 | 台湾温和 | 台湾腔、轻松闲聊 |

> **注意**：voice_name 传入 edge-tts 时需去掉 `-Female`/`-Male` 后缀（如 `zh-CN-XiaoxiaoNeural` 不带 `-Female`）。

### 3. 字幕配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `text_color` | `#EAEAEA` | 浅灰色，模仿电影字幕 |
| `text_bg_color` | `None` | 透明背景，无黑色方块 |
| `stroke_color` | `#000000` | 黑色描边，保证可读 |
| `stroke_width` | `2` | 描边宽度 |
| `font_size` | `60` (1080p) / `45` (720p) | 字号适配分辨率 |
| `subtitle_position` | `bottom` | 底部位置 |
| `渲染方式` | 句子级 | 完整句子，非逐词 |

### 4. BGM 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `bgm_mood` | `calm` | 音乐风格：`calm`, `upbeat`, `romantic`, `sad`, `dramatic`, `inspiring` |
| `bgm_volume` | `0.2` | BGM 音量（20%） |
| `bgm_library_dir` | `./bgm_library` | 本地曲库目录 |

---

## 工作流执行步骤 — 标准路径

当用户提供主题，需要通过 LLM 生成文案和搜索词时走此路径。

### 前置检查

```bash
# 确认项目存在
test -d ./MoneyPrinterPlus || echo "❌ 项目不存在"

# 确认网络可用（Pexels/Pinterest 需要外网）
curl -s --max-time 5 https://www.google.com -o /dev/null -w "%{http_code}"
```

### Step 1: contentNode — 生成文案

```bash
python3 contentNode/main.py \
  --topic "主题文字" \
  --output-dir ./output/content
```

**输出**: `./output/content/content.json`
- `title`: 视频标题
- `video_script`: 200-500 字文案
- `search_terms`: 3-5 个英文搜索词

---

## 工作流执行步骤 — 替代路径（跳过 contentNode）

当用户已提供现成文案（不通过 LLM 生成），直接跳至 ttsNode。

### 替代 Step 1: 准备文案

将用户提供的文案写入一个 .txt 文件，供 ttsNode 读取。

```bash
cat > output/script.txt << 'EOF'
这里放文案内容，约 300-400 字可匹配 60-90 秒音频。
EOF
```

### 替代 Step 2: 提供搜索词

因为跳过了 contentNode，没有自动生成的 search_terms，在 materialNode 阶段需要用 `--keywords` 手动传参：

```bash
python3 materialNode/main.py \
  --source pexels \
  --keywords "keyword1" "keyword2" "keyword3" \
  --output-dir ./output/materials \
  --min-videos 12
```

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

# 或 Pinterest（默认，无需 API key）
python3 materialNode/main.py \
  --source pinterest \
  --content-file ./output/content/content.json \
  --output-dir ./output/materials \
  --min-videos 12
```

**输出**: `./output/materials/video_manifest.json` + 多个 MP4 文件

**素材数量建议**：
- 60s 音频 + 5s 每片段 → 至少 12-15 个不同视频
- 计算公式：`ceil(audio_duration / max_clip_duration) * 1.5`

### Step 4: bgmNode — 选择背景音乐

```bash
# 首次需要初始化曲库
python3 bgmNode/main.py \
  --init \
  --library-dir ./bgm_library \
  --source-dir ./resource/songs

# 选取 BGM
python3 bgmNode/main.py \
  --pick \
  --library-dir ./bgm_library \
  --mood calm \
  --output-dir ./output/bgm
```

**输出**: `./output/bgm/bgm_selected.json`（含 BGM 文件路径）

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
  --bgm-volume 0.2 \
  --max-clip 5
```

**输出**: `./output/video/final-1.mp4`

---

## 完整一键流程（跳过交互）

```bash
cd MoneyPrinterPlus

# Step 1
python3 contentNode/main.py --topic "主题" --output-dir output/content

# Step 2
python3 ttsNode/main.py --script-file output/content/content.json --output-dir output/tts

# Step 3
python3 materialNode/main.py --source pexels --content-file output/content/content.json --output-dir output/materials --min-videos 12

# Step 4
python3 bgmNode/main.py --pick --library-dir bgm_library --mood calm --output-dir output/bgm

# Step 5
python3 videoNode/main.py \
  --video-manifest output/materials/video_manifest.json \
  --audio output/tts/audio.mp3 \
  --subtitle output/tts/subtitle.srt \
  --bgm output/bgm/bgm_selected.json \
  --output-dir output/video \
  --resolution 1080p --font-size 60 --bgm-volume 0.2
```

---

## 节点间数据流

```
用户主题
   │
   ▼
┌─────────────┐     content.json      ┌──────────┐
│ contentNode  │ ────────────────────→ │  ttsNode  │
│ (LLM生成)    │   {title,             │ (TTS+Srt) │
└─────────────┘     video_script,      └──────────┘
                     search_terms}        │
                          │               ├─ audio.mp3
                          │               └─ subtitle.srt
                          │
                          ▼
                    ┌──────────────┐     video_manifest.json
                    │ materialNode  │ ←──────────────────────
                    │ (Pexels/Pin)  │     ┌──────────┐
                    └──────────────┘     │ bgmNode   │
                          │              │ (BGM选择) │
                          ▼              └──────────┘
                    ┌──────────────┐          │
                    │  videoNode    │ ←────────┘
                    │ (MoviePy合成) │
                    └──────────────┘
                          │
                          ▼
                    final-1.mp4 🎬
```

---

## 用户交互模式

调用此 skill 时，流程如下：

### Phase 1: 展示配置

展示完整配置一览表（系统/语音/字幕/BGM），让用户确认。

### Phase 2: 询问修改

提供选项：
1. "使用默认配置，直接开始"
2. "修改个别参数" → 逐个询问修改项
3. "取消"

### Phase 3: 确认主题

没有主题则问："要做什么主题的视频？"

### Phase 4: 逐节点执行

按 Step 1-5 顺序执行，每步完成后报告结果。

### Phase 5: 交付

报告最终视频路径和大小。

---

## 关键词选择参考

Pexels 素材质量取决于搜索关键词。参考下表：

| 视频主题 | 推荐关键词（英文） |
|---------|-------------------|
| 情感/搭讪 | `beautiful girl`, `attractive woman`, `fashion model`, `party girl` |
| 励志/成功 | `successful man`, `business meeting`, `office work`, `city skyline` |
| 知识/教程 | `teacher`, `student studying`, `library`, `scientist` |
| 美食/生活 | `cooking`, `food preparation`, `restaurant`, `kitchen` |
| 旅游/风景 | `travel`, `nature`, `beach`, `mountain`, `city travel` |

**注意事项**：
- 避免过于泛泛的关键词（如 `man`, `woman`, `people`）→ 返回大量静态图片
- 对中文内容，搜索词必须用英文（Pexels 索引英文标签）
- 如果某个关键词效果差，在下次运行时排除它
