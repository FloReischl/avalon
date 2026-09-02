import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  streamChatMessageMock,
} = vi.hoisted(() => ({
  streamChatMessageMock: vi.fn(),
}));

vi.mock("../../frontend/src/services/backend", async (importOriginal) => {
  const original = await importOriginal<
    typeof import("../../frontend/src/services/backend")
  >();

  return {
    ...original,
    streamChatMessage: streamChatMessageMock,
  };
});

import ChatWindow from "../../frontend/src/ChatWindow.vue";

describe("ChatWindow", () => {
  beforeEach(() => {
    streamChatMessageMock.mockReset();
  });

  it("renders the chat sidebar with its default width", () => {
    const wrapper = mount(ChatWindow);

    expect(
      wrapper.get('[data-testid="chat-sidebar"]').attributes("style"),
    ).toContain("width: 280px");
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
    expect(streamChatMessageMock.mock.calls[0][0]).toBe("Hallo");
    expect(wrapper.get('[data-testid="message-user"]').text()).toContain(
      "Hallo",
    );
    expect(
      wrapper.get('[data-testid="message-assistant"]').text(),
    ).toContain("Hallo Flo");
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
    expect(streamChatMessageMock.mock.calls[0][0]).toBe(
      "Zeile 1\nZeile 2",
    );
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
    expect(wrapper.get('[data-testid="stop-chat"]').exists()).toBe(true);
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
