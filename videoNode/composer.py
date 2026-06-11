"""Video composer — combine clips, overlay subtitles, mix audio + BGM.

Inspired by MoneyPrinterTurbo's video.py and generate_video().
Uses MoviePy for composition and ffmpeg for efficient clip concatenation.
"""

import glob
import itertools
import os
import random
import shutil
import subprocess
from typing import List, Optional, Tuple

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    afx,
)
from moviepy.video.tools.subtitles import SubtitlesClip


# ── Constants ──────────────────────────────────────────────────────

PORTRAIT_1080P = (1080, 1920)
PORTRAIT_720P = (720, 1280)

audio_codec = "aac"
audio_bitrate = "192k"
video_codec = "libx264"
fps = 30


# ── Helpers ─────────────────────────────────────────────────────────


def _open_video(video_path: str) -> VideoFileClip:
    """Open video quietly (suppress MoviePy print noise)."""
    import io
    from contextlib import redirect_stdout

    captured = io.StringIO()
    with redirect_stdout(captured):
        clip = VideoFileClip(video_path, audio=False)
    return clip


def _close_clip(clip):
    """Safely close a clip and all its resources."""
    if clip is None:
        return
    try:
        if hasattr(clip, "reader") and clip.reader is not None:
            clip.reader.close()
        if hasattr(clip, "audio") and clip.audio is not None:
            if hasattr(clip.audio, "reader") and clip.audio.reader is not None:
                clip.audio.reader.close()
            del clip.audio
        if hasattr(clip, "mask") and clip.mask is not None:
            if hasattr(clip.mask, "reader") and clip.mask.reader is not None:
                clip.mask.reader.close()
            del clip.mask
    except Exception:
        pass


def _resolve_ffmpeg() -> str:
    """Find ffmpeg binary."""
    configured = os.environ.get("IMAGEIO_FFMPEG_EXE")
    if configured:
        return configured
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _parse_srt(srt_path: str) -> List[Tuple[Tuple[float, float], str]]:
    """Parse an SRT subtitle file.

    Returns list of [((start_sec, end_sec), text), ...].
    """
    import re

    _time_re = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")
    result = []

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        # Line 2 should be the time range
        time_line = lines[1]
        match = _time_re.findall(time_line)
        if len(match) < 2:
            continue

        def _to_sec(t):
            return int(t[0]) * 3600 + int(t[1]) * 60 + int(t[2]) + int(t[3]) / 1000

        t_start = _to_sec(match[0])
        t_end = _to_sec(match[1])
        text = "\n".join(lines[2:]).strip()
        result.append(((t_start, t_end), text))

    return result


# ── Step 1: Combine video clips ────────────────────────────────────


