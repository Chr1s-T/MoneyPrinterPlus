#!/usr/bin/env python3
"""ttsNode — 从文案生成 TTS 音频 + 字幕。

输入：script.txt 或 content.json（含 video_script 字段）
输出：audio.mp3, subtitle.srt

Usage:
    python main.py --script "文案文字" --output-dir ./output
    python main.py --script-file ./content.json --output-dir ./output
    python main.py --script-file ./script.txt --output-dir ./output
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tts import generate_audio, save_srt


def load_script(src: str) -> str:
    """Load script text from a file or return raw string."""
    if not os.path.isfile(src):
        return src  # raw string

    with open(src, "r", encoding="utf-8") as f:
        content = f.read()

    # Try JSON content with video_script field
    if src.endswith(".json") or src.endswith(".content.json"):
        try:
            data = json.loads(content)
            if "video_script" in data:
                return data["video_script"]
        except json.JSONDecodeError:
            pass

    # Fallback: treat entire file as script text
    return content.strip()


def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio + subtitles")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--script", help="文案原文（直接传入字符串）")
    group.add_argument("--script-file", help="文案文件路径（.txt 或 .json）")
    parser.add_argument("--output-dir", default="./output", help="输出目录")
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural-Female",
                        help="edge-tts voice name")
    parser.add_argument("--rate", type=float, default=1.0,
                        help="语速倍率 (1.0=正常)")
    parser.add_argument("--no-subtitle", action="store_true",
                        help="跳过字幕生成")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load script
    if args.script:
        script_text = args.script
    else:
        script_text = load_script(args.script_file)

    if not script_text:
        print("❌ 文案为空", file=sys.stderr)
        sys.exit(1)

    print(f"📝 文案长度: {len(script_text)} 字")

    # --- TTS ---
    audio_path = os.path.join(args.output_dir, "audio.mp3")
    print(f"🎤 正在生成语音 (voice: {args.voice}, rate: {args.rate})...")
    sub_maker = generate_audio(
        text=script_text,
        voice_file=audio_path,
        voice_name=args.voice,
        voice_rate=args.rate,
    )

    if not sub_maker:
        print("❌ TTS 生成失败", file=sys.stderr)
        sys.exit(1)

    audio_size = os.path.getsize(audio_path)
    print(f"✅ 音频已保存: {audio_path} ({audio_size / 1024:.0f} KB)")

    # --- Subtitle ---
    if not args.no_subtitle:
        srt_path = os.path.join(args.output_dir, "subtitle.srt")
        save_srt(sub_maker, srt_path)
        with open(srt_path, "r", encoding="utf-8") as f:
            srt_lines = f.read().strip().count("\n") + 1
        print(f"✅ 字幕已保存: {srt_path} ({srt_lines} 行)")
    else:
        print("⏭️  跳过字幕生成")


if __name__ == "__main__":
    main()
