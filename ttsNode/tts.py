"""TTS (Text-to-Speech) using edge-tts (Azure TTS V1).

Inspired by MoneyPrinterTurbo's voice.py implementation.
Generates audio.mp3 and returns a subtitle maker for SRT generation.
"""

import asyncio
import inspect
import math
import os

import edge_tts
from edge_tts import SubMaker


# ── public helpers ──────────────────────────────────────────────────


def parse_voice_name(voice_name: str) -> str:
    """Normalize voice name to edge-tts format."""
    # MoneyPrinterTurbo-style: "zh-CN-XiaoxiaoNeural-Female" → "zh-CN-XiaoxiaoNeural"
    voice_name = voice_name.replace("-Female", "").replace("-Male", "").strip()
    return voice_name


def convert_rate_to_percent(rate: float) -> str:
    """Convert float rate to edge-tts percent string (e.g. 1.2 → '+20%')."""
    if rate == 1.0:
        return "+0%"
    percent = round((rate - 1.0) * 100)
    prefix = "+" if percent > 0 else ""
    return f"{prefix}{percent}%"


def ensure_dir(file_path: str) -> None:
    """Ensure parent directory exists."""
    d = os.path.dirname(file_path)
    if d:
        os.makedirs(d, exist_ok=True)


# ── edge-tts communication ──────────────────────────────────────────


def create_communicate(
    text: str, voice_name: str, rate_str: str
) -> edge_tts.Communicate:
    """Construct Communicate, compatible with edge_tts 6.x and 7.x."""
    kwargs = {"rate": rate_str}
    sig = inspect.signature(edge_tts.Communicate)
    if "boundary" in sig.parameters:
        kwargs["boundary"] = "WordBoundary"
    return edge_tts.Communicate(text, voice_name, **kwargs)


def stream_chunks(communicate, on_chunk, timeout: float | None = 30.0) -> None:
    """Consume edge_tts stream (sync or async)."""
    if hasattr(communicate, "stream_sync"):
        _stream_sync(communicate, on_chunk, timeout)
        return
    if not hasattr(communicate, "stream"):
        raise AttributeError("edge_tts Communicate has no stream method")
    _stream_async(communicate, on_chunk, timeout)


def _stream_sync(communicate, on_chunk, timeout):
    if timeout:
        import signal

        def _timeout_handler(*_):
            raise TimeoutError(f"edge-tts stream timed out after {timeout}s")

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(int(timeout))
        try:
            for chunk in communicate.stream_sync():
                on_chunk(chunk)
        finally:
            signal.alarm(0)
    else:
        for chunk in communicate.stream_sync():
            on_chunk(chunk)


def _stream_async(communicate, on_chunk, timeout):
    async def _consume():
        async for chunk in communicate.stream():
            on_chunk(chunk)

    loop = asyncio.new_event_loop()
    try:
        if timeout:
            loop.run_until_complete(
                asyncio.wait_for(_consume(), timeout=timeout)
            )
        else:
            loop.run_until_complete(_consume())
    finally:
        loop.close()


# ── main TTS function ───────────────────────────────────────────────


def generate_audio(
    text: str,
    voice_file: str,
    voice_name: str = "zh-CN-XiaoxiaoNeural-Female",
    voice_rate: float = 1.0,
    max_retries: int = 3,
) -> SubMaker | None:
    """Generate audio from text using edge-tts.

    Args:
        text: The script text to speak.
        voice_file: Output path for audio (e.g. /path/to/audio.mp3).
        voice_name: edge-tts voice name (default: zh-CN-XiaoxiaoNeural-Female).
        voice_rate: Speech rate multiplier (1.0 = normal).
        max_retries: Number of retries on failure.

    Returns:
        SubMaker with subtitle data, or None on failure.
    """
    voice_name = parse_voice_name(voice_name)
    text = text.strip()
    rate_str = convert_rate_to_percent(voice_rate)

    for attempt in range(1, max_retries + 1):
        try:
            ensure_dir(voice_file)
            communicate = create_communicate(text, voice_name, rate_str)
            sub_maker = edge_tts.SubMaker()

            with open(voice_file, "wb") as f:

                def _handle(chunk):
                    ct = chunk["type"]
                    if ct == "audio":
                        f.write(chunk["data"])
                    elif ct in ("WordBoundary", "SentenceBoundary"):
                        sub_maker.feed(chunk)

                stream_chunks(communicate, _handle, timeout=30.0)

            if not sub_maker.get_srt():
                print(f"[tts] attempt {attempt}: sub_maker.get_srt() is empty, retrying...")
                continue

            return sub_maker

        except Exception as e:
            print(f"[tts] attempt {attempt} failed: {e}")
            # Remove empty file on failure
            if os.path.isfile(voice_file) and os.path.getsize(voice_file) == 0:
                try:
                    os.remove(voice_file)
                except OSError:
                    pass

    return None


