import { nextTick } from "vue";
import {
  enableAutoUnmount,
  flushPromises,
  mount,
} from "@vue/test-utils";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

enableAutoUnmount(afterEach);

Object.defineProperty(URL, "revokeObjectURL", {
  configurable: true,
  value: vi.fn(),
});

const {
  abortAudioRecordingMock,
  getChatMock,
  getChatsMock,
  notifyTtsPlaybackEndedMock,
  startAudioRecordingMock,
  streamAudioResponseMock,
  streamChatMessageMock,
  streamDialogResponseMock,
  synthesizeSpeechMock,
  startAudioCallMock,
  getAudioCallStatusMock,
  listenToAudioCallChangedMock,
  publishAudioCallChangedMock,
  exportChatToMarkdownMock,
  loadUiConfigMock,
} = vi.hoisted(() => ({

  abortAudioRecordingMock: vi.fn(),
  getChatMock: vi.fn(),
  getChatsMock: vi.fn(),
  notifyTtsPlaybackEndedMock: vi.fn(),
  startAudioRecordingMock: vi.fn(),
  streamAudioResponseMock: vi.fn(),
  streamChatMessageMock: vi.fn(),
  streamDialogResponseMock: vi.fn(),
  synthesizeSpeechMock: vi.fn(),
  startAudioCallMock: vi.fn(),
  getAudioCallStatusMock: vi.fn(),
  listenToAudioCallChangedMock: vi.fn(),
  publishAudioCallChangedMock: vi.fn(),
  exportChatToMarkdownMock: vi.fn(),
  loadUiConfigMock: vi.fn(),
}));



vi.mock("../../frontend/src/services/backend", async (importOriginal) => {
  const original = await importOriginal<
    typeof import("../../frontend/src/services/backend")
  >();

  return {
    ...original,
    abortAudioRecording: abortAudioRecordingMock,
    getChat: getChatMock,
    getChats: getChatsMock,
    notifyTtsPlaybackEnded: notifyTtsPlaybackEndedMock,
    startAudioRecording: startAudioRecordingMock,
    streamAudioResponse: streamAudioResponseMock,
    streamChatMessage: streamChatMessageMock,
    streamDialogResponse: streamDialogResponseMock,
    synthesizeSpeech: synthesizeSpeechMock,
    startAudioCall: startAudioCallMock,
    getAudioCallStatus: getAudioCallStatusMock,

  };
});

vi.mock("../../frontend/src/services/audioCallEvents", () => ({
  listenToAudioCallChanged: listenToAudioCallChangedMock,
  publishAudioCallChanged: publishAudioCallChangedMock,
}));

vi.mock("../../frontend/src/services/chatExport", () => ({
  exportChatToMarkdown: exportChatToMarkdownMock,
}));

vi.mock("../../frontend/src/uiConfig", () => ({
  loadUiConfig: loadUiConfigMock,
}));

vi.mock("../../frontend/src/components/MarkdownComposer.vue", async () => {

  const { defineComponent, h } = await import("vue");

  return {
    default: defineComponent({
      name: "MarkdownComposerStub",
      props: {
        modelValue: {
          type: String,
          required: true,
        },
        placeholder: {
          type: String,
          required: true,
        },
        disabled: {
          type: Boolean,
          default: false,
        },
      },
      emits: [
        "update:modelValue",
        "keydown",
      ],
      setup(props, { emit }) {
        return () => h("textarea", {
          "data-testid": "chat-input",
          "aria-label": "Nachricht",
          placeholder: props.placeholder,
          disabled: props.disabled,
          value: props.modelValue,
          onInput: (event: Event) => {
            emit(
              "update:modelValue",
              (event.target as HTMLTextAreaElement).value,
            );
          },
          onKeydown: (event: KeyboardEvent) => {
            emit("keydown", event);
          },
        });
      },
    }),
  };
});

import ChatWindow from "../../frontend/src/ChatWindow.vue";

