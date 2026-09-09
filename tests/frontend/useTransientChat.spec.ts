import { describe, expect, it, vi } from "vitest";

import {
  useTransientChat,
  type ChatManagementClient,
  type ChatStreamer,
} from "../../frontend/src/composables/useTransientChat";

function createChatManagement(
  overrides: Partial<ChatManagementClient> = {},
): ChatManagementClient {
  return {
    getChats: vi.fn().mockResolvedValue([]),
    getChat: vi.fn(),
    renameChat: vi.fn(),
    setChatPinned: vi.fn(),
    deleteChat: vi.fn(),
    ...overrides,
  };
}


describe("useTransientChat", () => {
  it("renames a chat only after the backend succeeds", async () => {
    const management = createChatManagement({
      getChats: vi.fn().mockResolvedValue([
        {
          id: 42,
          title: "Original",
          pinned: false,
          created_at: "2026-09-07T10:00:00",
        },
      ]),
      renameChat: vi.fn().mockResolvedValue({
        id: 42,
        title: "Neuer Name",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      }),
    });

    const chat = useTransientChat(
      undefined,
      undefined,
      management,
    );

    await chat.refreshChats();
    const result = await chat.renameChat(42, "Neuer Name");

    expect(result).toBe(true);
    expect(management.renameChat).toHaveBeenCalledWith(
      42,
      "Neuer Name",
    );
    expect(chat.chatSummaries.value[0].title).toBe("Neuer Name");
  });

  it("keeps the old title when renaming fails", async () => {
    const management = createChatManagement({
      getChats: vi.fn().mockResolvedValue([
        {
          id: 42,
          title: "Original",
          pinned: false,
          created_at: "2026-09-07T10:00:00",
        },
      ]),
      renameChat: vi.fn().mockRejectedValue(
        new Error("failed"),
      ),
    });

    const chat = useTransientChat(
      undefined,
      undefined,
      management,
    );

    await chat.refreshChats();
    const result = await chat.renameChat(42, "Neuer Name");

    expect(result).toBe(false);
    expect(chat.chatSummaries.value[0].title).toBe("Original");
    expect(chat.errorMessage.value).toBe(
      "Chat konnte nicht umbenannt werden.",
    );
  });

  it("updates pinned state only after the backend succeeds", async () => {
    const management = createChatManagement({
      getChats: vi.fn().mockResolvedValue([
        {
          id: 42,
          title: "Chat",
          pinned: false,
          created_at: "2026-09-07T10:00:00",
        },
      ]),
      setChatPinned: vi.fn().mockResolvedValue({
        id: 42,
        title: "Chat",
        pinned: true,
        created_at: "2026-09-07T10:00:00",
      }),
    });

    const chat = useTransientChat(
      undefined,
      undefined,
      management,
    );

    await chat.refreshChats();
    const result = await chat.setChatPinned(42, true);

    expect(result).toBe(true);
    expect(management.setChatPinned).toHaveBeenCalledWith(
      42,
      true,
    );
    expect(chat.chatSummaries.value[0].pinned).toBe(true);
  });

  it("keeps pinned state unchanged when updating it fails", async () => {
    const management = createChatManagement({
      getChats: vi.fn().mockResolvedValue([
        {
          id: 42,
          title: "Chat",
          pinned: false,
          created_at: "2026-09-07T10:00:00",
        },
      ]),
      setChatPinned: vi.fn().mockRejectedValue(
        new Error("failed"),
      ),
    });

    const chat = useTransientChat(
      undefined,
      undefined,
      management,
    );

    await chat.refreshChats();
    const result = await chat.setChatPinned(42, true);

    expect(result).toBe(false);
    expect(chat.chatSummaries.value[0].pinned).toBe(false);
    expect(chat.errorMessage.value).toBe(
      "Pin-Status konnte nicht geändert werden.",
    );
  });

  it("deletes a chat from local state after the backend succeeds", async () => {
    const management = createChatManagement({
      getChats: vi.fn().mockResolvedValue([
        {
          id: 42,
          title: "Chat",
          pinned: false,
          created_at: "2026-09-07T10:00:00",
        },
      ]),
      getChat: vi.fn().mockResolvedValue({
        id: 42,
        title: "Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
        messages: [
          {
            id: 1,
            role: "user",
            content: "Hallo",
            created_at: "2026-09-07T10:00:01",
          },
        ],
      }),
      deleteChat: vi.fn().mockResolvedValue(undefined),
    });

    const chat = useTransientChat(
      undefined,
      undefined,
      management,
    );

    await chat.refreshChats();
    await chat.selectChat(42);

    const result = await chat.deleteChat(42);

    expect(result).toBe(true);
    expect(management.deleteChat).toHaveBeenCalledWith(42);
    expect(chat.chatSummaries.value).toEqual([]);
    expect(chat.selectedChatId.value).toBeUndefined();
    expect(chat.messages.value).toEqual([]);
    expect(chat.input.value).toBe("");
  });

  it("keeps a chat unchanged when deleting fails", async () => {
    const management = createChatManagement({
      getChats: vi.fn().mockResolvedValue([
        {
          id: 42,
          title: "Chat",
          pinned: false,
          created_at: "2026-09-07T10:00:00",
        },
      ]),
      deleteChat: vi.fn().mockRejectedValue(
        new Error("failed"),
      ),
    });

    const chat = useTransientChat(
      undefined,
      undefined,
      management,
    );

    await chat.refreshChats();
    const result = await chat.deleteChat(42);

    expect(result).toBe(false);
    expect(chat.chatSummaries.value).toHaveLength(1);
    expect(chat.chatSummaries.value[0].id).toBe(42);
    expect(chat.errorMessage.value).toBe(
      "Chat konnte nicht gelöscht werden.",
    );
  });

  it("adds the first user turn, accepts its chat ID and streams the response", async () => {

    const streamer: ChatStreamer = async (
      request,
      handlers,
    ) => {
      expect(request).toEqual({
        message: "Hallo",
      });

      handlers.onChat?.(42);
      handlers.onChunk("Hallo ");
      handlers.onChunk("Flo");
    };

    const chat = useTransientChat(streamer);
    chat.input.value = "Hallo";

    await chat.send();

    expect(chat.selectedChatId.value).toBe(42);
    expect(chat.messages.value).toEqual([
      {
        role: "user",
        content: "Hallo",
      },
      {
        role: "assistant",
        content: "Hallo Flo",
      },
    ]);
    expect(chat.input.value).toBe("");
    expect(chat.isGenerating.value).toBe(false);
    expect(chat.errorMessage.value).toBeUndefined();
  });

  it("rolls back the whole turn without overwriting a new composer draft on stop", async () => {

    let resolveStream: (() => void) | undefined;

    const streamer: ChatStreamer = async (
      _request,
      handlers,
      signal,
    ) => {
      handlers.onChat?.(42);
      handlers.onChunk("Teilantwort");

      await new Promise<void>((resolve, reject) => {
        resolveStream = resolve;

        signal.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    };

    const chat = useTransientChat(streamer);
    chat.input.value = "Zeile 1\nZeile 2";

    const sending = chat.send();

    await vi.waitFor(() => {
      expect(chat.messages.value[1]?.content).toBe("Teilantwort");
    });

    chat.input.value = "Nächster Prompt";
    chat.stop();

    expect(chat.messages.value).toEqual([]);
    expect(chat.input.value).toBe("Nächster Prompt");
    expect(chat.isGenerating.value).toBe(false);

    expect(chat.errorMessage.value).toBeUndefined();

    await sending;
    resolveStream?.();
  });

  it("rolls back and exposes a user-facing error without overwriting a new draft", async () => {
    let rejectStream: ((error: Error) => void) | undefined;

    const streamer: ChatStreamer = async (
      _request,
      handlers,
    ) => {
      handlers.onChat?.(42);
      handlers.onChunk("Teilantwort");

      await new Promise<void>((_resolve, reject) => {
        rejectStream = reject;
      });
    };

    const chat = useTransientChat(streamer);
    chat.input.value = "Hallo";

    const sending = chat.send();

    await vi.waitFor(() => {
      expect(chat.messages.value[1]?.content).toBe("Teilantwort");
    });

    chat.input.value = "Nächster Prompt";
    rejectStream?.(new Error("technical details"));

    await sending;

    expect(chat.messages.value).toEqual([]);
    expect(chat.input.value).toBe("Nächster Prompt");
    expect(chat.isGenerating.value).toBe(false);
    expect(chat.errorMessage.value).toBe(
      "Antwort konnte nicht erzeugt werden.",
    );
  });


  it("replaces an audio placeholder with the streamed transcript", async () => {
    const audioStreamer = vi.fn(async (_messages, handlers) => {
      handlers.onChat?.(42);
      handlers.onTranscriptChunk?.("Mein ");
      handlers.onChunk("**Hallo** ");
      handlers.onTranscriptChunk?.("Text");
      handlers.onChunk("Flo");
      handlers.onDone?.();
    });

    const chat = useTransientChat(undefined, audioStreamer);

    chat.messages.value.push(
      { role: "user", content: "Mein Name ist Flo." },
      { role: "assistant", content: "Hallo Flo." },
    );

    await chat.sendAudio();

    expect(audioStreamer.mock.calls[0][0]).toEqual([
      { role: "user", content: "Mein Name ist Flo." },
      { role: "assistant", content: "Hallo Flo." },
    ]);

    expect(chat.selectedChatId.value).toBe(42);
    expect(chat.messages.value.slice(-2)).toEqual([
      {
        role: "user",
        content: "Mein Text",
        kind: "audio",
      },
      {
        role: "assistant",
        content: "**Hallo** Flo",
      },
    ]);
  });

  it("keeps the audio placeholder when transcription fails", async () => {
    const audioStreamer = vi.fn(async (_messages, handlers) => {
      handlers.onTranscriptChunk?.("Teil");
      handlers.onTranscriptError?.();
      handlers.onChunk("Antwort");
      handlers.onDone?.();
    });
    const chat = useTransientChat(undefined, audioStreamer);

    await chat.sendAudio();

    expect(chat.messages.value).toEqual([
      {
        role: "user",
        content: "🎤 Sprachnachricht",
        kind: "audio",
      },
      {
        role: "assistant",
        content: "Antwort",
      },
    ]);
    expect(chat.errorMessage.value).toBeUndefined();
  });

  it("keeps an audio message when response generation fails", async () => {
    const audioStreamer = vi.fn().mockRejectedValue(
      new Error("failed"),
    );
    const chat = useTransientChat(undefined, audioStreamer);

    await chat.sendAudio();

    expect(chat.messages.value).toEqual([
      {
        role: "user",
        content: "🎤 Sprachnachricht",
        kind: "audio",
      },
    ]);
    expect(chat.errorMessage.value).toBe(
      "Sprachantwort konnte nicht erzeugt werden.",
    );
  });
});