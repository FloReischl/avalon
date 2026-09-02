import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

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

  it("activates Frieda when clicked and keeps her active on subsequent clicks", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    const avatarRegion = wrapper.get('[data-testid="avatar-region"]');

    expect(wrapper.find('[data-testid="active-panel"]').exists()).toBe(false);

    await avatarRegion.trigger("click");

    expect(wrapper.find('[data-testid="active-panel"]').exists()).toBe(true);
    expect(showChatWindowMock).not.toHaveBeenCalled();
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

    await avatarRegion.trigger("click");

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

  it.todo("sends a text message and renders the complete response");
  it.todo("records and submits a push-to-talk audio clip");
  it.todo("plays synthesized speech for an assistant response");
});
