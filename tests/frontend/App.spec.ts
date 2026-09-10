import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const {
  exitAvaloMock,
  getBackendSnapshotMock,
  listenToBackendLifecycleMock,
  showChatWindowMock,
  startDraggingMock,
  resizeAvatarWindowMock,
  setWindowInputRegionsMock,
  loadUiConfigMock,
  setAvatarWindowTitleMock,
  listenToAvatarRuntimeStateMock,
} = vi.hoisted(() => ({



  exitAvaloMock: vi.fn(),
  getBackendSnapshotMock: vi.fn(),
  listenToBackendLifecycleMock: vi.fn(),
  showChatWindowMock: vi.fn(),
  startDraggingMock: vi.fn(),
  resizeAvatarWindowMock: vi.fn(),
  setWindowInputRegionsMock: vi.fn(),
  loadUiConfigMock: vi.fn(),
  setAvatarWindowTitleMock: vi.fn(),
  listenToAvatarRuntimeStateMock: vi.fn(),
}));

vi.mock("../../frontend/src/services/windowTitle", () => ({
  setAvatarWindowTitle: setAvatarWindowTitleMock,
}));

vi.mock("../../frontend/src/services/avatarState", () => ({
  listenToAvatarRuntimeState: listenToAvatarRuntimeStateMock,
}));

vi.mock("../../frontend/src/services/backendLifecycle", () => ({


  getBackendSnapshot: getBackendSnapshotMock,
  listenToBackendLifecycle: listenToBackendLifecycleMock,
}));

vi.mock("../../frontend/src/services/chatWindow", () => ({
  showChatWindow: showChatWindowMock,
}));

vi.mock("../../frontend/src/services/appLifecycle", () => ({
  exitAvalo: exitAvaloMock,
}));

vi.mock("../../frontend/src/services/windowDrag", () => ({
  startAvatarWindowDrag: startDraggingMock,
}));

vi.mock("../../frontend/src/services/inputShape", () => ({
  resizeAvatarWindow: resizeAvatarWindowMock,
  setWindowInputRegions: setWindowInputRegionsMock,
}));

vi.mock("../../frontend/src/uiConfig", () => ({
  loadUiConfig: loadUiConfigMock,
}));

import App from "../../frontend/src/App.vue";


