"""Opt-in spike measuring whether Ollama consumes audio incrementally."""

import asyncio
import base64
import json
import os
import time
import wave
from collections.abc import Callable
from pathlib import Path

import pytest

from app.config import settings
from app.runtime.ollama import OllamaRuntime


def _chunk(data: bytes) -> bytes:
    return f"{len(data):x}\r\n".encode() + data + b"\r\n"


def _streamed_text(response: bytes) -> str:
    parts: list[str] = []
    for line in response.splitlines():
        if not line.startswith(b"data: ") or line == b"data: [DONE]":
            continue
        event = json.loads(line.removeprefix(b"data: "))
        choices = event.get("choices", [])
        if not choices:
            continue
        delta = choices[0].get("delta", {})
        for field in ("reasoning", "content"):
            value = delta.get(field)
            if isinstance(value, str):
                parts.append(value)
    return "".join(parts)


async def _watch_response(
    reader: asyncio.StreamReader,
    clock: Callable[[], float],
) -> tuple[bytes, dict[str, float]]:
    response = bytearray()
    timings: dict[str, float] = {}

    while part := await reader.read(4096):
        now = clock()
        if "first_response_byte" not in timings:
            timings["first_response_byte"] = now
        response.extend(part)
        if b"data:" in response and "first_sse_event" not in timings:
            timings["first_sse_event"] = now

    timings["response_complete"] = clock()
    return bytes(response), timings


async def _measure_request(
    audio_data: bytes,
    *,
    upload_duration_seconds: float,
    prompt_label: str,
) -> dict[str, object]:
    encoded_audio = base64.b64encode(audio_data)
    encoded_chunk_size = max(1, len(encoded_audio) // 5)
    audio_chunks = [
        encoded_audio[index : index + encoded_chunk_size]
        for index in range(0, len(encoded_audio), encoded_chunk_size)
    ]
    prefix = json.dumps(
        {
            "model": settings.ollama_model,
            "stream": True,
            "temperature": 0,
            "max_tokens": 64,
            "reasoning_effort": "none",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Transcribe the German audio exactly. "
                                f"Output only the transcription. Test {prompt_label}."
                            ),
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {"data": "AUDIO_DATA", "format": "wav"},
                        },
                    ],
                },
            ],
        },
        separators=(",", ":"),
    ).encode()
    prefix, suffix = prefix.split(b"AUDIO_DATA")

    host, port_text = settings.ollama_host.rsplit(":", 1)
    clock = time.perf_counter
    started = clock()
    reader, writer = await asyncio.open_connection(host, int(port_text))
    writer.write(
        (
            "POST /v1/chat/completions HTTP/1.1\r\n"
            f"Host: {settings.ollama_host}\r\n"
            "Content-Type: application/json\r\n"
            "Transfer-Encoding: chunked\r\n"
            "Connection: close\r\n\r\n"
        ).encode()
    )
    await writer.drain()

    response_task = asyncio.create_task(_watch_response(reader, clock))
    writer.write(_chunk(prefix))
    await writer.drain()

    delay_per_chunk = upload_duration_seconds / len(audio_chunks)
    for audio_chunk in audio_chunks:
        writer.write(_chunk(audio_chunk))
        await writer.drain()
        if delay_per_chunk:
            await asyncio.sleep(delay_per_chunk)

    writer.write(_chunk(suffix))
    writer.write(b"0\r\n\r\n")
    await writer.drain()
    upload_finished = clock()

    try:
        async with asyncio.timeout(180):
            response, response_timings = await response_task
    finally:
        writer.close()
        await writer.wait_closed()

    status_line = response.split(b"\r\n", 1)[0]
    assert b"200 OK" in status_line, response.decode(errors="replace")
    assert b"data:" in response
    streamed_text = _streamed_text(response)
    assert streamed_text.strip()

    first_response = response_timings["first_response_byte"]
    first_sse_event = response_timings.get("first_sse_event")
    return {
        "upload_seconds": round(upload_finished - started, 3),
        "response_started_before_upload_finished": first_response < upload_finished,
        "seconds_from_upload_end_to_response": round(first_response - upload_finished, 3),
        "seconds_from_upload_end_to_first_sse_event": (
            round(first_sse_event - upload_finished, 3)
            if first_sse_event is not None
            else None
        ),
        "total_seconds": round(response_timings["response_complete"] - started, 3),
        "response_text": streamed_text,
    }


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Ollama buffers native audio input instead of consuming it incrementally",
    strict=True,
)
@pytest.mark.skipif(
    os.environ.get("AVALON_RUN_AUDIO_STREAMING_SPIKE") != "1",
    reason="requires explicit local Ollama streaming-spike opt-in",
)
async def test_ollama_audio_input_streaming_feasibility() -> None:
    """Compare immediate and realtime-paced uploads on a warm model."""
    audio_path = Path("tests/data/german-transcription.wav")
    audio_data = audio_path.read_bytes()
    with wave.open(str(audio_path), "rb") as recording:
        audio_duration = recording.getnframes() / recording.getframerate()

    # Keep model loading out of the two audio measurements.
    await OllamaRuntime().generate_text("Antworte ausschließlich mit: bereit")
    immediate = await _measure_request(
        audio_data,
        upload_duration_seconds=0,
        prompt_label="A",
    )
    realtime = await _measure_request(
        audio_data,
        upload_duration_seconds=audio_duration,
        prompt_label="B",
    )

    immediate_latency = immediate["seconds_from_upload_end_to_response"]
    realtime_latency = realtime["seconds_from_upload_end_to_response"]
    assert isinstance(immediate_latency, float)
    assert isinstance(realtime_latency, float)
    result = {
        "audio_duration_seconds": round(audio_duration, 3),
        "immediate_upload": immediate,
        "realtime_paced_upload": realtime,
        "post_upload_latency_ratio": round(realtime_latency / immediate_latency, 3),
    }
    print(json.dumps(result, indent=2))

    assert "diagnostizierte" in str(immediate["response_text"]).lower()
    assert "diagnostizierte" in str(realtime["response_text"]).lower()
    assert realtime["response_started_before_upload_finished"] is True
    # With incremental audio consumption, most post-upload inference latency
    # should already have elapsed while the realtime-paced upload was running.
    assert realtime_latency < immediate_latency * 0.5
