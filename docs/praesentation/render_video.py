#!/usr/bin/env python3
"""Combine slide PNGs with an original ambient bed into an MP4."""

from __future__ import annotations

import math
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

SLIDES = 8
SECONDS = 5
RATE = 44100
WIDTH = 1920
HEIGHT = 1080


def write_music(path: Path, seconds: int) -> None:
    n = RATE * seconds
    melody = [196.0, 246.94, 293.66, 329.63, 392.0, 329.63, 293.66, 246.94]
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        for i in range(n):
            t = i / RATE
            pad = 0.11 * math.sin(2 * math.pi * 98 * t) * math.exp(-0.015 * (t % 8))
            idx = int(t / 0.85) % len(melody)
            env = max(0.0, 1.0 - ((t % 0.85) / 0.85))
            tone = 0.16 * math.sin(2 * math.pi * melody[idx] * t) * env
            sample = max(-1.0, min(1.0, pad + tone))
            wav.writeframes(struct.pack("<h", int(sample * 22000)))


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: render_video.py FRAMES_DIR [OUT.mp4]", file=sys.stderr)
        return 2
    frames_dir = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent / "wachbuch-vorfuehrung.mp4"
    files = sorted(frames_dir.glob("slide-*.png"))
    if len(files) < SLIDES:
        print(f"Need {SLIDES} slides, found {len(files)}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        music = tmp_path / "bed.wav"
        write_music(music, SLIDES * SECONDS + 2)
        concat = tmp_path / "list.txt"
        concat.write_text(
            "".join(f"file '{p.resolve()}'\nduration {SECONDS}\n" for p in files[:SLIDES])
            + f"file '{files[SLIDES - 1].resolve()}'\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat),
                "-i",
                str(music),
                "-vf",
                f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                "-movflags",
                "+faststart",
                str(out),
            ],
            check=True,
        )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