describe("App", () => {
  beforeEach(() => {
    exitAvaloMock.mockReset();
    getBackendSnapshotMock.mockReset();
    listenToBackendLifecycleMock.mockReset();
    showChatWindowMock.mockReset();
    startDraggingMock.mockReset();
    resizeAvatarWindowMock.mockReset();
    setWindowInputRegionsMock.mockReset();
    loadUiConfigMock.mockReset();
    setAvatarWindowTitleMock.mockReset();
    listenToAvatarRuntimeStateMock.mockReset();
    exitAvaloMock.mockResolvedValue(undefined);
    setAvatarWindowTitleMock.mockResolvedValue(undefined);
    listenToAvatarRuntimeStateMock.mockResolvedValue(() => {});

    listenToBackendLifecycleMock.mockResolvedValue(() => {});

    showChatWindowMock.mockResolvedValue(undefined);
    startDraggingMock.mockResolvedValue(undefined);
    resizeAvatarWindowMock.mockResolvedValue(undefined);
    setWindowInputRegionsMock.mockResolvedValue(undefined);
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

  it("waits for backend readiness before loading UI config", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "waiting-for-health",
      logs: ["Waiting for backend health endpoint"],
    });

    const wrapper = mount(App);
    await flushPromises();

    expect(loadUiConfigMock).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid="avatar"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="startup-panel"]').exists()).toBe(true);
  });


  it("loads UI config when the backend is ready", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    expect(loadUiConfigMock).toHaveBeenCalledTimes(1);
    expect(wrapper.get('[data-testid="avatar"]').attributes("src")).toBe(
      "http://127.0.0.1:8095/api/v1/assets/avatar/images/standard",
    );
    expect(wrapper.get('[data-testid="avatar"]').attributes("alt")).toBe(
      "Frieda",
    );
    expect(setAvatarWindowTitleMock).toHaveBeenCalledWith("Frieda");

  });

  it("renders the received runtime state and independent pending balloon", async () => {
    vi.useFakeTimers();
    let onRuntimeState:
      | ((state: { state: string; backendPending: boolean }) => void)
      | undefined;
    listenToAvatarRuntimeStateMock.mockImplementation(
      async (handler) => {
        onRuntimeState = handler;
        return () => {};
      },
    );
    loadUiConfigMock.mockResolvedValue({
      name: "Frieda",
      avatar: {
        standard: { key: "standard", url: "standard.png" },
        animations: [
          {
            key: "listening",
            category: "state",
            spriteSetUrl: "listening.png",
            sprites: [
              { x: 10, y: 0, width: 200, height: 500 },
              { x: 220, y: 0, width: 200, height: 500 },
            ],
          },
        ],
      },
    });
    getBackendSnapshotMock.mockResolvedValue({ status: "ready", logs: [] });

    const wrapper = mount(App);
    await flushPromises();

    onRuntimeState?.({ state: "listening", backendPending: true });
    await flushPromises();

    expect(wrapper.get('[data-testid="avatar-pending-balloon"]').text())
      .toContain("Denke nach");
    expect(wrapper.get('[data-testid="avatar"]').attributes("data-avatar-state"))
      .toBe("listening");
    expect(wrapper.get('[data-testid="avatar"]').attributes("src"))
      .toBe("listening.png");
    expect(wrapper.get('[data-testid="avatar"]').attributes("data-avatar-frame"))
      .toBe("0");
    expect(wrapper.get('[data-testid="avatar"]').element.style.width)
      .toBe("auto");

    await vi.advanceTimersByTimeAsync(1000);
    expect(wrapper.get('[data-testid="avatar"]').attributes("data-avatar-frame"))
      .toBe("1");
  });

  it("shows a hard startup failure when UI config loading fails", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });
    loadUiConfigMock.mockRejectedValue(
      new Error("UI config request failed with HTTP 500"),
    );

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.get('[data-testid="backend-status"]').text()).toBe(
      "failed",
    );
    expect(wrapper.get('[data-testid="startup-log"]').text()).toContain(
      "Failed to load UI config: UI config request failed with HTTP 500",
    );
    expect(wrapper.find('[data-testid="avatar"]').exists()).toBe(false);
  });

  it("opens the chat window when Avatar is double-clicked", async () => {
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

  it("keeps double-click working after Avatar has been dragged", async () => {
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

  it("waits for the WebView resize event before rebuilding the Avatar input shape", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const getContextSpy = vi
      .spyOn(HTMLCanvasElement.prototype, "getContext")
      .mockReturnValue({
        drawImage: vi.fn(),
        getImageData: vi.fn(() => ({
          data: new Uint8ClampedArray(16).fill(255),
        })),
      } as unknown as CanvasRenderingContext2D);

    const wrapper = mount(App);

    try {
      await flushPromises();

      wrapper.get('[data-testid="avatar-stage"]').element.getBoundingClientRect =
        vi.fn(() => ({
          x: 0,
          y: 0,
          top: 0,
          right: 10,
          bottom: 20,
          left: 0,
          width: 10,
          height: 20,
          toJSON: () => ({}),
        }));

      const avatar = wrapper.get('[data-testid="avatar"]');
      avatar.element.getBoundingClientRect = vi.fn(() => ({
        x: 10,
        y: 20,
        top: 20,
        right: 12,
        bottom: 22,
        left: 10,
        width: 2,
        height: 2,
        toJSON: () => ({}),
      }));

      await avatar.trigger("load");
      await flushPromises();

      expect(resizeAvatarWindowMock).toHaveBeenCalledTimes(1);
      expect(setWindowInputRegionsMock).not.toHaveBeenCalled();

      window.dispatchEvent(new Event("resize"));
      await flushPromises();

      expect(setWindowInputRegionsMock).toHaveBeenCalledTimes(1);

      const latestRectangles =
        setWindowInputRegionsMock.mock.calls.at(-1)?.[0];

      expect(latestRectangles?.[0]).toMatchObject({
        x: 10,
        y: 20,
        width: 2,
        height: 2,
      });
    } finally {
      wrapper.unmount();
      getContextSpy.mockRestore();
    }
  });

  it("resizes the Avatar in ten percent steps with Ctrl+ and Ctrl-", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    await wrapper.get('[data-testid="avatar"]').trigger("load");
    await flushPromises();

    const stage = wrapper.get('[data-testid="avatar-stage"]');
    stage.element.getBoundingClientRect = vi.fn(() => ({
      x: 0,
      y: 0,
      top: 0,
      right: 480,
      bottom: 600,
      left: 0,
      width: 480,
      height: 600,
      toJSON: () => ({}),
    }));

    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "+",
        ctrlKey: true,
        bubbles: true,
      }),
    );
    await flushPromises();

    expect(
      wrapper.get('[data-testid="avatar-region"]').attributes("style"),
    ).toContain("26.4rem");
    expect(resizeAvatarWindowMock).toHaveBeenLastCalledWith(576, 696);

    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "-",
        ctrlKey: true,
        bubbles: true,
      }),
    );
    await flushPromises();

    expect(
      wrapper.get('[data-testid="avatar-region"]').attributes("style"),
    ).toContain("24rem");
    expect(resizeAvatarWindowMock).toHaveBeenLastCalledWith(576, 696);
  });

  it("limits Avatar keyboard resizing to fifty through one hundred fifty percent", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    for (let index = 0; index < 10; index += 1) {
      window.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: "-",
          ctrlKey: true,
          bubbles: true,
        }),
      );
      await wrapper.vm.$nextTick();
    }

    expect(
      wrapper.get('[data-testid="avatar-region"]').attributes("style"),
    ).toContain("12rem");

    for (let index = 0; index < 20; index += 1) {
      window.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: "+",
          ctrlKey: true,
          bubbles: true,
        }),
      );
      await wrapper.vm.$nextTick();
    }

    expect(
      wrapper.get('[data-testid="avatar-region"]').attributes("style"),
    ).toContain("36rem");
  });

  it("exits Avalo from the exit button", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    const exitButton = wrapper.get('[data-testid="exit-button"]');

    expect(exitButton.attributes("aria-label")).toBe("Exit");
    expect(exitButton.attributes("title")).toBe("Exit");

    await exitButton.trigger("click");

    expect(exitAvaloMock).toHaveBeenCalledTimes(1);
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
