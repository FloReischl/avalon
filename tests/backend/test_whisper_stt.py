import asyncio
import threading
import wave
from pathlib import Path

import pytest

from app.stt.whisper import (
    FasterWhisperSttService,
    StreamingPcmChunker,
    create_audio_chunks,
    merge_transcripts,
)



def write_wav(path: Path, seconds: float) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(10)
        output.writeframes(b"\0\0" * int(seconds * 10))


def test_chunking_window_overlap_and_final_tail(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    write_wav(source, 27)
    chunks = create_audio_chunks(source, tmp_path)
    assert [(item.start_seconds, item.end_seconds) for item in chunks] == [
        (0.0, 10.0), (8.0, 18.0), (16.0, 26.0), (24.0, 27.0),
    ]


def test_merge_is_exact_and_preserves_boundary_whitespace() -> None:
    assert merge_transcripts("Hallo Welt,", "welt, das ist Avalon") == "Hallo Welt, das ist Avalon"
    assert merge_transcripts("eins zwei", "drei vier") == "eins zwei drei vier"


@pytest.mark.asyncio
async def test_lazy_load_has_fixed_production_parameters() -> None:
    created, calls = [], []
    class Segment: text = " Hallo"
    class Model:
        def transcribe(self, path, **kwargs):
            calls.append((path, kwargs))
            return iter([Segment()]), object()
    def factory(*args, **kwargs):
        created.append((args, kwargs))
        return Model()
    service = FasterWhisperSttService(model_factory=factory)
    assert await service.transcribe(Path("input.wav")) == "Hallo"
    assert created == [(('small',), {'device': 'cpu', 'compute_type': 'int8'})]
    assert calls == [("input.wav", {'language': 'de', 'beam_size': 5})]
    await service.unload()


@pytest.mark.asyncio
async def test_inference_is_single_flight() -> None:
    entered = maximum = 0
    release = threading.Event()
    class Segment: text = " text"
    class Model:
        def transcribe(self, path, **kwargs):
            nonlocal entered, maximum
            entered += 1
            maximum = max(maximum, entered)
            release.wait()
            entered -= 1
            return iter([Segment()]), object()
    service = FasterWhisperSttService(model_factory=lambda *args, **kwargs: Model())
    first = asyncio.create_task(service.transcribe(Path("one.wav")))
    await asyncio.sleep(.01)
    second = asyncio.create_task(service.transcribe(Path("two.wav")))
    await asyncio.sleep(.01)
    release.set()
    assert await asyncio.gather(first, second) == ["text", "text"]
    assert maximum == 1
    await service.unload()


@pytest.mark.asyncio
async def test_cancelled_inference_returns_immediately_but_keeps_single_flight() -> None:
    entered = threading.Event()
    release = threading.Event()

    class Segment:
        text = " text"

    class Model:
        def transcribe(self, path, **kwargs):
            del path, kwargs
            entered.set()
            release.wait()
            return iter([Segment()]), object()

    service = FasterWhisperSttService(
        model_factory=lambda *args, **kwargs: Model(),
    )

    first = asyncio.create_task(service.transcribe(Path("one.wav")))

    for _ in range(100):
        if entered.is_set():
            break
        await asyncio.sleep(0.001)
    assert entered.is_set()

    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(first, timeout=0.05)

    second = asyncio.create_task(service.transcribe(Path("two.wav")))
    await asyncio.sleep(0.01)

    # The cancelled caller is already gone, but its worker thread still owns
    # the single-flight lock until the real Whisper inference returns.
    assert second.done() is False

    release.set()
    assert await second == "text"
    await service.unload()


@pytest.mark.asyncio
async def test_idle_unload_is_reset_by_activity_and_call_residency() -> None:
    class Model:
        def transcribe(self, path, **kwargs): return iter(()), object()
    service = FasterWhisperSttService(model_factory=lambda *args, **kwargs: Model(), idle_unload_seconds=.03)
    await service.warm_up()
    await asyncio.sleep(.01)
    await service.transcribe(Path("input.wav"))
    await asyncio.sleep(.025)
    assert service._model is not None
    await asyncio.sleep(.02)
    assert service._model is None
    await service.warm_up()
    await service.set_audio_call_active(True)
    await asyncio.sleep(.05)
    assert service._model is not None
    await service.set_audio_call_active(False)
    await asyncio.sleep(.05)
    assert service._model is None


@pytest.mark.asyncio
async def test_model_load_failure_propagates_without_retaining_a_model() -> None:
    def factory(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("model unavailable")

    service = FasterWhisperSttService(model_factory=factory)

    with pytest.raises(RuntimeError, match="model unavailable"):
        await service.warm_up()

    assert service._model is None


@pytest.mark.asyncio
async def test_real_small_model_transcribes_german_fixture() -> None:
    service = FasterWhisperSttService()
    try:
        transcript = await service.transcribe(
            Path("tests/data/german-transcription.wav"),
        )
    finally:
        await service.unload()

    normalized = transcript.lower()
    assert transcript.strip()
    assert "diagnostiz" in normalized


def test_streaming_chunker_emits_full_windows_before_finish(
    tmp_path: Path,
) -> None:
    chunker = StreamingPcmChunker(
        sample_rate_hz=10,
        output_directory=tmp_path,
    )

    assert chunker.add_pcm(b"\0\0" * 99) == []
    first = chunker.add_pcm(b"\0\0")
    second = chunker.add_pcm(b"\0\0" * 80)
    third = chunker.add_pcm(b"\0\0" * 80)
    tail = chunker.add_pcm(b"\0\0" * 10) + chunker.finish()

    assert [(item.start_seconds, item.end_seconds) for item in [
        *first,
        *second,
        *third,
        *tail,
    ]] == [
        (0.0, 10.0),
        (8.0, 18.0),
        (16.0, 26.0),
        (24.0, 27.0),
    ]
    assert chunker.finish() == []


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (10, [(0.0, 10.0)]),
        (18, [(0.0, 10.0), (8.0, 18.0)]),
        (
            27,
            [
                (0.0, 10.0),
                (8.0, 18.0),
                (16.0, 26.0),
                (24.0, 27.0),
            ],
        ),
    ],
)
def test_streaming_chunker_only_emits_uncovered_final_tail(
    tmp_path: Path,
    seconds: int,
    expected: list[tuple[float, float]],
) -> None:
    chunker = StreamingPcmChunker(
        sample_rate_hz=10,
        output_directory=tmp_path,
    )

    chunks = chunker.add_pcm(b"\0\0" * (seconds * 10))
    chunks.extend(chunker.finish())

    assert [
        (item.start_seconds, item.end_seconds)
        for item in chunks
    ] == expected
