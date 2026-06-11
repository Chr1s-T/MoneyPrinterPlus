#!/usr/bin/env python3
"""musicNode — 背景音乐 (BGM) 选择与管理。

管理 BGM 曲库，按风格/情绪选取背景音乐用于视频合成。

Usage:
    # 初始化曲库（从 MoneyPrinterTurbo 拷贝）
    python main.py --init --library-dir ./bgm_library

    # 从 Pixabay 下载更多 BGM
    python main.py --init --library-dir ./bgm_library --pixabay-key xxx --mood calm

    # 选取一首 BGM
    python main.py --pick --library-dir ./bgm_library --mood calm

    # 查看曲库
    python main.py --list --library-dir ./bgm_library
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bgm_library import (
    MOOD_TAGS,
    init_library,
    pick_bgm,
    scan_library,
)


def main():
    parser = argparse.ArgumentParser(description="Background music management")
    parser.add_argument("--library-dir", default="./bgm_library",
                        help="BGM 曲库目录")
    parser.add_argument("--init", action="store_true",
                        help="初始化曲库（复制已有 MP3 + 可选下载）")
    parser.add_argument("--source-dir",
                        default="./resource/songs",
                        help="源 MP3 目录（用于 --init 时复制）")
    parser.add_argument("--pixabay-key", help="Pixabay API key（用于在线下载）")
    parser.add_argument("--mood", default="calm", choices=list(MOOD_TAGS.keys()),
                        help="音乐风格/情绪")
    parser.add_argument("--download-count", type=int, default=5,
                        help="从 Pixabay 下载的数量")
    parser.add_argument("--pick", action="store_true",
                        help="从曲库中选取一首 BGM")
    parser.add_argument("--list", action="store_true",
                        help="列出曲库中的 BGM")
    parser.add_argument("--output-dir", default="./output",
                        help="输出目录（--pick 的结果保存到这里）")
    args = parser.parse_args()

    if args.init:
        print(f"🎵 初始化 BGM 曲库: {args.library_dir}")
        count = init_library(
            target_dir=args.library_dir,
            source_dir=args.source_dir,
            pixabay_key=args.pixabay_key,
            mood=args.mood,
            count=args.download_count,
        )
        print(f"✅ 曲库就绪: {count} 首")

    if args.list:
        tracks = scan_library(args.library_dir)
        if not tracks:
            print("❌ 曲库为空，先运行 --init")
            sys.exit(1)
        print(f"\n📀 BGM 曲库 ({len(tracks)} 首):")
        for t in tracks:
            size_kb = t["size"] / 1024
            print(f"   🎵 {t['name']}.mp3 ({size_kb:.0f} KB)")

    if args.pick:
        tracks = scan_library(args.library_dir)
        if not tracks:
            print("❌ 曲库为空，先运行 --init", file=sys.stderr)
            sys.exit(1)

        # If Pixabay was just initialized, we might also have search results
        # to enrich selection. For now, just pick from local.
        chosen = pick_bgm(tracks, mood=args.mood)
        if not chosen:
            print("❌ 无法选取 BGM", file=sys.stderr)
            sys.exit(1)

        print(f"\n🎶 选取的 BGM: {chosen['name']}.mp3 ({chosen['size'] / 1024:.0f} KB)")

        # Save result
        os.makedirs(args.output_dir, exist_ok=True)
        result = {
            "file": chosen["file"],
            "name": chosen["name"],
            "size": chosen["size"],
            "source": chosen.get("source", "local"),
            "duration_hint": "unknown",
        }

        # Try to get duration with ffprobe
        import subprocess
        try:
            dur = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "csv=p=0", chosen["file"]],
                capture_output=True, text=True, timeout=10,
            )
            if dur.returncode == 0 and dur.stdout.strip():
                result["duration_hint"] = f"{float(dur.stdout.strip()):.1f}s"
        except Exception:
            pass

        result_path = os.path.join(args.output_dir, "bgm_selected.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"📋 选取结果: {result_path}")
        print(f"⏱️  时长: {result['duration_hint']} (视频合成时会自动循环匹配)")

    if not any([args.init, args.list, args.pick]):
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
