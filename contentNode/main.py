#!/usr/bin/env python3
"""contentNode — 用 LLM 从主题生成视频文案 + 搜索关键词。

Usage:
    python main.py --topic "主题文字" --output-dir ./output [--api-key sk-xxx]

输出保存到 output-dir/content.json，包含 title / video_script / search_terms。
"""

import argparse
import json
import os
import sys

# 将项目根目录加入 path，方便作为独立节点运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_client import create_client, chat
from prompt import SYSTEM_PROMPT


def main():
    parser = argparse.ArgumentParser(description="Generate video content from a topic")
    parser.add_argument("--topic", required=True, help="视频主题")
    parser.add_argument("--output-dir", default="./output", help="输出目录 (default: ./output)")
    parser.add_argument("--api-key", help="DeepSeek API key (或设置 DEEPSEEK_API_KEY 环境变量)")
    parser.add_argument("--model", default="deepseek-v4-flash", help="模型名")
    args = parser.parse_args()

    # 确保输出目录
    os.makedirs(args.output_dir, exist_ok=True)

    # 调用 LLM
    client = create_client(args.api_key)
    print(f"🤖 正在为主题「{args.topic}」生成文案与搜索词...")
    result = chat(client, SYSTEM_PROMPT, args.topic, model=args.model)

    # 解析 JSON
    try:
        data = json.loads(result)
    except json.JSONDecodeError as e:
        print(f"❌ LLM 返回的不是合法 JSON:\n{result}", file=sys.stderr)
        sys.exit(1)

    # 校验必要字段
    for field in ("title", "video_script", "search_terms"):
        if field not in data:
            print(f"❌ 缺少必要字段: {field}\n{result}", file=sys.stderr)
            sys.exit(1)

    # 写入文件
    output_file = os.path.join(args.output_dir, "content.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存到 {output_file}")

    # 输出摘要
    print(f"\n📌 标题: {data['title']}")
    print(f"📝 文案: {len(data['video_script'])} 字")
    print(f"🔑 搜索词: {', '.join(data['search_terms'])}")


if __name__ == "__main__":
    main()
