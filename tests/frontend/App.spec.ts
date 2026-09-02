import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const {
  getBackendSnapshotMock,
  listenToBackendLifecycleMock,
  showChatWindowMock,
  startDraggingMock,
} = vi.hoisted(() => ({
  getBackendSnapshotMock: vi.fn(),
  listenToBackendLifecycleMock: vi.fn(),
  showChatWindowMock: vi.fn(),
  startDraggingMock: vi.fn(),
}));

vi.mock("../../frontend/src/services/backendLifecycle", () => ({
  getBackendSnapshot: getBackendSnapshotMock,
  listenToBackendLifecycle: listenToBackendLifecycleMock,
}));

vi.mock("../../frontend/src/services/chatWindow", () => ({
  showChatWindow: showChatWindowMock,
}));

vi.mock("../../frontend/src/services/windowDrag", () => ({
  startAvatarWindowDrag: startDraggingMock,
}));

import App from "../../frontend/src/App.vue";

describe("App", () => {
  beforeEach(() => {
    getBackendSnapshotMock.mockReset();
    listenToBackendLifecycleMock.mockReset();
    showChatWindowMock.mockReset();
    startDraggingMock.mockReset();
    listenToBackendLifecycleMock.mockResolvedValue(() => {});
    showChatWindowMock.mockResolvedValue(undefined);
    startDraggingMock.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows the startup snapshot while the backend is starting", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "waiting-for-health",
      logs: [
        "Starting backend",
        "Waiting for backend health endpoint",
      ],
    });

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.get('[data-testid="backend-status"]').text()).toBe(
      "waiting-for-health",
    );
    expect(wrapper.get('[data-testid="startup-log"]').text()).toContain(
      "Starting backend",
    );
    expect(wrapper.get('[data-testid="startup-log"]').text()).toContain(
      "Waiting for backend health endpoint",
    );
  });

  it("shows the companion view when the snapshot is already ready", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.get('[data-testid="backend-status"]').text()).toBe(
      "Backend ready",
    );
    expect(wrapper.find('[data-testid="startup-log"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="avatar"]').attributes("alt")).toBe(
      "Frieda",
    );
    expect(wrapper.find('[data-testid="active-panel"]').exists()).toBe(false);
  });

  it("keeps Frieda visible while the backend is starting", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "waiting-for-health",
      logs: ["Waiting for backend health endpoint"],
    });

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.get('[data-testid="avatar"]').attributes("alt")).toBe(
      "Frieda",
    );
    expect(wrapper.get('[data-testid="startup-panel"]').exists()).toBe(true);
  });

  it("opens the chat window when Frieda is double-clicked", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    const avatarRegion = wrapper.get('[data-testid="avatar-region"]');

    await avatarRegion.trigger("pointerdown", {
      button: 0,
      clientX: 100,
      clientY: 100,
    });
    await avatarRegion.trigger("pointerup");
    await avatarRegion.trigger("pointerdown", {
      button: 0,
      clientX: 100,
      clientY: 100,
    });
    await avatarRegion.trigger("pointerup");
    await avatarRegion.trigger("dblclick");

    expect(startDraggingMock).not.toHaveBeenCalled();
    expect(showChatWindowMock).toHaveBeenCalledTimes(1);
  });

  it("keeps double-click working after Frieda has been dragged", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    const avatarRegion = wrapper.get('[data-testid="avatar-region"]');

    avatarRegion.element.dispatchEvent(
      new MouseEvent("pointerdown", {
        bubbles: true,
        button: 0,
        clientX: 100,
        clientY: 100,
      }),
    );
    avatarRegion.element.dispatchEvent(
      new MouseEvent("pointermove", {
        bubbles: true,
        buttons: 1,
        clientX: 120,
        clientY: 100,
      }),
    );
    await flushPromises();

    expect(startDraggingMock).toHaveBeenCalledTimes(1);

    await avatarRegion.trigger("pointerdown", {
      button: 0,
      clientX: 100,
      clientY: 100,
    });
    await avatarRegion.trigger("pointerup");
    await avatarRegion.trigger("pointerdown", {
      button: 0,
      clientX: 100,
      clientY: 100,
    });
    await avatarRegion.trigger("pointerup");
    await avatarRegion.trigger("dblclick");

    expect(showChatWindowMock).toHaveBeenCalledTimes(1);
  });

  it("shows push-to-talk recording state only while the audio button is held", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    const audioButton = wrapper.get('[data-testid="audio-button"]');

    expect(wrapper.find('[data-testid="audio-countdown"]').exists()).toBe(false);

    await audioButton.trigger("pointerdown", { button: 0 });

    expect(audioButton.classes()).toContain("audio-button--recording");
    expect(audioButton.attributes("aria-pressed")).toBe("true");
    expect(wrapper.get('[data-testid="audio-countdown"]').text()).toBe("30");

    await audioButton.trigger("pointerup");

    expect(audioButton.classes()).not.toContain("audio-button--recording");
    expect(audioButton.attributes("aria-pressed")).toBe("false");
    expect(wrapper.find('[data-testid="audio-countdown"]').exists()).toBe(false);
  });

  it("aborts push-to-talk when the 30 second limit is reached", async () => {
    vi.useFakeTimers();

    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    const audioButton = wrapper.get('[data-testid="audio-button"]');
    await audioButton.trigger("pointerdown", { button: 0 });

    vi.advanceTimersByTime(29_000);
    await wrapper.vm.$nextTick();

    expect(wrapper.get('[data-testid="audio-countdown"]').text()).toBe("1");
    expect(audioButton.classes()).toContain("audio-button--recording");

    vi.advanceTimersByTime(1_000);
    await wrapper.vm.$nextTick();

    expect(audioButton.classes()).not.toContain("audio-button--recording");
    expect(wrapper.find('[data-testid="audio-countdown"]').exists()).toBe(false);
  });

  it.todo("sends a text message and renders the complete response");
  it.todo("records and submits a push-to-talk audio clip");
  it.todo("plays synthesized speech for an assistant response");
});
