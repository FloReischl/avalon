####################################################################################
# Run test in only in vscode session, started from ./spikes/whisper_cpu !
####################################################################################

from pathlib import Path

import pytest
from transcribe import (
    create_audio_chunks,
    get_audio_duration,
    merge_transcripts,
    transcribe,
)

DEFAULT_AUDIO = Path(__file__).resolve().parents[2] / "tests/data/german-transcription.wav"
MODELS = ("base", "small", "medium")

LONG_AUDIO = Path(__file__).resolve().parents[2] / "tests/data/long-text.wav"
LONG_AUDIO_MODELS = ("small", "medium")



def run_benchmark(audio_path, models):
    audio_duration = get_audio_duration(audio_path)

    # Run one complete transcription before measuring anything so one-time
    # initialization costs do not influence the benchmark results.
    transcribe(audio_path, models[0])

    results = []

    for model_name in models:
        result = transcribe(audio_path, model_name)
        result["realtime_factor"] = (
            result["transcription_duration"] / audio_duration
        )
        results.append(result)

        print()
        print(f"Model:           {model_name}")
        print(f"Language:        {result['language']}")
        print(f"Transcript:      {result['transcript']}")
        print(f"Model load:      {result['load_duration']:.2f} s")
        print(f"Transcription:   {result['transcription_duration']:.2f} s")
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

    return results


def test_short_audio():
    results = run_benchmark(DEFAULT_AUDIO, MODELS)

    assert len(results) == 3
    assert all(result["language"] == "de" for result in results)
    assert all(result["transcript"] for result in results)


def test_long_audio():
    results = run_benchmark(LONG_AUDIO, LONG_AUDIO_MODELS)

    assert len(results) == 2
    assert results[0]["language"] == "de"
    assert results[0]["transcript"]


def test_long_audio_chunked(tmp_path):
    chunks = create_audio_chunks(
        LONG_AUDIO,
        tmp_path,
        chunk_seconds=10.0,
        overlap_seconds=2.0,
    )

    assert chunks

    # Warm-up outside the measured chunk results.
    transcribe(chunks[0]["path"], "small")

    total_transcription_duration = 0.0
    merged_transcript = ""

    print()
    print("Chunked transcription: small")

    print("Window: 10.0 s, overlap: 2.0 s")
    print()

    for chunk in chunks:
        result = transcribe(chunk["path"], "small")
        total_transcription_duration += result["transcription_duration"]
        merged_transcript = merge_transcripts(
            merged_transcript,
            result["transcript"],
        )

        print(
            f"[{chunk['start']:05.1f}-{chunk['end']:05.1f}] "
            f"{result['transcript']}"
        )

    audio_duration = get_audio_duration(LONG_AUDIO)

    print()
    print(f"Merged transcript: {merged_transcript}")

    realtime_factor = total_transcription_duration / audio_duration

    print()
    print(f"Chunks:              {len(chunks)}")
    print(f"Audio duration:      {audio_duration:.2f} s")
    print(f"Transcription total: {total_transcription_duration:.2f} s")
    print(f"Realtime factor:     {realtime_factor:.3f}x")

    assert merged_transcript

if __name__ == "__main__":
    # Führt alle Tests in genau dieser Datei aus (__file__)
    pytest.main([__file__, "-v", "-s", "--capture=no"])
