import { describe, expect, it, vi } from "vitest";

import {
  useTransientChat,
  type ChatStreamer,
} from "../../frontend/src/composables/useTransientChat";

describe("useTransientChat", () => {
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


  it("keeps an audio message and streams a response with prior context", async () => {
    const audioStreamer = vi.fn(async (_messages, handlers) => {
      handlers.onChunk("**Hallo** ");
      handlers.onChunk("Flo");
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

    expect(chat.messages.value.slice(-2)).toEqual([
      {
        role: "user",
        content: "🎤 Sprachnachricht",
        kind: "audio",
      },
      {
        role: "assistant",
        content: "**Hallo** Flo",
      },
    ]);
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