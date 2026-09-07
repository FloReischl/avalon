"""Tests for the local TTS HTTP contract."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.api.routes.tts import get_tts_service
from app.main import create_app
from app.services.tts import TtsBusyError, TtsResult


class FakeTtsService:
    def __init__(self) -> None:
        self.received_text: str | None = None
        self.ended_playback_id: str | None = None
        self.error: Exception | None = None

    async def synthesize(self, text: str) -> TtsResult:
        self.received_text = text
        if self.error is not None:
            raise self.error

        return TtsResult(
            playback_id="playback-123",
            audio=b"RIFFfake-WAVE",
        )

    async def playback_ended(self, playback_id: str) -> None:
        self.ended_playback_id = playback_id


def request(
    method: str,
    path: str,
    service: FakeTtsService,
    **kwargs,
):
    async def send_request():
        application = create_app()
        application.dependency_overrides[get_tts_service] = lambda: service

        transport = ASGITransport(app=application)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send_request())


def test_tts_returns_wav_and_playback_id() -> None:
    service = FakeTtsService()

    response = request(
        "POST",
        "/api/v1/tts",
        service,
        json={"text": "Hallo Flo"},
        headers={"Origin": "http://127.0.0.1:5173"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["x-avalo-tts-playback-id"] == "playback-123"
    assert (
        "X-Avalo-TTS-Playback-ID"
        in response.headers["access-control-expose-headers"]
    )
    assert response.content == b"RIFFfake-WAVE"
    assert service.received_text == "Hallo Flo"


def test_playback_end_is_forwarded_to_service() -> None:
    service = FakeTtsService()

    response = request(
        "POST",
        "/api/v1/tts/playback-ended",
        service,
        json={"playback_id": "playback-123"},
    )

    assert response.status_code == 204
    assert service.ended_playback_id == "playback-123"


def test_tts_reports_synthesis_failure_without_internal_details() -> None:
    service = FakeTtsService()
    service.error = RuntimeError("GPU exploded spectacularly")

    response = request(
        "POST",
        "/api/v1/tts",
        service,
        json={"text": "Hallo Flo"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Speech synthesis failed.",
    }


def test_tts_reports_busy_synthesis_as_conflict() -> None:
    service = FakeTtsService()
    service.error = TtsBusyError("already active")

    response = request(
        "POST",
        "/api/v1/tts",
        service,
        json={"text": "Hallo Flo"},
    )

    assert response.status_code == 409