def combine_clips(
    video_paths: List[str],
    audio_file: str,
    output_path: str,
    target_size: Tuple[int, int] = PORTRAIT_1080P,
    max_clip_duration: int = 5,
    random_order: bool = True,
    transition: str = "none",
    threads: int = 2,
    progress_callback=None,
) -> str:
    """Combine multiple video clips into one, matching audio duration.

    Steps:
    1. Read audio to get target duration
    2. Split each source video into max_clip_duration segments
    3. Shuffle segments (optional)
    4. Process segments: resize to target, apply transitions
    5. Loop until total >= audio duration
    6. Concatenate with ffmpeg

    Args:
        video_paths: List of source video file paths.
        audio_file: TTS audio file (used for timing).
        output_path: Where to save the combined video.
        target_size: (width, height) for output.
        max_clip_duration: Max seconds per clip segment.
        random_order: Shuffle segments randomly.
        transition: Transition type: none, fade, shuffle.
        threads: Threads for encoding.

    Returns:
        Path to the combined video file.
    """
    # 1. Get audio duration
    audio_clip = AudioFileClip(audio_file)
    try:
        audio_duration = audio_clip.duration
    finally:
        _close_clip(audio_clip)

    print(f"[video] audio duration: {audio_duration:.1f}s")
    print(f"[video] target resolution: {target_size[0]}x{target_size[1]}")

    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    _report = progress_callback or (lambda msg, pct: None)

    # 2. Scan clips and split into segments
    segments = []
    for vp in video_paths:
        clip = _open_video(vp)
        duration = clip.duration
        clip_w, clip_h = clip.size
        _close_clip(clip)

        start = 0
        while start < duration:
            end = min(start + max_clip_duration, duration)
            if end > start:
                segments.append({
                    "file": vp,
                    "start": start,
                    "end": end,
                    "width": clip_w,
                    "height": clip_h,
                    "duration": end - start,
                })
            start = end
            if not random_order:  # sequential: only one segment per source
                break

    # 3. Shuffle if random
    if random_order:
        random.shuffle(segments)

    _report(f"generated {len(segments)} clip segments", 10)

    # 4. Process segments: resize + transition → write temp clips
    target_w, target_h = target_size
    processed_files = []
    total_duration = 0.0
    segment_pool = list(segments)

    # We'll iterate through segments, looping if needed
    iterator = itertools.cycle(segment_pool) if len(segment_pool) > 0 else []
    idx = 0

    for seg in iterator:
        if total_duration >= audio_duration:
            break

        idx += 1
        _report(f"processing clip {idx}", 10 + min(35, int(30 * total_duration / max(audio_duration, 1))))

        try:
            clip = _open_video(seg["file"]).subclipped(seg["start"], seg["end"])
            seg_duration = clip.duration

            # Resize to target aspect ratio
            cw, ch = clip.size
            if cw != target_w or ch != target_h:
                clip_ratio = cw / ch
                target_ratio = target_w / target_h

                if abs(clip_ratio - target_ratio) < 0.05:
                    clip = clip.resized(new_size=(target_w, target_h))
                elif clip_ratio > target_ratio:
                    # Wider than target → scale by height, add black bars on sides
                    scale = target_h / ch
                    new_w = int(cw * scale)
                    bg = ColorClip(size=(target_w, target_h), color=(0, 0, 0)).with_duration(clip.duration)
                    clip_resized = clip.resized(new_size=(new_w, target_h)).with_position("center")
                    clip = CompositeVideoClip([bg, clip_resized])
                else:
                    # Taller than target → scale by width, add black bars on top/bottom
                    scale = target_w / cw
                    new_h = int(ch * scale)
                    bg = ColorClip(size=(target_w, target_h), color=(0, 0, 0)).with_duration(clip.duration)
                    clip_resized = clip.resized(new_size=(target_w, new_h)).with_position("center")
                    clip = CompositeVideoClip([bg, clip_resized])

            # Trim to max_clip_duration
            if clip.duration > max_clip_duration:
                clip = clip.subclipped(0, max_clip_duration)

            # Write temp clip
            temp_file = os.path.join(output_dir, f"_tc_{idx:04d}.mp4")
            clip.write_videofile(
                temp_file,
                fps=fps,
                codec=video_codec,
                audio=False,
                logger=None,
                threads=threads,
            )
            stored_duration = clip.duration
            _close_clip(clip)

            processed_files.append(temp_file)
            total_duration += stored_duration

        except Exception as e:
            print(f"[video] clip {idx} failed: {e}")
            continue

    print(f"[video] total processed clips: {len(processed_files)}, "
          f"duration: {total_duration:.1f}s (target: {audio_duration:.1f}s)")

    _report(f"concatenating {len(processed_files)} clips", 50)

    # 5. Concatenate with ffmpeg
    if not processed_files:
        raise RuntimeError("No valid clips to combine")

    if len(processed_files) == 1:
        shutil.copy(processed_files[0], output_path)
    else:
        _concat_with_ffmpeg(processed_files, output_path, threads)

    # 6. Cleanup temp files
    for f in processed_files:
        try:
            os.remove(f)
        except OSError:
            pass

    print(f"[video] combined video: {output_path}")
    return output_path


