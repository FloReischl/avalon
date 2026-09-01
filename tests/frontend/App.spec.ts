import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getBackendSnapshotMock, listenToBackendLifecycleMock } = vi.hoisted(
  () => ({
    getBackendSnapshotMock: vi.fn(),
    listenToBackendLifecycleMock: vi.fn(),
  }),
);

vi.mock("../../frontend/src/services/backendLifecycle", () => ({
  getBackendSnapshot: getBackendSnapshotMock,
  listenToBackendLifecycle: listenToBackendLifecycleMock,
}));

import App from "../../frontend/src/App.vue";

describe("App", () => {
  beforeEach(() => {
    getBackendSnapshotMock.mockReset();
    listenToBackendLifecycleMock.mockReset();
    listenToBackendLifecycleMock.mockResolvedValue(() => {});
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

  it("toggles between idle and active when Frieda is clicked", async () => {
    getBackendSnapshotMock.mockResolvedValue({
      status: "ready",
      logs: ["Backend ready"],
    });

    const wrapper = mount(App);
    await flushPromises();

    const avatarRegion = wrapper.get('[data-testid="avatar-region"]');

    expect(wrapper.find('[data-testid="active-panel"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="hit-debug"]').text()).toBe("MISS");

    await avatarRegion.trigger("click");

    expect(wrapper.find('[data-testid="active-panel"]').exists()).toBe(false);
  });

  it.todo("sends a text message and renders the complete response");
  it.todo("records and submits a push-to-talk audio clip");
  it.todo("plays synthesized speech for an assistant response");
});