def get_audio_duration(sub_maker: SubMaker) -> float:
    """Get audio duration in seconds from SubMaker."""
    import re

    srt = sub_maker.get_srt()
    if not srt:
        return 0.0
    # Parse last subtitle's end time
    times = re.findall(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", srt)
    if not times:
        return 0.0
    last = times[-1]
    seconds = int(last[0]) * 3600 + int(last[1]) * 60 + int(last[2]) + int(last[3]) / 1000
    return math.ceil(seconds)


def parse_srt_entries(srt_content: str) -> list[dict]:
    """Parse SRT content into list of entries.

    Each entry: {index, start_ms, end_ms, text}
    """
    import re

    _time_re = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")
    entries = []

    blocks = srt_content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        # Line 2 is the time range
        match = _time_re.findall(lines[1])
        if len(match) < 2:
            continue

        def _to_ms(t):
            return (int(t[0]) * 3600 + int(t[1]) * 60 + int(t[2])) * 1000 + int(t[3])

        start_ms = _to_ms(match[0])
        end_ms = _to_ms(match[1])
        text = "".join(lines[2:]).strip()
        entries.append({"start_ms": start_ms, "end_ms": end_ms, "text": text})

    return entries


def _ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT time format: hh:mm:ss,mmm"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    mm = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{mm:03d}"


def merge_srt_to_sentences(
    srt_content: str,
    max_gap_ms: int = 500,
    sentence_end_chars: str = "。！？.!?\n",
) -> str:
    """Merge word-level SRT entries into sentence-level chunks.

    edge-tts with WordBoundary generates one entry per word.
    This groups consecutive words into full sentences based on:

    1. Sentence-ending punctuation （。！？.!?）— start a new group
    2. Time gap > ``max_gap_ms`` between consecutive entries
    3. Newline characters in the text — start a new group
    4. Long entries (>40 chars) are kept as-is

    Args:
        srt_content: Raw SRT text from SubMaker.get_srt().
        max_gap_ms: Max pause between words in same group (ms).
        sentence_end_chars: Characters that trigger a sentence break.

    Returns:
        Merged SRT content with full-sentence subtitles.
    """
    entries = parse_srt_entries(srt_content)
    if not entries:
        return srt_content

    groups = []
    current_group = []

    for entry in entries:
        text = entry["text"]
        if not current_group:
            current_group.append(entry)
        else:
            prev = current_group[-1]
            gap = entry["start_ms"] - prev["end_ms"]

            # Should we break here?
            should_break = False

            # 1. Previous entry ended with sentence-ending punct
            if prev["text"] and prev["text"][-1] in sentence_end_chars:
                should_break = True
            # 2. Gap too large (natural pause between sentences)
            elif gap > max_gap_ms:
                should_break = True
            # 3. This entry starts with a newline
            elif text.startswith("\n"):
                should_break = True
            # 4. Current group would be too long (>80 chars)
            elif sum(len(e["text"]) for e in current_group) + len(text) > 80:
                should_break = True

            if should_break:
                groups.append(current_group)
                current_group = [entry]
            else:
                current_group.append(entry)

    if current_group:
        groups.append(current_group)

    # Build merged SRT
    output_lines = []
    for idx, group in enumerate(groups, 1):
        start_ms = group[0]["start_ms"]
        end_ms = group[-1]["end_ms"]
        # Ensure minimum subtitle duration (1 second for readability)
        if end_ms - start_ms < 1000:
            end_ms = start_ms + 1000

        text = "".join(e["text"] for e in group).strip()
        # Normalize whitespace
        text = text.replace("\n", " ").strip()
        if not text:
            continue

        output_lines.append(str(idx))
        output_lines.append(
            f"{_ms_to_srt_time(start_ms)} --> {_ms_to_srt_time(end_ms)}"
        )
        output_lines.append(text)
        output_lines.append("")

    return "\n".join(output_lines)


def save_srt(sub_maker: SubMaker, srt_file: str, merge_sentences: bool = True) -> str:
    """Save SRT from SubMaker to file, optionally merging into sentences."""
    ensure_dir(srt_file)
    content = sub_maker.get_srt()
    if content:
        if merge_sentences:
            content = merge_srt_to_sentences(content)
        with open(srt_file, "w", encoding="utf-8") as f:
            f.write(content)
    return srt_file
