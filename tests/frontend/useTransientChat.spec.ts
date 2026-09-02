import { describe, expect, it, vi } from "vitest";

import {
  useTransientChat,
  type ChatStreamer,
} from "../../frontend/src/composables/useTransientChat";

describe("useTransientChat", () => {
  it("adds the user turn and streams the assistant response", async () => {
    const streamer: ChatStreamer = async (
      message,
      handlers,
    ) => {
      expect(message).toBe("Hallo");
      handlers.onChunk("Hallo ");
      handlers.onChunk("Flo");
    };

    const chat = useTransientChat(streamer);
    chat.input.value = "Hallo";

    await chat.send();

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

  it("rolls back the whole turn and restores the exact prompt on stop", async () => {
    let resolveStream: (() => void) | undefined;

    const streamer: ChatStreamer = async (
      _message,
      handlers,
      signal,
    ) => {
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

    chat.stop();

    expect(chat.messages.value).toEqual([]);
    expect(chat.input.value).toBe("Zeile 1\nZeile 2");
    expect(chat.isGenerating.value).toBe(false);
    expect(chat.errorMessage.value).toBeUndefined();

    await sending;
    resolveStream?.();
  });

  it("rolls back and exposes a user-facing error after generation failure", async () => {
    const streamer: ChatStreamer = async (
      _message,
      handlers,
    ) => {
      handlers.onChunk("Teilantwort");
      throw new Error("technical details");
    };

    const chat = useTransientChat(streamer);
    chat.input.value = "Hallo";

    await chat.send();

    expect(chat.messages.value).toEqual([]);
    expect(chat.input.value).toBe("Hallo");
    expect(chat.isGenerating.value).toBe(false);
    expect(chat.errorMessage.value).toBe(
      "Antwort konnte nicht erzeugt werden.",
    );
  });
});