def _concat_with_ffmpeg(clip_files: List[str], output: str, threads: int):
    """Concat clips with ffmpeg concat demuxer (re-encode to avoid corrupt frames)."""
    out_dir = os.path.dirname(output)
    list_file = os.path.join(out_dir, "_concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for cf in clip_files:
            abs_path = os.path.abspath(cf).replace("'", "'\\\\''")
            f.write(f"file '{abs_path}'\n")

    cmd = [
        _resolve_ffmpeg(), "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-threads", str(threads),
        output,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        os.remove(list_file)
    except OSError:
        pass

    if result.returncode != 0:
        error = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"ffmpeg concat failed: {error}")


# ── Step 2: Compose final video ─────────────────────────────────────


def _make_text_clip(
    text: str,
    font_path: str,
    font_size: int,
    color: str,
    bg_color: str,
    stroke_color: str,
    stroke_width: int,
    video_width: int,
    video_height: int,
    start_time: float,
    end_time: float,
    position: str = "bottom",
) -> TextClip:
    """Create a styled TextClip for subtitles."""
    from PIL import ImageFont

    # Measure per-line height
    font = ImageFont.truetype(font_path, font_size)
    _, _, _, line_h = font.getbbox("中")  # A Chinese char gives line height

    # Wrap text if needed
    max_width = int(video_width * 0.88)
    wrapped = text
    w, _ = font.getbbox(text)[2], font.getbbox(text)[3]
    if w > max_width:
        lines = []
        txt = ""
        for char in text:
            txt += char
            tw = font.getbbox(txt)[2]
            if tw > max_width:
                lines.append(txt[:-1])
                txt = char
        lines.append(txt)
        wrapped = "\n".join(line.strip() for line in lines)

    interline = int(font_size * 0.25)
    vertical_padding = int(font_size * 0.35)
    line_count = wrapped.count("\n") + 1
    # Total height: padding_top + all lines + interline gaps + padding_bottom
    clip_height = (
        vertical_padding
        + line_h * line_count
        + interline * (line_count - 1)
        + vertical_padding
    )
    # Safety cap: subtitle shouldn't exceed 40% of screen
    if clip_height > video_height * 0.4:
        clip_height = int(video_height * 0.4)

    clip = TextClip(
        text=wrapped,
        font=font_path,
        font_size=font_size,
        color=color,
        bg_color=bg_color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        interline=interline,
        size=(int(max_width), clip_height),
        text_align="center",
    )

    duration = end_time - start_time
    clip = clip.with_start(start_time).with_end(end_time).with_duration(duration)

    # Position with safe margins: keep subtitle fully inside the screen
    bottom_margin = int(video_height * 0.07)   # 7% from bottom edge
    top_margin = int(video_height * 0.05)       # 5% from top edge
    y_pos = video_height - bottom_margin - clip_height
    y_pos = max(y_pos, top_margin)  # Don't go above top margin
    # Also don't push bottom below screen
    y_pos = min(y_pos, video_height - bottom_margin - clip_height // 2)

    if position == "bottom":
        clip = clip.with_position(("center", y_pos))
    elif position == "top":
        clip = clip.with_position(("center", top_margin))
    else:  # center
        clip = clip.with_position(("center", "center"))

    return clip


def compose_final(
    combined_video: str,
    audio_file: str,
    subtitle_file: str | None,
    output_path: str,
    bgm_file: str | None = None,
    target_size: Tuple[int, int] = PORTRAIT_1080P,
    font_path: str = "",
    voice_volume: float = 1.0,
    bgm_volume: float = 0.2,
    subtitle_position: str = "bottom",
    text_color: str = "#EAEAEA",
    text_bg_color: str = None,
    stroke_color: str = "#000000",
    stroke_width: int = 1,
    font_size: int = 60,
    threads: int = 2,
    progress_callback=None,
) -> str:
    """Compose final video: combine + subtitles + TTS audio + BGM.

    Args:
        combined_video: Path from combine_clips().
        audio_file: TTS audio (MP3).
        subtitle_file: Optional SRT subtitle file.
        output_path: Final output path.
        bgm_file: Optional BGM file.
        target_size: (width, height) for output.
        font_path: TTF font path for subtitles.
        voice_volume: TTS audio volume multiplier.
        bgm_volume: BGM volume multiplier (default 0.2 = 20%).
        subtitle_position: bottom / top / center.
        text_color: Subtitle text color.
        text_bg_color: Subtitle background color (None = transparent).
        stroke_color: Subtitle stroke/outline color.
        stroke_width: Subtitle stroke width.
        font_size: Subtitle font size.
        threads: Encoding threads.

    Returns:
        Path to final video file.
    """
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    _report = progress_callback or (lambda msg, pct: None)

    target_w, target_h = target_size
    _report("opening video and audio", 60)

    # Load video
    video_clip = _open_video(combined_video)
    # Trim video to match audio in case it's longer
    audio_clip = AudioFileClip(audio_file)

    if video_clip.duration > audio_clip.duration:
        video_clip = video_clip.subclipped(0, audio_clip.duration)

    _report("applying subtitles", 70)

    # Apply subtitles
    if subtitle_file and os.path.isfile(subtitle_file):
        subtitles = _parse_srt(subtitle_file)
        if subtitles:
            text_clips = []
            for (t_start, t_end), txt in subtitles:
                clip = _make_text_clip(
                    text=txt,
                    font_path=font_path,
                    font_size=font_size,
                    color=text_color,
                    bg_color=text_bg_color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    video_width=target_w,
                    video_height=target_h,
                    start_time=t_start,
                    end_time=t_end,
                    position=subtitle_position,
                )
                text_clips.append(clip)

            if text_clips:
                video_clip = CompositeVideoClip([video_clip, *text_clips])

    _report("mixing audio and BGM", 80)

    # Adjust TTS volume
    tts_audio = audio_clip.with_effects([afx.MultiplyVolume(voice_volume)])

    # Add BGM
    if bgm_file and os.path.isfile(bgm_file):
        try:
            bgm_clip = AudioFileClip(bgm_file).with_effects([
                afx.MultiplyVolume(bgm_volume),
                afx.AudioFadeOut(3),
                afx.AudioLoop(duration=video_clip.duration),
            ])
            final_audio = CompositeAudioClip([tts_audio, bgm_clip])
        except Exception as e:
            print(f"[video] BGM failed: {e}, using TTS only")
            final_audio = tts_audio
    else:
        final_audio = tts_audio

    video_clip = video_clip.with_audio(final_audio)

    _report("writing final video", 85)

    # Write final video
    output_audio_fps = int(getattr(final_audio, "fps", 0) or 44100)
    video_clip.write_videofile(
        output_path,
        audio_codec=audio_codec,
        audio_fps=output_audio_fps,
        audio_bitrate=audio_bitrate,
        temp_audiofile_path=output_dir,
        threads=threads,
        logger=None,
        fps=fps,
    )

    _close_clip(video_clip)

    print(f"[video] final video: {output_path}")
    return output_path


# ── Convenience: full pipeline ──────────────────────────────────────


def make_video(
    video_paths: List[str],
    audio_file: str,
    output_path: str,
    subtitle_file: str | None = None,
    bgm_file: str | None = None,
    target_size: Tuple[int, int] = PORTRAIT_1080P,
    font_path: str = "",
    max_clip_duration: int = 5,
    random_order: bool = True,
    transition: str = "none",
    voice_volume: float = 1.0,
    bgm_volume: float = 0.2,
    subtitle_position: str = "bottom",
    text_color: str = "#EAEAEA",
    text_bg_color: str = None,
    stroke_color: str = "#000000",
    stroke_width: int = 2,
    font_size: int = 45,
    threads: int = 2,
) -> str:
    """Run the full pipeline: combine clips → compose final video.

    Returns path to the final video file.
    """
    output_dir = os.path.dirname(output_path)

    # Step 1: Combine clips
    combined_path = os.path.join(output_dir, "combined.mp4")
    combine_clips(
        video_paths=video_paths,
        audio_file=audio_file,
        output_path=combined_path,
        target_size=target_size,
        max_clip_duration=max_clip_duration,
        random_order=random_order,
        transition=transition,
        threads=threads,
    )

    # Step 2: Compose final
    compose_final(
        combined_video=combined_path,
        audio_file=audio_file,
        subtitle_file=subtitle_file,
        output_path=output_path,
        bgm_file=bgm_file,
        target_size=target_size,
        font_path=font_path,
        voice_volume=voice_volume,
        bgm_volume=bgm_volume,
        subtitle_position=subtitle_position,
        text_color=text_color,
        text_bg_color=text_bg_color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        font_size=font_size,
        threads=threads,
    )

    return output_path
