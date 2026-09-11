"""Unit and route-contract tests for the singleton backend audio call."""

import asyncio

import pytest
from fastapi import HTTPException

from app.api.routes import audio as audio_routes
import app.state as state_module
from app.api.schemas import AudioCallStartRequest
from app.services.audio_call import AudioCallAlreadyActiveError, AudioCallState


def test_audio_call_starts_unbound_and_can_bind_its_first_chat() -> None:
    state = AudioCallState()

    assert state.start() == state.get_status().__class__(True, None, False)
    assert state.bind_chat(42) == state.get_status().__class__(True, 42, False)


def test_audio_call_cannot_be_rebound_to_another_chat() -> None:
    state = AudioCallState()
    state.start(42)

    with pytest.raises(RuntimeError, match="already bound"):
        state.bind_chat(43)


def test_audio_call_turn_state_requires_an_active_call() -> None:
    state = AudioCallState()

    with pytest.raises(RuntimeError, match="without an active"):
        state.set_turn_active(True)

    state.start(42)
    assert state.set_turn_active(True).turn_active is True


def test_audio_call_end_clears_everything() -> None:
    state = AudioCallState()
    state.start(42)
    state.set_turn_active(True)

    assert state.end() == state.get_status().__class__(False, None, False)


def test_audio_call_queues_one_text_response_until_avatar_consumes_it() -> None:
    state = AudioCallState()
    state.start(42)
    state.set_turn_active(True)
    state.queue_speech("Antwort")

    assert state.get_status().pending_speech == "Antwort"
    assert state.consume_speech() == "Antwort"
    assert state.get_status().pending_speech is None
    assert state.set_turn_active(False).turn_active is False


def test_second_audio_call_is_rejected() -> None:
    state = AudioCallState()
    state.start()

    with pytest.raises(AudioCallAlreadyActiveError):
        state.start()


def test_call_routes_expose_and_clear_the_singleton_status(monkeypatch) -> None:
    state = AudioCallState()
    monkeypatch.setattr(state_module, "_audio_call_state", state)

    initial = asyncio.run(audio_routes.get_audio_call_status())
    started = audio_routes.start_audio_call(AudioCallStartRequest(chat_id=42))
    active = asyncio.run(audio_routes.get_audio_call_status())

    with pytest.raises(HTTPException) as exc_info:
        audio_routes.start_audio_call(AudioCallStartRequest())

    ended = audio_routes.end_audio_call()

    assert initial.model_dump() == {
        "active": False,
        "chat_id": None,
        "turn_active": False,
        "pending_speech": None,
    }
    assert started.model_dump() == {
        "active": True,
        "chat_id": 42,
        "turn_active": False,
        "pending_speech": None,
    }
    assert active == started
    assert exc_info.value.status_code == 409
    assert ended == initial
