"""pinterest_client — 搜索+下载 Pinterest 视频素材（materialNode 默认源）。

网络约束：
  - Pinterest 首页/搜索页被 GFW 封锁（浏览器和 curl 均不可直达）
  - 但 pin 详情页 (pinterest.com/pin/<id>) 可直达（CDN 走不同线路）
  - yt-dlp 内部网络处理可正常下载

搜索策略：DuckDuckGo Lite → Brave Search（curl，搜索引擎不限 ip 但限 UA）
下载策略：yt-dlp 直接下载（自动解析 m3u8 HLS → MP4，无需登录/浏览器）
"""
import json
import os
import random
import re
import subprocess
import sys
import time
from typing import List
from urllib.parse import quote


# ── 搜索引擎搜索 pin URL ─────────────────────────────────────────────


def _search_urls(keyword: str) -> List[str]:
    """多引擎搜 Pinterest pin URL，返回去重列表。"""
    all_pins = []

    for engine, url_tpl in [
        ("DuckDuckGo Lite",
         "https://lite.duckduckgo.com/lite?q={}"),
        ("Brave",
         "https://search.brave.com/search?q={}"),
    ]:
        query = f"site:pinterest.com/pin {keyword}"
        url = url_tpl.format(quote(query))
        try:
            r = subprocess.run(
                [
                    "curl", "-sL", "--max-time", "10",
                    url,
                    "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                ],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0:
                pins = set(re.findall(r"pin/(\d+)", r.stdout))
                all_pins.extend(
                    f"https://www.pinterest.com/pin/{p}/" for p in pins
                )
                if pins:
                    print(f"  {engine}: {len(pins)} 个 pin")
        except Exception:
            pass

        if len(all_pins) >= 30:
            break

    return list(dict.fromkeys(all_pins))


# ── 视频检测 & 下载（yt-dlp）──────────────────────────────────────────


def _is_video(pin_url: str) -> bool:
    """用 yt-dlp --simulate 检测 pin 是否为视频。"""
    try:
        r = subprocess.run(
            ["yt-dlp", "--simulate", "--no-warnings", pin_url],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0 and "Downloading" in r.stdout
    except (subprocess.TimeoutExpired, Exception):
        return False


def _cleanup(output_path: str):
    """清理 yt-dlp 残留的 .part/.ytdl 文件。"""
    basedir = os.path.dirname(output_path)
    prefix = os.path.basename(output_path).rsplit(".", 1)[0]
    for f in os.listdir(basedir):
        if f.startswith(prefix) and f != os.path.basename(output_path):
            try:
                os.remove(os.path.join(basedir, f))
            except OSError:
                pass


def _download_pin(pin_url: str, output_path: str) -> bool:
    """用 yt-dlp 下载单个 pin 视频。"""
    try:
        r = subprocess.run(
            [
                "yt-dlp", "-o", output_path,
                "--no-warnings", "--merge-output-format", "mp4",
                "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                pin_url,
            ],
            capture_output=True, text=True, timeout=180,
        )
        if r.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            return True
        _cleanup(output_path)
        return False
    except subprocess.TimeoutExpired:
        _cleanup(output_path)
        return False
    except Exception:
        _cleanup(output_path)
        return False


# ── 主入口 ────────────────────────────────────────────────────────────


def search_and_download(
    keywords: List[str],
    output_dir: str,
    proxy: str = "",
    videos_per_keyword: int = 10,
    max_videos: int = 20,
    **kwargs,
) -> List[str]:
    """搜索+下载 Pinterest 视频素材。

    Args:
        keywords: 搜索关键词列表（中文/英文均可）。
        output_dir: 视频保存目录。
        proxy: 已废弃，保留参数兼容。
        videos_per_keyword: 每个关键词最多取几个视频。
        max_videos: 总共最多下载几个视频。

    Returns:
        下载成功的视频文件路径列表。
    """
    os.makedirs(output_dir, exist_ok=True)
    downloaded: List[str] = []

    for kw in keywords:
        if len(downloaded) >= max_videos:
            break

        print(f"\n🔍 搜索: {kw}")
        pin_urls = _search_urls(kw)

        if not pin_urls:
            print("  ⚠ 未搜索到 pin 链接（搜索引擎限流，稍后再试）")
            continue

        print(f"  📌 共 {len(pin_urls)} 个候选，检测视频...")
        random.shuffle(pin_urls)

        kw_count = 0
        for url in pin_urls:
            if kw_count >= videos_per_keyword:
                break
            if len(downloaded) >= max_videos:
                break

            pid = url.strip("/").split("/")[-1]
            out = os.path.join(output_dir, f"pinterest-{pid}.mp4")

            if os.path.isfile(out) and os.path.getsize(out) > 0:
                downloaded.append(out)
                kw_count += 1
                continue

            print(f"  ⏳ 检测 {pid}...", end=" ", flush=True)
            if not _is_video(url):
                print("❌ 不是视频")
                continue

            print("下载...", end=" ", flush=True)
            if _download_pin(url, out):
                size = os.path.getsize(out) / 1024
                print(f"✅ ({size:.0f} KB)")
                downloaded.append(out)
                kw_count += 1
            else:
                print("❌ 下载失败")

    print(f"\n{'='*50}")
    print(f"✅ 完成: {len(downloaded)} 个视频")
    for v in downloaded:
        sz = os.path.getsize(v) / 1024
        print(f"   {os.path.basename(v)} ({sz:.0f} KB)")
    print(f"{'='*50}")

    return downloaded


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Pinterest video downloader")
    p.add_argument("--keywords", nargs="+", required=True)
    p.add_argument("--output-dir", default="./pinterest_videos")
    p.add_argument("--videos-per-keyword", type=int, default=10)
    p.add_argument("--max-videos", type=int, default=20)
    a = p.parse_args()

    v = search_and_download(
        keywords=a.keywords,
        output_dir=a.output_dir,
        videos_per_keyword=a.videos_per_keyword,
        max_videos=a.max_videos,
    )
    if v:
        manifest = os.path.join(a.output_dir, "video_manifest.json")
        with open(manifest, "w") as f:
            json.dump({"count": len(v), "videos": v, "source": "pinterest"}, f, indent=2)
        print(f"📋 {manifest}")
    else:
        print("❌ 未下载到任何视频")
        sys.exit(1)
