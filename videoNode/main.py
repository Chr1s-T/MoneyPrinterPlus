#!/usr/bin/env python3
"""videoNode — 视频合成：合并素材 + 叠加字幕 + 混音（TTS + BGM）。

将所有上游节点的输出合成为最终视频。

Usage:
    python main.py \\
        --video-manifest ./materials/video_manifest.json \\
        --audio ./tts/audio.mp3 \\
        --subtitle ./tts/subtitle.srt \\
        --bgm ./bgm/bgm_selected.json \\
        --output-dir ./output

    也可以直接传参数：
    python main.py \\
        --videos ./materials/vid-*.mp4 \\
        --audio ./tts/audio.mp3 \\
        --subtitle ./tts/subtitle.srt \\
        --bgm-file ./bgm_library/output000.mp3 \\
        --output-dir ./output
"""

import argparse
import json
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from composer import make_video, PORTRAIT_1080P, PORTRAIT_720P


def main():
    parser = argparse.ArgumentParser(description="Video composition node")
    parser.add_argument("--video-manifest", help="video_manifest.json from materialNode")
    parser.add_argument("--videos", nargs="*", help="直接传入视频文件路径")
    parser.add_argument("--audio", required=True, help="TTS 音频文件 (audio.mp3)")
    parser.add_argument("--subtitle", help="字幕文件 (subtitle.srt)")
    parser.add_argument("--bgm", help="BGM 选取结果 (bgm_selected.json)")
    parser.add_argument("--bgm-file", help="直接传入 BGM 文件路径")
    parser.add_argument("--output-dir", default="./output", help="输出目录")
    parser.add_argument("--resolution", choices=["1080p", "720p"], default="1080p",
                        help="输出分辨率 (default: 1080p)")
    parser.add_argument("--font", default="",
                        help="中文字体路径 (默认自动从原项目查找)")
    parser.add_argument("--font-size", type=int, default=45,
                        help="字幕字号 (default: 45)")
    parser.add_argument("--bgm-volume", type=float, default=0.2,
                        help="BGM 音量 (0.0-1.0, default: 0.2)")
    parser.add_argument("--voice-volume", type=float, default=1.0,
                        help="人声音量 (default: 1.0)")
    parser.add_argument("--no-subtitle", action="store_true",
                        help="不叠加字幕")
    parser.add_argument("--max-clip", type=int, default=5,
                        help="每个视频片段最大秒数")
    parser.add_argument("--sequential", action="store_true",
                        help="顺序拼接（默认随机排列）")
    parser.add_argument("--threads", type=int, default=2,
                        help="编码线程数")
    args = parser.parse_args()

    # ── Resolve video paths ──
    video_paths = []
    if args.video_manifest:
        if not os.path.isfile(args.video_manifest):
            print(f"❌ 清单文件不存在: {args.video_manifest}", file=sys.stderr)
            sys.exit(1)
        with open(args.video_manifest, "r", encoding="utf-8") as f:
            data = json.load(f)
        video_paths = data.get("videos", data if isinstance(data, list) else [])
    elif args.videos:
        for pattern in args.videos:
            matches = sorted(glob.glob(pattern))
            video_paths.extend(matches)

    if not video_paths:
        print("❌ 未指定视频素材", file=sys.stderr)
        sys.exit(1)

    # Validate files exist
    valid = [v for v in video_paths if os.path.isfile(v)]
    if not valid:
        print("❌ 所有视频文件都不存在", file=sys.stderr)
        sys.exit(1)
    if len(valid) != len(video_paths):
        print(f"⚠️  跳过 {len(video_paths) - len(valid)} 个不存在的文件")
    video_paths = valid

    print(f"🎬 视频素材: {len(video_paths)} 个文件")

    # ── Audio ──
    if not os.path.isfile(args.audio):
        print(f"❌ 音频文件不存在: {args.audio}", file=sys.stderr)
        sys.exit(1)

    # ── Subtitle ──
    subtitle_file = None
    if args.subtitle and not args.no_subtitle:
        if os.path.isfile(args.subtitle):
            subtitle_file = args.subtitle
            print(f"📝 字幕: {args.subtitle}")
        else:
            print(f"⚠️  字幕文件不存在: {args.subtitle}，跳过字幕")

    # ── BGM ──
    bgm_file = None
    if args.bgm_file:
        if os.path.isfile(args.bgm_file):
            bgm_file = args.bgm_file
    elif args.bgm:
        if os.path.isfile(args.bgm):
            with open(args.bgm, "r", encoding="utf-8") as f:
                bgm_data = json.load(f)
            bgm_path = bgm_data.get("file", "")
            if bgm_path and os.path.isfile(bgm_path):
                bgm_file = bgm_path
            else:
                print(f"⚠️  BGM 文件不存在: {bgm_path}，跳过 BGM")
        else:
            print(f"⚠️  BGM 选取文件不存在: {args.bgm}，跳过 BGM")

    if bgm_file:
        print(f"🎵 BGM: {os.path.basename(bgm_file)} (音量: {args.bgm_volume})")

    # ── Resolution ──
    target_size = PORTRAIT_720P if args.resolution == "720p" else PORTRAIT_1080P
    print(f"📐 分辨率: {target_size[0]}x{target_size[1]} (9:16)")

    # ── Font ──
    font_path = args.font
    if not font_path:
        # Auto-discover from project fonts/ directory
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
        candidates = [
            os.path.join(font_dir, "MicrosoftYaHeiBold.ttc"),
            os.path.join(font_dir, "STHeitiMedium.ttc"),
            os.path.join(font_dir, "Charm-Bold.ttf"),
            os.path.join(font_dir, "Charm-Regular.ttf"),
        ]
        # Also scan for any .ttf/.ttc files in fonts/
        if os.path.isdir(font_dir):
            for f in sorted(os.listdir(font_dir)):
                if f.endswith((".ttf", ".ttc")):
                    candidates.append(os.path.join(font_dir, f))
        for c in candidates:
            if os.path.isfile(c):
                font_path = c
                break
    if font_path:
        print(f"🔤 字体: {os.path.basename(font_path)}")

    # ── Output ──
    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, "final-1.mp4")

    print(f"\n{'='*50}")
    print(f"  开始合成视频...")
    print(f"{'='*50}\n")

    # ── Run ──
    try:
        make_video(
            video_paths=video_paths,
            audio_file=args.audio,
            output_path=output_path,
            subtitle_file=subtitle_file,
            bgm_file=bgm_file,
            target_size=target_size,
            font_path=font_path,
            max_clip_duration=args.max_clip,
            random_order=not args.sequential,
            voice_volume=args.voice_volume,
            bgm_volume=args.bgm_volume,
            threads=args.threads,
        )
    except Exception as e:
        print(f"\n❌ 合成失败: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Done ──
    final_size = os.path.getsize(output_path)
    print(f"\n{'='*50}")
    print(f"✅ 视频合成完成!")
    print(f"📁 {output_path}")
    print(f"📏 {final_size / 1024 / 1024:.1f} MB")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
