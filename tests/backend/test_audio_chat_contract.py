import asyncio
from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient

from app.api.routes.audio import get_audio_chat_service
from app.audio.capture import CaptureError
from app.main import create_app
from app.services.audio_text_chat import AudioStreamEvent


class FakeAudioChatService:
    def __init__(self) -> None:
        self.started = False
        self.aborted = False
        self.received_messages: list[dict[str, str]] | None = None
        self.received_chat_id: int | None = None
        self.error: Exception | None = None
        self.compression_error: str | None = None

    async def start_recording(self) -> None:
        if self.error:
            raise self.error
        self.started = True

    async def abort_recording(self) -> None:
        self.aborted = True

    def terminal_compression_error(self, chat_id: int | None) -> str | None:
        del chat_id
        return self.compression_error

    async def stream_response_with_transcription(
        self,
        messages: list[dict[str, str]],
        chat_id: int | None = None,
    ) -> AsyncIterator[AudioStreamEvent]:
        self.received_messages = messages
        self.received_chat_id = chat_id
        if self.error:
            raise self.error
        yield AudioStreamEvent(kind="transcript", text="Mein Text")
        yield AudioStreamEvent(kind="assistant", text="Hallo ")
        yield AudioStreamEvent(kind="assistant", text="Flo")

    async def stream_dialog_response_with_transcription(
        self,
        messages: list[dict[str, str]],
        chat_id: int | None = None,
    ) -> AsyncIterator[AudioStreamEvent]:
        self.received_messages = messages
        self.received_chat_id = chat_id
        yield AudioStreamEvent(kind="processing")
        yield AudioStreamEvent(kind="assistant", text="Hallo")


def request(method: str, path: str, service: FakeAudioChatService, **kwargs):
    async def send_request():
        application = create_app()

        async def override_audio_chat_service():
            return service

        application.dependency_overrides[
            get_audio_chat_service
        ] = override_audio_chat_service
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send_request())


def test_audio_recording_start_and_abort() -> None:
    service = FakeAudioChatService()

    start = request("POST", "/api/v1/audio/recording/start", service)
    abort = request("POST", "/api/v1/audio/recording/abort", service)

    assert start.status_code == 204
    assert abort.status_code == 204
    assert service.started is True
    assert service.aborted is True


def test_audio_stop_streams_response_with_conversation_context() -> None:
    service = FakeAudioChatService()
    messages = [
        {"role": "user", "content": "Mein Name ist Flo."},
        {"role": "assistant", "content": "Hallo Flo."},
    ]

    response = request(
        "POST",
        "/api/v1/audio/recording/stop",
        service,
        json={"chat_id": 42, "messages": messages},
    )

    assert response.status_code == 200
    assert service.received_messages == messages
    assert service.received_chat_id == 42
    assert response.text == (
        'event: transcript_chunk\ndata: {"text": "Mein Text"}\n\n'
        'event: chunk\ndata: {"text": "Hallo "}\n\n'
        'event: chunk\ndata: {"text": "Flo"}\n\n'
        "event: done\ndata: {}\n\n"
    )


def test_audio_stop_keeps_stream_contract_on_capture_failure() -> None:
    service = FakeAudioChatService()
    service.error = CaptureError("no recording")

    response = request(
        "POST",
        "/api/v1/audio/recording/stop",
        service,
        json={"messages": []},
    )

    assert response.status_code == 200
    assert response.text == "event: error\ndata: {}\n\n"


def test_dialog_turn_announces_processing_before_assistant_output() -> None:
    service = FakeAudioChatService()

    response = request(
        "POST",
        "/api/v1/audio/dialog/turn",
        service,
        json={"messages": []},
    )

    assert response.status_code == 200
    assert response.text == (
        "event: processing\ndata: {}\n\n"
        'event: chunk\ndata: {"text": "Hallo"}\n\n'
        "event: done\ndata: {}\n\n"
    )


def test_audio_stop_rejects_terminal_chat_and_discards_recording() -> None:
    service = FakeAudioChatService()
    service.compression_error = "chat_context_compression_failed"

    response = request(
        "POST",
        "/api/v1/audio/recording/stop",
        service,
        json={"chat_id": 42, "messages": []},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "chat_context_compression_failed"}
    assert service.aborted is True


def test_dialog_rejects_terminal_chat_before_recording() -> None:
    service = FakeAudioChatService()
    service.compression_error = "chat_context_compression_failed"

    response = request(
        "POST",
        "/api/v1/audio/dialog/turn",
        service,
        json={"chat_id": 42, "messages": []},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "chat_context_compression_failed"}
    assert service.aborted is False
