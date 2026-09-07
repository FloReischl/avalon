import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  abortAudioRecordingMock,
  notifyTtsPlaybackEndedMock,
  startAudioRecordingMock,
  streamAudioResponseMock,
  streamChatMessageMock,
  synthesizeSpeechMock,
} = vi.hoisted(() => ({
  abortAudioRecordingMock: vi.fn(),
  notifyTtsPlaybackEndedMock: vi.fn(),
  startAudioRecordingMock: vi.fn(),
  streamAudioResponseMock: vi.fn(),
  streamChatMessageMock: vi.fn(),
  synthesizeSpeechMock: vi.fn(),
}));


vi.mock("../../frontend/src/services/backend", async (importOriginal) => {
  const original = await importOriginal<
    typeof import("../../frontend/src/services/backend")
  >();

  return {
    ...original,
    abortAudioRecording: abortAudioRecordingMock,
    notifyTtsPlaybackEnded: notifyTtsPlaybackEndedMock,
    startAudioRecording: startAudioRecordingMock,
    streamAudioResponse: streamAudioResponseMock,
    streamChatMessage: streamChatMessageMock,
    synthesizeSpeech: synthesizeSpeechMock,

  };
});

import ChatWindow from "../../frontend/src/ChatWindow.vue";

describe("ChatWindow", () => {
  beforeEach(() => {
    abortAudioRecordingMock.mockReset();
    abortAudioRecordingMock.mockResolvedValue(undefined);
    notifyTtsPlaybackEndedMock.mockReset();
    notifyTtsPlaybackEndedMock.mockResolvedValue(undefined);
    startAudioRecordingMock.mockReset();
    startAudioRecordingMock.mockResolvedValue(undefined);
    streamAudioResponseMock.mockReset();
    streamChatMessageMock.mockReset();
    synthesizeSpeechMock.mockReset();

  });

  it("renders the chat sidebar with its default width", () => {
    const wrapper = mount(ChatWindow);

    expect(
      wrapper.get('[data-testid="chat-sidebar"]').attributes("style"),
    ).toContain("width: 280px");
  });

  it("renders the generic composer placeholder", () => {
    const wrapper = mount(ChatWindow);

    expect(
      wrapper.get('[data-testid="chat-input"]').attributes("placeholder"),
    ).toBe("Dein Prompt hier");
  });

  it("renders composer actions as labelled icon buttons", () => {
    const wrapper = mount(ChatWindow);

    const newChatButton = wrapper.get('[data-testid="new-chat"]');
    const sendButton = wrapper.get('[data-testid="send-chat"]');
    const expandButton = wrapper.get('[data-testid="toggle-composer"]');
    const audioButton = wrapper.get('[data-testid="record-audio"]');

    expect(newChatButton.attributes("aria-label")).toBe("Neuer Chat");
    expect(newChatButton.attributes("title")).toBe("Neuer Chat");
    expect(newChatButton.text()).toBe("");

    expect(sendButton.attributes("aria-label")).toBe("Nachricht senden");
    expect(sendButton.attributes("title")).toBe("Nachricht senden");
    expect(sendButton.text()).toBe("");

    expect(expandButton.attributes("aria-label")).toBe("Eingabe vergrößern");
    expect(expandButton.attributes("title")).toBe("Eingabe vergrößern");
    expect(expandButton.text()).toBe("");

    expect(audioButton.attributes("aria-label")).toBe(
      "Sprachnachricht aufnehmen",
    );
    expect(audioButton.attributes("title")).toBe(
      "Zum Aufnehmen gedrückt halten",
    );
  });

  it("records while held and renders the streamed audio response", async () => {
    streamAudioResponseMock.mockImplementation(
      async (_messages, handlers) => {
        handlers.onChunk("**Hallo** ");
        handlers.onChunk("Flo");
      },
    );
    const wrapper = mount(ChatWindow);
    const audioButton = wrapper.get('[data-testid="record-audio"]');

    await audioButton.trigger("pointerdown", { button: 0 });
    await flushPromises();

    expect(startAudioRecordingMock).toHaveBeenCalledTimes(1);
    expect(wrapper.get('[data-testid="recording-status"]').text()).toContain(
      "30 s",
    );

    window.dispatchEvent(new Event("pointerup"));
    await flushPromises();

    expect(streamAudioResponseMock).toHaveBeenCalledWith(
      [],
      expect.any(Object),
      expect.any(AbortSignal),
    );
    expect(wrapper.get('[data-testid="message-user"]').text()).toContain(
      "🎤 Sprachnachricht",
    );
    expect(wrapper.get('[data-testid="message-user"]').classes()).toContain(
      "message-audio",
    );
    expect(
      wrapper.get('[data-testid="message-assistant"] strong').text(),
    ).toBe("Hallo");
    expect(wrapper.get('[data-testid="message-assistant"]').text()).toContain(
      "Hallo Flo",
    );
  });

  it("finishes a quick release after recording start completes", async () => {
    let resolveStart: (() => void) | undefined;
    startAudioRecordingMock.mockImplementation(
      () => new Promise<void>((resolve) => {
        resolveStart = resolve;
      }),
    );
    streamAudioResponseMock.mockResolvedValue(undefined);

    const wrapper = mount(ChatWindow);
    const audioButton = wrapper.get('[data-testid="record-audio"]');

    void audioButton.trigger("pointerdown", { button: 0 });
    await flushPromises();

    expect(startAudioRecordingMock).toHaveBeenCalledTimes(1);

    window.dispatchEvent(new Event("pointerup"));
    await flushPromises();

    expect(streamAudioResponseMock).not.toHaveBeenCalled();

    resolveStart?.();
    await flushPromises();

    expect(streamAudioResponseMock).toHaveBeenCalledTimes(1);
    expect(abortAudioRecordingMock).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid="recording-status"]').exists()).toBe(
      false,
    );
  });

  it("expands and collapses the composer without replacing its input", async () => {
    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');
    const inputElement = input.element as HTMLTextAreaElement;

    await input.setValue("Zeile 1\nZeile 2");
    inputElement.setSelectionRange(4, 4);

    await wrapper.get('[data-testid="toggle-composer"]').trigger("click");

    expect(
      wrapper.get('[data-testid="messages"]').attributes("style"),
    ).toContain("display: none");
    expect(wrapper.get(".composer").classes()).toContain("composer--expanded");
    expect(wrapper.get('[data-testid="toggle-composer"]').attributes("aria-label")).toBe(
      "Eingabe verkleinern",
    );
    expect(wrapper.get('[data-testid="chat-input"]').element).toBe(inputElement);
    expect(inputElement.value).toBe("Zeile 1\nZeile 2");
    expect(inputElement.selectionStart).toBe(4);

    await wrapper.get('[data-testid="toggle-composer"]').trigger("click");

    expect(
      wrapper.get('[data-testid="messages"]').attributes("style") ?? "",
    ).not.toContain("display: none");
    expect(wrapper.get(".composer").classes()).not.toContain("composer--expanded");
    expect(wrapper.get('[data-testid="chat-input"]').element).toBe(inputElement);
  });

  it("resizes the sidebar and constrains its width", async () => {
    const originalInnerWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 1000,
    });

    try {
      const wrapper = mount(ChatWindow);
      const splitter = wrapper.get('[data-testid="sidebar-splitter"]');

      await splitter.trigger("pointerdown", { clientX: 280 });

      window.dispatchEvent(
        new MouseEvent("pointermove", { clientX: 400 }),
      );

      await wrapper.vm.$nextTick();

      expect(
        wrapper.get('[data-testid="chat-sidebar"]').attributes("style"),
      ).toContain("width: 400px");

      window.dispatchEvent(
        new MouseEvent("pointermove", { clientX: 1000 }),
      );

      await wrapper.vm.$nextTick();

      expect(
        wrapper.get('[data-testid="chat-sidebar"]').attributes("style"),
      ).toContain("width: 450px");

      window.dispatchEvent(new Event("pointerup"));
    } finally {
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        value: originalInnerWidth,
      });
    }
  });

  it("sends a single-line message with Enter and renders streamed chunks", async () => {
    streamChatMessageMock.mockImplementation(
      async (_message, handlers) => {
        handlers.onChunk("Hallo ");
        handlers.onChunk("Flo");
      },
    );

    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("Hallo");
    await input.trigger("keydown", { key: "Enter" });
    await flushPromises();

    expect(streamChatMessageMock).toHaveBeenCalledTimes(1);
    expect(streamChatMessageMock.mock.calls[0][0]).toEqual([
      { role: "user", content: "Hallo" },
    ]);
    expect(wrapper.get('[data-testid="message-user"]').text()).toContain(
      "Hallo",
    );
    expect(
      wrapper.get('[data-testid="message-assistant"]').text(),
    ).toContain("Hallo Flo");
  });

  it("renders role-specific message actions", async () => {
    streamChatMessageMock.mockImplementation(
      async (_message, handlers) => {
        handlers.onChunk("Antwort");
      },
    );

    const wrapper = mount(ChatWindow);

    await wrapper.get('[data-testid="chat-input"]').setValue("Frage");
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    const userActions = wrapper.get(
      '[data-testid="message-actions-user"]',
    );
    const assistantActions = wrapper.get(
      '[data-testid="message-actions-assistant"]',
    );

    expect(userActions.find('[data-testid="copy-message"]').exists()).toBe(true);
    expect(userActions.find('[data-testid="edit-message"]').exists()).toBe(true);
    expect(userActions.find('[data-testid="read-aloud-message"]').exists()).toBe(false);
    expect(userActions.find('[data-testid="branch-message"]').exists()).toBe(false);

    expect(assistantActions.find('[data-testid="copy-message"]').exists()).toBe(true);
    expect(assistantActions.find('[data-testid="read-aloud-message"]').exists()).toBe(true);
    expect(assistantActions.find('[data-testid="branch-message"]').exists()).toBe(true);
    expect(assistantActions.find('[data-testid="edit-message"]').exists()).toBe(false);

    expect(
      assistantActions.get('[data-testid="read-aloud-message"]').attributes("disabled"),
    ).toBeUndefined();
    expect(
      assistantActions.get('[data-testid="branch-message"]').attributes("disabled"),
    ).toBeDefined();

    expect(
      userActions.get('[data-testid="edit-message"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("reads rendered assistant text aloud and reports playback end", async () => {
    streamChatMessageMock.mockImplementation(
      async (_message, handlers) => {
        handlers.onChunk("**Hallo** `Flo`");
      },
    );

    synthesizeSpeechMock.mockResolvedValue({
      playbackId: "playback-123",
      response: new Response(
        new Blob(["wav"], { type: "audio/wav" }),
        { status: 200 },
      ),
    });

    const audios: AudioMock[] = [];

    class AudioMock {
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      play = vi.fn().mockResolvedValue(undefined);
      pause = vi.fn();

      constructor() {
        audios.push(this);
      }
    }


    vi.stubGlobal("Audio", AudioMock);
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:tts"),
      revokeObjectURL: vi.fn(),
    });

    try {
      const wrapper = mount(ChatWindow);

      await wrapper.get('[data-testid="chat-input"]').setValue("Frage");
      await wrapper.get('[data-testid="send-chat"]').trigger("click");
      await flushPromises();

      await wrapper
        .get('[data-testid="message-actions-assistant"]')
        .get('[data-testid="read-aloud-message"]')
        .trigger("click");
      await flushPromises();

      expect(synthesizeSpeechMock).toHaveBeenCalledTimes(1);
      expect(synthesizeSpeechMock.mock.calls[0][0]).toContain("Hallo");
      expect(synthesizeSpeechMock.mock.calls[0][0]).toContain("Flo");
      expect(audios).toHaveLength(1);
      expect(audios[0].play).toHaveBeenCalledTimes(1);

      audios[0].onended?.();
      await flushPromises();

      expect(notifyTtsPlaybackEndedMock).toHaveBeenCalledWith(
        "playback-123",
      );
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("replaces an active read-aloud playback instead of queueing it", async () => {
    streamChatMessageMock.mockImplementation(
      async (_message, handlers) => {
        handlers.onChunk("Antwort");
      },
    );

    synthesizeSpeechMock
      .mockResolvedValueOnce({
        playbackId: "playback-1",
        response: new Response(new Blob(["wav-1"])),
      })
      .mockResolvedValueOnce({
        playbackId: "playback-2",
        response: new Response(new Blob(["wav-2"])),
      });

    const audios: Array<{
      onended: (() => void) | null;
      onerror: (() => void) | null;
      play: ReturnType<typeof vi.fn>;
      pause: ReturnType<typeof vi.fn>;
    }> = [];

    class AudioMock {
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      play = vi.fn().mockResolvedValue(undefined);
      pause = vi.fn();

      constructor() {
        audios.push(this);
      }
    }

    vi.stubGlobal("Audio", AudioMock);
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:tts"),
      revokeObjectURL: vi.fn(),
    });

    try {
      const wrapper = mount(ChatWindow);

      await wrapper.get('[data-testid="chat-input"]').setValue("Frage");
      await wrapper.get('[data-testid="send-chat"]').trigger("click");
      await flushPromises();

      const button = wrapper
        .get('[data-testid="message-actions-assistant"]')
        .get('[data-testid="read-aloud-message"]');

      await button.trigger("click");
      await flushPromises();

      await button.trigger("click");
      await flushPromises();

      expect(synthesizeSpeechMock).toHaveBeenCalledTimes(2);
      expect(audios).toHaveLength(2);
      expect(audios[0].pause).toHaveBeenCalledTimes(1);
      expect(audios[1].play).toHaveBeenCalledTimes(1);
      expect(notifyTtsPlaybackEndedMock).toHaveBeenCalledWith(
        "playback-1",
      );
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("shows a chat error when read aloud fails", async () => {
    streamChatMessageMock.mockImplementation(
      async (_message, handlers) => {
        handlers.onChunk("Antwort");
      },
    );
    synthesizeSpeechMock.mockRejectedValue(
      new Error("tts failed"),
    );

    const wrapper = mount(ChatWindow);

    await wrapper.get('[data-testid="chat-input"]').setValue("Frage");
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    await wrapper
      .get('[data-testid="message-actions-assistant"]')
      .get('[data-testid="read-aloud-message"]')
      .trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-testid="chat-error"]').text()).toBe(
      "Vorlesen fehlgeschlagen.",
    );
  });

  it("copies Markdown source and rendered HTML together", async () => {

    streamChatMessageMock.mockImplementation(
      async (_message, handlers) => {
        handlers.onChunk("**fett**");
      },
    );

    const write = vi.fn().mockResolvedValue(undefined);
    const writeText = vi.fn().mockResolvedValue(undefined);

    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        write,
        writeText,
      },
    });

    class BlobMock {
      parts: unknown[];
      type: string;

      constructor(
        parts: unknown[],
        options?: BlobPropertyBag,
      ) {
        this.parts = parts;
        this.type = options?.type ?? "";
      }
    }

    class ClipboardItemMock {
      data: Record<string, BlobMock>;

      constructor(data: Record<string, BlobMock>) {
        this.data = data;
      }
    }

    vi.stubGlobal("Blob", BlobMock);
    vi.stubGlobal("ClipboardItem", ClipboardItemMock);

    try {
      const wrapper = mount(ChatWindow);

      await wrapper.get('[data-testid="chat-input"]').setValue("Frage");
      await wrapper.get('[data-testid="send-chat"]').trigger("click");
      await flushPromises();

      await wrapper
        .get('[data-testid="message-actions-assistant"]')
        .get('[data-testid="copy-message"]')
        .trigger("click");

      expect(write).toHaveBeenCalledTimes(1);
      expect(writeText).not.toHaveBeenCalled();

      const clipboardItem = write.mock.calls[0][0][0] as ClipboardItemMock;

      expect(
        clipboardItem.data["text/plain"].parts.join(""),
      ).toBe("**fett**");
      expect(
        clipboardItem.data["text/plain"].type,
      ).toBe("text/plain");

      expect(
        clipboardItem.data["text/html"].parts.join(""),
      ).toContain("<strong>fett</strong>");
      expect(
        clipboardItem.data["text/html"].type,
      ).toBe("text/html");
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("falls back to plain Markdown copy when multi-format clipboard is unavailable", async () => {
    streamChatMessageMock.mockImplementation(
      async (_message, handlers) => {
        handlers.onChunk("**fett**");
      },
    );

    const writeText = vi.fn().mockResolvedValue(undefined);

    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText,
      },
    });

    const wrapper = mount(ChatWindow);

    await wrapper.get('[data-testid="chat-input"]').setValue("Frage");
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    await wrapper
      .get('[data-testid="message-actions-assistant"]')
      .get('[data-testid="copy-message"]')
      .trigger("click");

    expect(writeText).toHaveBeenCalledWith("**fett**");
  });

  it("keeps Enter as newline behavior once the input contains a newline", async () => {
    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("Zeile 1\nZeile 2");
    await input.trigger("keydown", { key: "Enter" });

    expect(streamChatMessageMock).not.toHaveBeenCalled();
  });

  it("always sends with Ctrl+Enter", async () => {
    streamChatMessageMock.mockResolvedValue(undefined);

    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("Zeile 1\nZeile 2");
    await input.trigger("keydown", {
      key: "Enter",
      ctrlKey: true,
    });
    await flushPromises();

    expect(streamChatMessageMock).toHaveBeenCalledTimes(1);
    expect(streamChatMessageMock.mock.calls[0][0]).toEqual([
      {
        role: "user",
        content: "Zeile 1\nZeile 2",
      },
    ]);
  });

  it("does not send with Shift+Enter", async () => {
    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("Hallo");
    await input.trigger("keydown", {
      key: "Enter",
      shiftKey: true,
    });

    expect(streamChatMessageMock).not.toHaveBeenCalled();
  });

  it("disables input and offers Stop while generating", async () => {
    streamChatMessageMock.mockImplementation(
      () => new Promise(() => {}),
    );

    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("Hallo");
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    expect(
      wrapper.get('[data-testid="chat-input"]').attributes("disabled"),
    ).toBeDefined();
    expect(wrapper.find('[data-testid="send-chat"]').exists()).toBe(false);

    const stopButton = wrapper.get('[data-testid="stop-chat"]');
    expect(stopButton.exists()).toBe(true);
    expect(stopButton.attributes("aria-label")).toBe("Antwort stoppen");
    expect(stopButton.attributes("title")).toBe("Antwort stoppen");
    expect(stopButton.text()).toBe("");
  });

  it("stops and rolls back the current turn", async () => {
    streamChatMessageMock.mockImplementation(
      (_message, handlers, signal) => {
        handlers.onChunk("Teilantwort");

        return new Promise<void>((_resolve, reject) => {
          signal.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        });
      },
    );

    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("Mein Prompt");
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-testid="stop-chat"]').trigger("click");
    await flushPromises();

    expect(wrapper.findAll(".message")).toHaveLength(0);
    expect(
      (wrapper.get('[data-testid="chat-input"]').element as HTMLTextAreaElement)
        .value,
    ).toBe("Mein Prompt");
    expect(wrapper.find('[data-testid="chat-error"]').exists()).toBe(false);
  });

  it("shows a short error and restores the prompt on generation failure", async () => {
    streamChatMessageMock.mockRejectedValue(
      new Error("technical details"),
    );

    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("Hallo");
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    expect(wrapper.findAll(".message")).toHaveLength(0);
    expect(wrapper.get('[data-testid="chat-error"]').text()).toBe(
      "Antwort konnte nicht erzeugt werden.",
    );
    expect(
      (wrapper.get('[data-testid="chat-input"]').element as HTMLTextAreaElement)
        .value,
    ).toBe("Hallo");
  });

  it("starts a new empty chat and aborts a running response", async () => {
    let aborted = false;

    streamChatMessageMock.mockImplementation(
      (_message, _handlers, signal) => (
        new Promise<void>((_resolve, reject) => {
          signal.addEventListener("abort", () => {
            aborted = true;
            reject(new DOMException("Aborted", "AbortError"));
          });
        })
      ),
    );

    const wrapper = mount(ChatWindow);

    await wrapper.get('[data-testid="chat-input"]').setValue("Hallo");
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-testid="new-chat"]').trigger("click");
    await flushPromises();

    expect(aborted).toBe(true);
    expect(wrapper.findAll(".message")).toHaveLength(0);
    expect(
      (wrapper.get('[data-testid="chat-input"]').element as HTMLTextAreaElement)
        .value,
    ).toBe("");
    expect(wrapper.find('[data-testid="chat-error"]').exists()).toBe(false);
  });
});
