"""Contract tests for persistent chat-management endpoints."""

import asyncio
from datetime import datetime

from httpx import ASGITransport, AsyncClient

from app.api.routes.chats import get_chat, get_chat_repository
from app.main import create_app
from app.mcp.security import bearer_token_for_principal
from app.persistence.models import Chat, TextMessage


class FakeChatRepository:
    def __init__(self) -> None:
        self.chats = {
            1: Chat(
                id=1,
                title="Erster Chat",
                title_is_manual=False,
                pinned=False,
                principal_id=1,
                created_at=datetime(2026, 9, 7, 20, 0, 0),
            ),
            2: Chat(
                id=2,
                title="Zweiter Chat",
                title_is_manual=False,
                pinned=True,
                principal_id=2,
                created_at=datetime(2026, 9, 7, 21, 0, 0),
            ),

        }
        self.messages = {
            1: [
                TextMessage(
                    id=10,
                    chat_id=1,
                    role="user",
                    content="Hallo",
                    created_at=datetime(2026, 9, 7, 20, 1, 0),
                ),
                TextMessage(
                    id=11,
                    chat_id=1,
                    role="assistant",
                    content="Hallo Flo",
                    created_at=datetime(2026, 9, 7, 20, 1, 1),
                ),
            ],
            2: [],
        }

    def list_chats(self):
        return [self.chats[2], self.chats[1]]

    def get_chat(self, chat_id: int):
        return self.chats.get(chat_id)

    def get_messages(self, chat_id: int):
        return self.messages.get(chat_id, [])

    def get_attachments_for_messages(self, message_ids: list[int]):
        return {message_id: [] for message_id in message_ids}

    def rename_chat(self, chat_id: int, title: str):
        chat = self.chats.get(chat_id)
        if chat is None:
            return None

        normalized = title.strip()
        if not normalized:
            raise ValueError("Chat title must not be empty.")
        if len(normalized) > 200:
            raise ValueError("Chat title must not exceed 200 characters.")

        chat.title = normalized
        chat.title_is_manual = True
        return chat

    def set_pinned(self, chat_id: int, pinned: bool):
        chat = self.chats.get(chat_id)
        if chat is None:
            return None

        chat.pinned = pinned
        return chat

    def delete_chat(self, chat_id: int) -> bool:
        if chat_id not in self.chats:
            return False


        del self.chats[chat_id]
        self.messages.pop(chat_id, None)
        return True


def request(method: str, path: str, json=None):
    async def send():
        application = create_app()
        repository = FakeChatRepository()
        application.dependency_overrides[get_chat_repository] = (
            lambda: repository
        )

        transport = ASGITransport(app=application)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.request(
                method,
                path,
                json=json,
                headers={"Authorization": f"Bearer {bearer_token_for_principal(1)}"},
            )

    return asyncio.run(send())


def test_list_chats_returns_repository_order() -> None:
    response = request("GET", "/api/v1/chats")

    assert response.status_code == 200
    assert [chat["id"] for chat in response.json()] == [2, 1]
    assert [chat["title"] for chat in response.json()] == [
        "Zweiter Chat",
        "Erster Chat",
    ]
    assert [chat["pinned"] for chat in response.json()] == [
        True,
        False,
    ]
    assert [chat["principal_id"] for chat in response.json()] == [2, 1]


def test_get_chat_returns_complete_history() -> None:

    response = request("GET", "/api/v1/chats/1")

    assert response.status_code == 200
    payload = response.json()

    assert payload["id"] == 1
    assert payload["title"] == "Erster Chat"
    assert payload["pinned"] is False
    assert payload["principal_id"] == 1
    assert payload["compression_error_code"] is None
    assert [message["id"] for message in payload["messages"]] == [10, 11]

    assert [message["role"] for message in payload["messages"]] == [
        "user",
        "assistant",
    ]
    assert [message["content"] for message in payload["messages"]] == [
        "Hallo",
        "Hallo Flo",
    ]
    assert "created_at" in payload
    assert all(
        "created_at" in message
        for message in payload["messages"]
    )


def test_get_chat_exposes_terminal_compression_error() -> None:
    repository = FakeChatRepository()
    repository.chats[1].compression_error_code = (
        "chat_context_compression_failed"
    )

    detail = get_chat(1, repository)  # type: ignore[arg-type]

    assert detail.compression_error_code == "chat_context_compression_failed"


def test_get_unknown_chat_returns_404() -> None:
    response = request("GET", "/api/v1/chats/999")

    assert response.status_code == 404


def test_rename_chat_trims_title() -> None:
    response = request(
        "PATCH",
        "/api/v1/chats/1",
        json={"title": "  Mein Chat  "},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Mein Chat"


def test_rename_chat_rejects_empty_title_after_trim() -> None:
    response = request(
        "PATCH",
        "/api/v1/chats/1",
        json={"title": "   "},
    )

    assert response.status_code == 422


def test_rename_chat_rejects_title_over_200_characters() -> None:
    response = request(
        "PATCH",
        "/api/v1/chats/1",
        json={"title": "x" * 201},
    )

    assert response.status_code == 422


def test_rename_unknown_chat_returns_404() -> None:
    response = request(
        "PATCH",
        "/api/v1/chats/999",
        json={"title": "Mein Chat"},
    )

    assert response.status_code == 404


def test_set_chat_pinned() -> None:
    response = request(
        "PATCH",
        "/api/v1/chats/1/pinned",
        json={"pinned": True},
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["pinned"] is True


def test_set_chat_unpinned() -> None:
    response = request(
        "PATCH",
        "/api/v1/chats/2/pinned",
        json={"pinned": False},
    )

    assert response.status_code == 200
    assert response.json()["id"] == 2
    assert response.json()["pinned"] is False


def test_set_pinned_unknown_chat_returns_404() -> None:
    response = request(
        "PATCH",
        "/api/v1/chats/999/pinned",
        json={"pinned": True},
    )

    assert response.status_code == 404



def test_delete_chat_returns_204() -> None:
    response = request("DELETE", "/api/v1/chats/1")

    assert response.status_code == 204
    assert response.content == b""


def test_delete_unknown_chat_returns_404() -> None:
    response = request("DELETE", "/api/v1/chats/999")

    assert response.status_code == 404


def test_chat_summary_includes_agent_name_or_none() -> None:
    from app.persistence.models import Agent

    class AgentChatRepository(FakeChatRepository):
        def __init__(self):
            super().__init__()
            self.chats[1].agent = None
            agent = Agent(key="test-agent", name="Hedwig Agent", principal_id=99)
            self.chats[2].agent = agent
            self.chats[2].principal_id = None

    async def run_test():
        application = create_app()
        application.dependency_overrides[get_chat_repository] = lambda: AgentChatRepository()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/chats",
                headers={"Authorization": f"Bearer {bearer_token_for_principal(1)}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data[0]["id"] == 2
            assert data[0]["agent_name"] == "Hedwig Agent"
            assert data[0]["principal_id"] == 99
            assert data[1]["id"] == 1
            assert data[1]["agent_name"] is None

    asyncio.run(run_test())
