#!/usr/bin/env python3

import argparse
import time
import wave
from pathlib import Path

from faster_whisper import WhisperModel

DEFAULT_AUDIO = Path(__file__).resolve().parents[2] / "tests/data/german-transcription.wav"
MODELS = ("base", "small", "medium")

COMPUTE_TYPE = "int8"


def get_audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def create_audio_chunks(
    path: Path,
    output_dir: Path,
    chunk_seconds: float = 10.0,
    overlap_seconds: float = 2.0,
) -> list[dict]:
    if overlap_seconds >= chunk_seconds:
        raise ValueError("overlap_seconds must be smaller than chunk_seconds")

    chunks = []

    with wave.open(str(path), "rb") as source:
        frame_rate = source.getframerate()
        total_frames = source.getnframes()

        chunk_frames = int(chunk_seconds * frame_rate)
        step_frames = int((chunk_seconds - overlap_seconds) * frame_rate)

        start_frame = 0
        index = 0

        while start_frame < total_frames:
            end_frame = min(start_frame + chunk_frames, total_frames)

            source.setpos(start_frame)
            frames = source.readframes(end_frame - start_frame)

            chunk_path = output_dir / f"chunk-{index:03d}.wav"

            with wave.open(str(chunk_path), "wb") as target:
                target.setparams(source.getparams())
                target.writeframes(frames)

            chunks.append(
                {
                    "path": chunk_path,
                    "start": start_frame / frame_rate,
                    "end": end_frame / frame_rate,
                }
            )

            if end_frame == total_frames:
                break

            start_frame += step_frames
            index += 1

    return chunks



def merge_transcripts(previous: str, current: str) -> str:
    if not previous:
        return current.strip()

    previous_words = previous.split()
    current_words = current.split()

    def normalize(word: str) -> str:
        return word.lower().strip(".,!?;:\"'()")

    previous_normalized = [normalize(word) for word in previous_words]
    current_normalized = [normalize(word) for word in current_words]

    max_overlap = min(len(previous_words), len(current_words))
    overlap = 0

    for size in range(1, max_overlap + 1):
        if previous_normalized[-size:] == current_normalized[:size]:
            overlap = size

    new_words = current_words[overlap:]

    if not new_words:
        return previous.strip()

    return f"{previous.rstrip()} {' '.join(new_words)}"


def transcribe(audio_path: Path, model_name: str) -> dict:

    load_started = time.perf_counter()
    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type=COMPUTE_TYPE,
    )
    load_duration = time.perf_counter() - load_started

    transcription_started = time.perf_counter()

    segments, info = model.transcribe(
        str(audio_path),
        language="de",
        beam_size=5,
    )

    # faster-whisper performs transcription lazily while iterating segments.
    segments = list(segments)

    transcription_duration = time.perf_counter() - transcription_started
    transcript = "".join(segment.text for segment in segments).strip()

    return {
        "model": model_name,
        "load_duration": load_duration,
        "transcription_duration": transcription_duration,
        "language": info.language,
        "transcript": transcript,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CPU-only faster-whisper benchmark spike"
    )
    parser.add_argument(
        "audio",
        nargs="?",
        type=Path,
        default=DEFAULT_AUDIO,
        help="WAV file to transcribe",
    )
    args = parser.parse_args()

    audio_path = args.audio.resolve()
    if not audio_path.is_file():
        raise SystemExit(f"Audio file not found: {audio_path}")

    audio_duration = get_audio_duration(audio_path)

    print("Device:         CPU")
    print(f"Compute type:   {COMPUTE_TYPE}")
    print(f"Audio:          {audio_path}")
    print(f"Audio duration: {audio_duration:.2f} s")
    print()

    print("Warm-up: base (results discarded)")
    transcribe(audio_path, "base")
    print("Warm-up complete.")
    print()

    results = []

    for model_name in MODELS:
        print(f"Benchmarking: {model_name}")

        result = transcribe(audio_path, model_name)
        result["realtime_factor"] = (
            result["transcription_duration"] / audio_duration
        )
        results.append(result)

        print(f"Language:      {result['language']}")
        print(f"Transcript:    {result['transcript']}")
        print(f"Model load:    {result['load_duration']:.2f} s")
        print(f"Transcription: {result['transcription_duration']:.2f} s")
        print(f"Realtime factor: {result['realtime_factor']:.3f}x")
        print()

    print("Summary")
    print(
        f"{'Model':<10}"
        f"{'Load':>10}"
        f"{'Transcription':>16}"
        f"{'RTF':>10}"
    )
    print("-" * 46)

    for result in results:
        print(
            f"{result['model']:<10}"
            f"{result['load_duration']:>9.2f}s"
            f"{result['transcription_duration']:>15.2f}s"
            f"{result['realtime_factor']:>9.3f}x"
        )


if __name__ == "__main__":
    main()