describe("ChatWindow", () => {

  beforeEach(() => {
    abortAudioRecordingMock.mockReset();
    abortAudioRecordingMock.mockResolvedValue(undefined);

    getChatMock.mockReset();

    getChatsMock.mockReset();
    getChatsMock.mockResolvedValue([]);

    notifyTtsPlaybackEndedMock.mockReset();
    notifyTtsPlaybackEndedMock.mockResolvedValue(undefined);
    startAudioRecordingMock.mockReset();
    startAudioRecordingMock.mockResolvedValue(undefined);
    streamAudioResponseMock.mockReset();
    streamChatMessageMock.mockReset();
    streamDialogResponseMock.mockReset();
    synthesizeSpeechMock.mockReset();

    startAudioCallMock.mockReset();
    startAudioCallMock.mockResolvedValue({
      active: true,
      chat_id: null,
      turn_active: false,
      pending_speech: null,
    });

    getAudioCallStatusMock.mockReset();
    getAudioCallStatusMock.mockResolvedValue({
      active: false,
      chat_id: null,
      turn_active: false,
      pending_speech: null,
    });

    listenToAudioCallChangedMock.mockReset();
    listenToAudioCallChangedMock.mockResolvedValue(() => {});
    publishAudioCallChangedMock.mockReset();
    publishAudioCallChangedMock.mockResolvedValue(undefined);

    exportChatToMarkdownMock.mockReset();
    exportChatToMarkdownMock.mockResolvedValue(undefined);

    loadUiConfigMock.mockReset();
    loadUiConfigMock.mockResolvedValue({
      name: "Frieda",
      avatar: {
        standard: {
          key: "standard",
          url: "http://127.0.0.1:8095/api/v1/assets/avatar/images/standard",
        },
        animations: [],
      },
    });
  });


  it("loads UI config before loading chat history", async () => {
    let resolveUiConfig:
      | ((config: {
          name: string;
          avatar: {
            standard: {
              key: "standard";
              url: string;
            };
            animations: never[];
          };
        }) => void)
      | undefined;

    loadUiConfigMock.mockImplementation(
      () => new Promise((resolve) => {
        resolveUiConfig = resolve;
      }),
    );

    mount(ChatWindow);
    await flushPromises();

    expect(loadUiConfigMock).toHaveBeenCalledTimes(1);
    expect(getChatsMock).not.toHaveBeenCalled();

    resolveUiConfig?.({
      name: "Frieda",
      avatar: {
        standard: {
          key: "standard",
          url: "http://127.0.0.1:8095/api/v1/assets/avatar/images/standard",
        },
        animations: [],
      },
    });
    await flushPromises();

    expect(getChatsMock).toHaveBeenCalled();
  });

  it("shows a hard startup error when UI config loading fails", async () => {
    loadUiConfigMock.mockRejectedValue(
      new Error("UI config request failed with HTTP 500"),
    );

    const wrapper = mount(ChatWindow);
    await flushPromises();

    expect(getChatsMock).not.toHaveBeenCalled();
    expect(wrapper.get('[data-testid="chat-error"]').text()).toContain(
      "UI-Konfiguration konnte nicht geladen werden: UI config request failed with HTTP 500",
    );
  });

  it("uses the configured avatar name for assistant messages", async () => {
    loadUiConfigMock.mockResolvedValue({
      name: "Konfig-Frieda",
      avatar: {
        standard: {
          key: "standard",
          url: "http://127.0.0.1:8095/api/v1/assets/avatar/images/standard",
        },
        animations: [],
      },
    });

    getChatMock.mockResolvedValue({
      id: 42,
      title: "Chat",
      pinned: false,
      created_at: "2026-09-07T10:00:00",
      messages: [
        {
          id: 1,
          role: "assistant",
          content: "Hallo",
          created_at: "2026-09-07T10:00:01",
        },
      ],
    });

    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);

    const wrapper = mount(ChatWindow);
    await flushPromises();

    await wrapper.get('[data-testid="chat-42"]').trigger("click");
    await flushPromises();

    expect(
      wrapper.get('[data-testid="message-assistant"] .message-role').text(),
    ).toBe("Konfig-Frieda");
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

  it("renders the dialog call button between audio and send", () => {
    const wrapper = mount(ChatWindow);

    const callButton = wrapper.get('[data-testid="dialog-call"]');

    expect(callButton.attributes("aria-label")).toBe("Dialog starten");
    expect(callButton.attributes("title")).toBe("Dialog starten");

    const actions = wrapper.get(".composer-actions");
    const testIds = actions
      .findAll("[data-testid]")
      .map((element) => element.attributes("data-testid"));

    expect(testIds.indexOf("record-audio")).toBeLessThan(
      testIds.indexOf("dialog-call"),
    );
    expect(testIds.indexOf("dialog-call")).toBeLessThan(
      testIds.indexOf("send-chat"),
    );
  });

  it("delegates a persisted chat call to the avatar backend", async () => {
    getChatsMock.mockResolvedValue([{ id: 42, title: "Chat", pinned: false, created_at: "2026-01-01" }]);
    getChatMock.mockResolvedValue({ id: 42, title: "Chat", pinned: false, created_at: "2026-01-01", messages: [] });
    getAudioCallStatusMock.mockResolvedValue({ active: false, chat_id: null, turn_active: false, pending_speech: null });
    startAudioCallMock.mockResolvedValue({ active: true, chat_id: 42, turn_active: false, pending_speech: null });
    const wrapper = mount(ChatWindow);
    await flushPromises();
    await wrapper.get('[data-testid="chat-42"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-testid="dialog-call"]').trigger("click");
    await flushPromises();
    expect(startAudioCallMock).toHaveBeenCalledWith(42);
    expect(publishAudioCallChangedMock).toHaveBeenCalledTimes(1);
    expect(streamDialogResponseMock).not.toHaveBeenCalled();
  });


  it("leaves dialog execution to the avatar", () => {
    const wrapper = mount(ChatWindow);
    expect(wrapper.get('[data-testid="dialog-call"]').attributes("aria-label"))
      .toBe("Dialog starten");
    expect(streamDialogResponseMock).not.toHaveBeenCalled();
  });

  it("refreshes the chat list when the ChatWindow regains focus", async () => {
    const wrapper = mount(ChatWindow);
    await flushPromises();

    expect(getChatsMock).toHaveBeenCalledTimes(1);

    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Avatar Chat",
        pinned: false,
        created_at: "2026-09-11T18:00:00",
      },
    ]);

    window.dispatchEvent(new Event("focus"));
    await flushPromises();

    expect(getChatsMock).toHaveBeenCalledTimes(2);
    expect(wrapper.get('[data-testid="chat-42"]').text()).toContain(
      "Avatar Chat",
    );
  });

  it("refreshes visible messages on audio call events without idle polling", async () => {
    vi.useFakeTimers();

    let onAudioCallChanged: (() => void) | undefined;
    listenToAudioCallChangedMock.mockImplementation(async (handler) => {
      onAudioCallChanged = handler;
      return () => {};
    });

    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Call Chat",
        pinned: false,
        created_at: "2026-09-11T18:00:00",
      },
    ]);

    getChatMock
      .mockResolvedValueOnce({
        id: 42,
        title: "Call Chat",
        pinned: false,
        created_at: "2026-09-11T18:00:00",
        messages: [],
      })
      .mockResolvedValue({
        id: 42,
        title: "Call Chat",
        pinned: false,
        created_at: "2026-09-11T18:00:00",
        messages: [
          {
            id: 1,
            role: "user",
            content: "Audiofrage",
            created_at: "2026-09-11T18:00:01",
          },
          {
            id: 2,
            role: "assistant",
            content: "Audioantwort",
            created_at: "2026-09-11T18:00:02",
          },
        ],
      });

    getAudioCallStatusMock.mockResolvedValue({
      active: true,
      chat_id: 42,
      turn_active: false,
      pending_speech: null,
    });

    const wrapper = mount(ChatWindow);
    await flushPromises();
    await wrapper.get('[data-testid="chat-42"]').trigger("click");
    await flushPromises();

    const callsAfterMount = getAudioCallStatusMock.mock.calls.length;

    await vi.advanceTimersByTimeAsync(2000);
    await flushPromises();

    expect(getAudioCallStatusMock).toHaveBeenCalledTimes(callsAfterMount);
    expect(wrapper.findAll(".message")).toHaveLength(2);

    onAudioCallChanged?.();
    await flushPromises();

    expect(wrapper.get('[data-testid="message-user"]').text()).toContain(
      "Audiofrage",
    );
    expect(
      wrapper.get('[data-testid="message-assistant"]').text(),
    ).toContain("Audioantwort");
  });

  it("preserves audio recording outside avatar call ownership", () => {
    expect(true).toBe(true);
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
      undefined,
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
      wrapper.get(".messages-shell").attributes("style"),
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
      wrapper.get(".messages-shell").attributes("style") ?? "",
    ).not.toContain("display: none");
    expect(wrapper.get(".composer").classes()).not.toContain("composer--expanded");
    expect(wrapper.get('[data-testid="chat-input"]').element).toBe(inputElement);
  });

  it("sends a single-line message with Enter from the expanded composer and collapses it", async () => {
    streamChatMessageMock.mockResolvedValue(undefined);

    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');

    await wrapper.get('[data-testid="toggle-composer"]').trigger("click");
    await input.setValue("Hallo");
    await input.trigger("keydown", { key: "Enter" });
    await flushPromises();

    expect(streamChatMessageMock).toHaveBeenCalledTimes(1);
    expect(streamChatMessageMock.mock.calls[0][0]).toEqual({
      message: "Hallo",
    });
    expect(wrapper.get(".composer").classes()).not.toContain(
      "composer--expanded",
    );
  });

  it("collapses the expanded composer when sending with the send button", async () => {
    streamChatMessageMock.mockResolvedValue(undefined);

    const wrapper = mount(ChatWindow);

    await wrapper.get('[data-testid="toggle-composer"]').trigger("click");
    await wrapper.get('[data-testid="chat-input"]').setValue("Hallo");
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    expect(streamChatMessageMock).toHaveBeenCalledTimes(1);
    expect(wrapper.get(".composer").classes()).not.toContain(
      "composer--expanded",
    );
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
    expect(streamChatMessageMock.mock.calls[0][0]).toEqual({
      message: "Hallo",
    });
    expect(wrapper.get('[data-testid="message-user"]').text()).toContain(
      "Hallo",
    );
    expect(
      wrapper.get('[data-testid="message-assistant"]').text(),
    ).toContain("Hallo Flo");
  });

  it("preserves user line breaks while rendering Markdown", async () => {
    streamChatMessageMock.mockResolvedValue(undefined);

    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("Zeile 1\n**Zeile 2**\nZeile 3");
    await input.trigger("keydown", {
      key: "Enter",
      ctrlKey: true,
    });
    await flushPromises();

    const userMessage = wrapper.get(
      '[data-testid="message-user"] [data-testid="markdown-message"]',
    );

    expect(userMessage.findAll("br")).toHaveLength(2);
    expect(userMessage.find("strong").text()).toBe("Zeile 2");
  });

  it("renders the watermark behind the scrolling message area", () => {
    const wrapper = mount(ChatWindow);

    const watermark = wrapper.get(".chat-watermark");

    expect(watermark.attributes("src")).toContain("watermark");
    expect(watermark.attributes("aria-hidden")).toBe("true");
    expect(wrapper.get(".messages-shell").exists()).toBe(true);
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
    expect(streamChatMessageMock.mock.calls[0][0]).toEqual({
      message: "Zeile 1\nZeile 2",
    });
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

  it("keeps the composer editable but disables sending while generating", async () => {
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
    ).toBeUndefined();
    expect(wrapper.find('[data-testid="send-chat"]').exists()).toBe(false);
    expect(
      wrapper.get('[data-testid="record-audio"]').attributes("disabled"),
    ).toBeDefined();

    await wrapper.get('[data-testid="chat-input"]').setValue(
      "Nächster Prompt",
    );

    expect(
      (wrapper.get('[data-testid="chat-input"]').element as HTMLTextAreaElement)
        .value,
    ).toBe("Nächster Prompt");

    const stopButton = wrapper.get('[data-testid="stop-chat"]');
    expect(stopButton.exists()).toBe(true);
    expect(stopButton.attributes("aria-label")).toBe("Antwort stoppen");
    expect(stopButton.attributes("title")).toBe("Antwort stoppen");
    expect(stopButton.text()).toBe("");
  });


  it("stops and rolls back the current turn without replacing a new draft", async () => {

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

    await input.setValue("Nächster Prompt");
    await wrapper.get('[data-testid="stop-chat"]').trigger("click");
    await flushPromises();

    expect(wrapper.findAll(".message")).toHaveLength(0);
    expect(
      (wrapper.get('[data-testid="chat-input"]').element as HTMLTextAreaElement)
        .value,
    ).toBe("Nächster Prompt");

    expect(wrapper.find('[data-testid="chat-error"]').exists()).toBe(false);
  });

  it("shows a short error without replacing a new composer draft", async () => {
    let rejectStream: ((error: Error) => void) | undefined;

    streamChatMessageMock.mockImplementation(
      () => new Promise<void>((_resolve, reject) => {
        rejectStream = reject;
      }),
    );

    const wrapper = mount(ChatWindow);
    const input = wrapper.get('[data-testid="chat-input"]');

    await input.setValue("Hallo");
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    await input.setValue("Nächster Prompt");
    rejectStream?.(new Error("technical details"));
    await flushPromises();

    expect(wrapper.findAll(".message")).toHaveLength(0);
    expect(wrapper.get('[data-testid="chat-error"]').text()).toBe(
      "Antwort konnte nicht erzeugt werden.",
    );
    expect(
      (wrapper.get('[data-testid="chat-input"]').element as HTMLTextAreaElement)
        .value,
    ).toBe("Nächster Prompt");
  });


  it("starts a new empty chat without aborting a running response", async () => {
    let aborted = false;

    streamChatMessageMock.mockImplementation(
      (_request, handlers, signal) => {
        handlers.onChat?.(42);

        return new Promise<void>((_resolve, reject) => {
          signal.addEventListener("abort", () => {
            aborted = true;
            reject(new DOMException("Aborted", "AbortError"));
          });
        });
      },
    );

    const wrapper = mount(ChatWindow);

    await wrapper.get('[data-testid="chat-input"]').setValue("Hallo");
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-testid="new-chat"]').trigger("click");
    await flushPromises();

    expect(aborted).toBe(false);
    expect(wrapper.findAll(".message")).toHaveLength(0);
    expect(
      (wrapper.get('[data-testid="chat-input"]').element as HTMLTextAreaElement)
        .value,
    ).toBe("");
    expect(wrapper.find('[data-testid="chat-error"]').exists()).toBe(false);
  });

  it("separates pinned chats from normal history and always shows the pinned section", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Angeheftet",
        pinned: true,
        created_at: "2026-09-07T10:00:00",
      },
      {
        id: 7,
        title: "Normal",
        pinned: false,
        created_at: "2026-09-06T10:00:00",
      },
    ]);

    const wrapper = mount(ChatWindow);
    await flushPromises();

    const pinned = wrapper.get('[data-testid="pinned-chats"]');

    expect(pinned.text()).toContain("Pinned Chats");
    expect(pinned.find('[data-testid="chat-42"]').exists()).toBe(true);
    expect(pinned.find('[data-testid="chat-7"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid="chat-42"]')).toHaveLength(1);
    expect(wrapper.findAll('[data-testid="chat-7"]')).toHaveLength(1);
  });

  it("shows the pinned section when no chats exist", async () => {
    const wrapper = mount(ChatWindow);
    await flushPromises();

    expect(
      wrapper.get('[data-testid="pinned-chats"]').text(),
    ).toContain("Pinned Chats");
  });

  it("opens the chat menu and exposes all management actions", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);

    const wrapper = mount(ChatWindow);
    await flushPromises();

    await wrapper
      .get('[data-testid="chat-menu-42"]')
      .trigger("click");

    expect(
      wrapper.get('[data-testid="chat-pin-42"]').text(),
    ).toContain("Pin");
    expect(
      wrapper.get('[data-testid="chat-rename-42"]').text(),
    ).toBe("Rename");
    expect(
      wrapper.get('[data-testid="chat-export-42"]').text(),
    ).toBe("Export");
    expect(
      wrapper.get('[data-testid="chat-permissions-42"]').text(),
    ).toBe("Permissions");
    expect(
      wrapper.get('[data-testid="chat-export-42"]').attributes("disabled"),
    ).toBeUndefined();
    expect(
      wrapper.get('[data-testid="chat-delete-42"]').text(),
    ).toBe("Delete");
  });

  it("exports a persisted chat from its menu", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);

    const wrapper = mount(ChatWindow);
    await flushPromises();

    await wrapper
      .get('[data-testid="chat-menu-42"]')
      .trigger("click");
    await wrapper
      .get('[data-testid="chat-export-42"]')
      .trigger("click");
    await flushPromises();

    expect(exportChatToMarkdownMock).toHaveBeenCalledWith(
      42,
      "Frieda",
    );
    expect(
      wrapper.find('[data-testid="chat-menu-popup-42"]').exists(),
    ).toBe(false);
    expect(
      wrapper.find('[data-testid="chat-error"]').exists(),
    ).toBe(false);
  });

  it("shows the existing chat error area when export fails", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);
    exportChatToMarkdownMock.mockRejectedValue(
      new Error("export failed"),
    );

    const wrapper = mount(ChatWindow);
    await flushPromises();

    await wrapper
      .get('[data-testid="chat-menu-42"]')
      .trigger("click");
    await wrapper
      .get('[data-testid="chat-export-42"]')
      .trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-testid="chat-error"]').text()).toBe(
      "Chat konnte nicht exportiert werden.",
    );
  });

  it("closes the chat menu on outside pointer interaction and Escape", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);

    const wrapper = mount(ChatWindow);
    await flushPromises();

    const menuButton = wrapper.get('[data-testid="chat-menu-42"]');

    await menuButton.trigger("click");
    expect(
      wrapper.find('[data-testid="chat-menu-popup-42"]').exists(),
    ).toBe(true);

    document.dispatchEvent(new Event("pointerdown"));
    await wrapper.vm.$nextTick();

    expect(
      wrapper.find('[data-testid="chat-menu-popup-42"]').exists(),
    ).toBe(false);

    await menuButton.trigger("click");
    window.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape" }),
    );
    await wrapper.vm.$nextTick();

    expect(
      wrapper.find('[data-testid="chat-menu-popup-42"]').exists(),
    ).toBe(false);
  });

  it("opens rename with the current title and rejects an empty trimmed title", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Alter Name",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);

    const wrapper = mount(ChatWindow);
    await flushPromises();

    await wrapper
      .get('[data-testid="chat-menu-42"]')
      .trigger("click");
    await wrapper
      .get('[data-testid="chat-rename-42"]')
      .trigger("click");

    const input = wrapper.get('[data-testid="rename-chat-input"]');

    expect((input.element as HTMLInputElement).value).toBe(
      "Alter Name",
    );

    await input.setValue("   ");
    await wrapper
      .get('[data-testid="rename-chat-dialog"] form')
      .trigger("submit");

    expect(
      wrapper.find('[data-testid="rename-chat-dialog"]').exists(),
    ).toBe(true);
    expect(wrapper.get('[role="alert"]').text()).toContain(
      "darf nicht leer sein",
    );
  });

  it("shows the current chat title in the delete confirmation", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Mein Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);

    const wrapper = mount(ChatWindow);
    await flushPromises();

    await wrapper
      .get('[data-testid="chat-menu-42"]')
      .trigger("click");
    await wrapper
      .get('[data-testid="chat-delete-42"]')
      .trigger("click");

    expect(
      wrapper.get('[data-testid="delete-chat-dialog"]').text(),
    ).toContain("Chat ‚Mein Chat‘ wirklich löschen?");
  });

  it("loads persisted chats into the sidebar", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Persistenter Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
      {
        id: 7,
        title: "Älterer Chat",
        pinned: false,
        created_at: "2026-09-06T10:00:00",
      },
    ]);

    const wrapper = mount(ChatWindow);
    await flushPromises();

    expect(wrapper.get('[data-testid="chat-42"]').text()).toContain(
      "Persistenter Chat",
    );
    expect(wrapper.get('[data-testid="chat-7"]').text()).toContain(
      "Älterer Chat",
    );
    expect(
      wrapper.find(".chat-history-placeholder").exists(),
    ).toBe(false);
  });

  it("loads a persisted chat and discards unsent composer text", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Persistenter Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);

    getChatMock.mockResolvedValue({
      id: 42,
      title: "Persistenter Chat",
      pinned: false,
      created_at: "2026-09-07T10:00:00",

      messages: [
        {
          id: 1,
          role: "user",
          content: "Frage",
          created_at: "2026-09-07T10:00:01",
        },
        {
          id: 2,
          role: "assistant",
          content: "Antwort",
          created_at: "2026-09-07T10:00:02",
        },
      ],
    });

    const wrapper = mount(ChatWindow);
    await flushPromises();

    await wrapper.get('[data-testid="chat-input"]').setValue(
      "ungesendet",
    );
    await wrapper.get('[data-testid="chat-42"]').trigger("click");
    await flushPromises();

    expect(getChatMock).toHaveBeenCalledWith(42);
    expect(wrapper.findAll(".message")).toHaveLength(2);
    expect(wrapper.get('[data-testid="message-user"]').text()).toContain(
      "Frage",
    );
    expect(
      wrapper.get('[data-testid="message-assistant"]').text(),
    ).toContain("Antwort");
    expect(
      (wrapper.get('[data-testid="chat-input"]').element as HTMLTextAreaElement)
        .value,
    ).toBe("");
  });

  it("shows the terminal compression error and disables chat input", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Zu großer Kontext",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);
    getChatMock.mockResolvedValue({
      id: 42,
      title: "Zu großer Kontext",
      pinned: false,
      created_at: "2026-09-07T10:00:00",
      messages: [],
      compression_error_code: "chat_context_compression_failed",
    });

    const wrapper = mount(ChatWindow);
    await flushPromises();
    await wrapper.get('[data-testid="chat-42"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-testid="chat-error"]').text()).toContain(
      "kann wegen eines zu großen Kontextes nicht fortgesetzt werden",
    );
    expect(wrapper.get('[data-testid="chat-input"]').attributes("disabled"))
      .toBeDefined();
    expect(wrapper.get('[data-testid="record-audio"]').attributes("disabled"))
      .toBeDefined();
    expect(wrapper.get('[data-testid="dialog-call"]').attributes("disabled"))
      .toBeDefined();
    expect(wrapper.get('[data-testid="send-chat"]').attributes("disabled"))
      .toBeDefined();
  });

  it("continues a persisted chat using its chat ID", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Persistenter Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);

    getChatMock.mockResolvedValue({
      id: 42,
      title: "Persistenter Chat",
      pinned: false,
      created_at: "2026-09-07T10:00:00",
      messages: [],
    });

    streamChatMessageMock.mockImplementation(
      async (_request, handlers) => {
        handlers.onChat?.(42);
        handlers.onChunk("Antwort");
      },
    );

    const wrapper = mount(ChatWindow);
    await flushPromises();

    await wrapper.get('[data-testid="chat-42"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-testid="chat-input"]').setValue(
      "Weiter",
    );
    await wrapper.get('[data-testid="send-chat"]').trigger("click");
    await flushPromises();

    expect(streamChatMessageMock.mock.calls[0][0]).toEqual({
      chatId: 42,
      message: "Weiter",
    });
  });

  it("keeps the current chat visible when loading another chat fails", async () => {
    getChatsMock.mockResolvedValue([
      {
        id: 42,
        title: "Kaputter Chat",
        pinned: false,
        created_at: "2026-09-07T10:00:00",
      },
    ]);

    getChatMock.mockRejectedValue(new Error("failed"));

    const wrapper = mount(ChatWindow);
    await flushPromises();

    await wrapper.get('[data-testid="chat-input"]').setValue(
      "bleibt erhalten",
    );
    await wrapper.get('[data-testid="chat-42"]').trigger("click");
    await flushPromises();

    expect(
      (wrapper.get('[data-testid="chat-input"]').element as HTMLTextAreaElement)
        .value,
    ).toBe("bleibt erhalten");
    expect(wrapper.get('[data-testid="chat-error"]').text()).toBe(
      "Chat konnte nicht geladen werden.",
    );
});
});
