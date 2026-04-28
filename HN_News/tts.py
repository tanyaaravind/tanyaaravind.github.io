"""
tts.py
Converts a podcast script to MP3 audio.
Currently uses edge-tts (free). Swap to OpenAI TTS by changing TTS_BACKEND.

Import: from tts import script_to_audio
"""

import asyncio
import os
import re
import tempfile
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────────────────────
# CONFIGURATION — swap backend here when ready
# ─────────────────────────────────────────────

TTS_BACKEND = "openai"   # "edge" (free) or "openai" ($)

# Edge TTS voices — these sound decent and are free
EDGE_VOICES = {
    "JORDAN": "en-US-AndrewNeural",   # male, warm and conversational
    "ALEX":   "en-US-EmmaNeural",     # female, clear and authoritative
}

# OpenAI TTS voices — swap in when ready
OPENAI_VOICES = {
    "JORDAN": "echo",    # deep, engaging
    "ALEX":   "nova",    # clear, professional
}

OPENAI_TTS_MODEL = "tts-1"   # or "tts-1-hd" for higher quality (2x cost)


# ─────────────────────────────────────────────
# EDGE TTS (free)
# ─────────────────────────────────────────────

async def _edge_line_to_audio(text: str, voice: str, output_path: str):
    """Convert one line to audio using edge-tts"""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


async def _edge_script_to_chunks(
    script: list[tuple[str, str]],
    tmp_dir: str
) -> list[str]:
    """Convert all lines to audio chunks using edge-tts"""
    chunk_paths = []
    for i, (speaker, text) in enumerate(script):
        voice = EDGE_VOICES.get(speaker, EDGE_VOICES["JORDAN"])
        path = os.path.join(tmp_dir, f"chunk_{i:04d}.mp3")
        print(f"   [{i+1}/{len(script)}] {speaker}: {text[:60]}...")
        await _edge_line_to_audio(text, voice, path)
        chunk_paths.append(path)
    return chunk_paths


# ─────────────────────────────────────────────
# OPENAI TTS ($)
# ─────────────────────────────────────────────

def _openai_script_to_chunks(
    script: list[tuple[str, str]],
    tmp_dir: str
) -> list[str]:
    """Convert all lines to audio chunks using OpenAI TTS"""
    from openai import OpenAI
    openai_client = OpenAI()

    chunk_paths = []
    for i, (speaker, text) in enumerate(script):
        voice = OPENAI_VOICES.get(speaker, OPENAI_VOICES["JORDAN"])
        path = os.path.join(tmp_dir, f"chunk_{i:04d}.mp3")
        print(f"   [{i+1}/{len(script)}] {speaker}: {text[:60]}...")

        response = openai_client.audio.speech.create(
            model=OPENAI_TTS_MODEL,
            voice=voice,
            input=text,
        )
        response.stream_to_file(path)
        chunk_paths.append(path)

    return chunk_paths


# ─────────────────────────────────────────────
# AUDIO MERGING
# ─────────────────────────────────────────────

def _merge_chunks(chunk_paths: list[str], output_path: str, pause_ms: int = 400):
    """Merge audio chunks into one MP3 with a short pause between speakers"""
    from pydub import AudioSegment

    combined = AudioSegment.empty()
    pause = AudioSegment.silent(duration=pause_ms)
    prev_speaker_idx = None

    for i, path in enumerate(chunk_paths):
        segment = AudioSegment.from_file(path, format="mp3")
        if i > 0:
            combined += pause
        combined += segment

    combined.export(output_path, format="mp3")
    print(f"   Merged {len(chunk_paths)} chunks → {output_path}")


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def script_to_audio(
    script: list[tuple[str, str]],
    output_path: str = "podcast.mp3",
    backend: str = TTS_BACKEND,
) -> str:
    """
    Convert a podcast script to an MP3 file.

    Args:
        script: list of (speaker, text) tuples e.g. [("JORDAN", "Hey..."), ...]
        output_path: where to save the final MP3
        backend: "edge" or "openai"

    Returns:
        path to the output MP3
    """
    print(f"\n🎙️  Converting script to audio ({backend} TTS)...")
    print(f"   {len(script)} lines → {output_path}\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Generate chunks
        if backend == "edge":
            chunk_paths = asyncio.run(
                _edge_script_to_chunks(script, tmp_dir)
            )
        elif backend == "openai":
            chunk_paths = _openai_script_to_chunks(script, tmp_dir)
        else:
            raise ValueError(f"Unknown TTS backend: {backend}. Use 'edge' or 'openai'.")

        # Merge into one file
        print(f"\n   Merging audio...")
        _merge_chunks(chunk_paths, output_path)

    print(f"✅ Audio saved to: {output_path}")
    return output_path


# ─────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    TEST_SCRIPT = [
        ("JORDAN", "Welcome to HN Daily — today we're talking about why GitHub Copilot just got a lot more complicated for developers."),
        ("ALEX", "Right, and this one's interesting because it's not just a pricing story. It reveals something bigger about where the AI tools market is heading."),
        ("JORDAN", "Okay so first — what actually changed? Like, I'm a developer, I've been paying ten bucks a month. What's different now?"),
        ("ALEX", "So instead of that flat ten dollars, you now pay per suggestion you actually accept. Per line generated. The more you use it, the more you pay."),
        ("JORDAN", "Which sounds fair in theory. But what are we talking about in actual dollars for a heavy user?"),
        ("ALEX", "Someone coding eight hours a day could realistically see forty to eighty dollars a month. That's a four to eight times increase."),
        ("JORDAN", "Yeah that's not a small rounding error. So what's the HN community saying about this?"),
        ("ALEX", "It's split. The cynical take is that Microsoft established the market at a loss and is now extracting value. But there's a genuine counterargument that heavy users were always being subsidized by people who barely used it."),
        ("JORDAN", "Huh. So the light users were basically paying for the power users this whole time."),
        ("ALEX", "Exactly. And one commenter made the point that at the actual per-token rate, writing a whole CRUD app costs about the same as a coffee. The outrage might be a bit disproportionate."),
        ("JORDAN", "Okay that's a good reality check. So what's the actual takeaway here?"),
        ("ALEX", "Watch the open source alternatives. Codeium, Cursor, local models. If Copilot gets expensive, that ecosystem gets very interesting very fast."),
    ]

    output = script_to_audio(TEST_SCRIPT, output_path="test_output.mp3")
    print(f"\nOpen {output} to hear the result!")