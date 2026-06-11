#!/usr/bin/env python3
"""materialNode — 从搜索关键词下载视频素材。

支持视频源：
  - pinterest: 通过 Brave Search + yt-dlp 搜索下载 Pinterest 视频（默认）
  - pexels: 通过 Pexels API 下载竖屏 9:16 视频

Usage:
    # Pinterest（默认，无需 API key）
    python main.py --keywords "old money girl" --output-dir ./output

    # Pexels（需要 API key）
    python main.py --source pexels --keywords "couple walking" \
        --output-dir ./output

    # 从 content.json 读取关键词
    python main.py --source pinterest --content-file ../content/output/content.json \
        --output-dir ./output
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pinterest_client import search_and_download as pinterest_download


def load_keywords(src: str) -> list:
    """Load search keywords from a file (JSON with search_terms field) or return list."""
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        terms = data.get("search_terms") or data.get("keywords") or data.get("terms")
        if terms and isinstance(terms, list):
            return terms
    raise ValueError(f"Cannot extract search keywords from {src}")


def main():
    parser = argparse.ArgumentParser(description="Download video materials")
    parser.add_argument("--source", default="pinterest", choices=["pexels", "pinterest"],
                        help="视频源 (default: pinterest)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--keywords", nargs="+", help="搜索关键词（空格分隔）")
    group.add_argument("--content-file", help="content.json 路径（自动读取 search_terms）")

    # 通用选项
    parser.add_argument("--min-videos", type=int, default=10,
                        help="最少下载几个视频")

    # Pexels 选项
    parser.add_argument("--api-key", help="Pexels API key")
    parser.add_argument("--clip-duration", type=int, default=5,
                        help="每个片段最小时长（秒）")

    # Pinterest 选项
    parser.add_argument("--videos-per-keyword", type=int, default=5,
                        help="每个关键词下载几个视频")

    parser.add_argument("--output-dir", default="./output", help="视频保存目录")
    args = parser.parse_args()

    # Resolve keywords
    if args.content_file:
        keywords = load_keywords(args.content_file)
    else:
        keywords = args.keywords

    if not keywords:
        print("❌ 搜索关键词为空", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 搜索关键词: {keywords}")
    print(f"🎬 视频源: {args.source}")

    os.makedirs(args.output_dir, exist_ok=True)

    if args.source == "pexels":
        # ── Pexels ──
        from pexels_client import download_videos

        api_key = args.api_key or os.environ.get("PEXELS_API_KEY")
        if not api_key:
            print("❌ 未设置 Pexels API key", file=sys.stderr)
            sys.exit(1)

        videos = download_videos(
            search_terms=keywords,
            api_key=api_key,
            save_dir=args.output_dir,
            max_clip_duration=args.clip_duration,
            min_videos=args.min_videos,
        )

    elif args.source == "pinterest":
        # ── Pinterest（Brave Search + yt-dlp，无需浏览器/登录）──
        videos = pinterest_download(
            keywords=keywords,
            output_dir=args.output_dir,
            videos_per_keyword=args.videos_per_keyword,
            max_videos=args.min_videos,
        )

    if not videos:
        print("❌ 未下载到任何视频", file=sys.stderr)
        sys.exit(1)

    # Save manifest
    manifest = {
        "source": args.source,
        "count": len(videos),
        "videos": videos,
    }
    manifest_path = os.path.join(args.output_dir, "video_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 下载完成: {len(videos)} 个视频")
    print(f"📋 清单: {manifest_path}")
    for v in videos:
        size = os.path.getsize(v)
        print(f"   {os.path.basename(v)} ({size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
