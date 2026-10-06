import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const {
  getChatPermissionsMock,
  getPendingAuthorizationRequestsMock,
  getProactivePermissionsChatMock,
  loadAgentBearerTokenMock,
  setAgentBearerTokenMock,
  loadUiConfigMock,
  saveChatPermissionMock,
  callbacks,
  eventCallbackIds,
} = vi.hoisted(() => ({
  getChatPermissionsMock: vi.fn(),
  getPendingAuthorizationRequestsMock: vi.fn(),
  getProactivePermissionsChatMock: vi.fn(),
  loadAgentBearerTokenMock: vi.fn(),
  setAgentBearerTokenMock: vi.fn(),
  loadUiConfigMock: vi.fn(),
  saveChatPermissionMock: vi.fn(),
  callbacks: new Map<number, (event: { payload: unknown }) => void>(),
  eventCallbackIds: new Map<string, number>(),
}));

vi.mock("../../frontend/src/services/backend", () => ({
  BACKEND_BASE_URL: "http://test",
  abortAuthorization: vi.fn(),
  confirmAuthorization: vi.fn(),
  getChatPermissions: getChatPermissionsMock,
  getPendingAuthorizationRequests: getPendingAuthorizationRequestsMock,
  loadAgentBearerToken: loadAgentBearerTokenMock,
  saveChatPermission: saveChatPermissionMock,
  setAgentBearerToken: setAgentBearerTokenMock,
}));

vi.mock("../../frontend/src/services/permissionsWindow", () => ({
  getProactivePermissionsChat: getProactivePermissionsChatMock,
}));

vi.mock("../../frontend/src/uiConfig", () => ({
  loadUiConfig: loadUiConfigMock,
}));

import PermissionsWindow from "../../frontend/src/PermissionsWindow.vue";

beforeEach(() => {
  let nextCallbackId = 0;
  callbacks.clear();
  eventCallbackIds.clear();
  Object.defineProperty(window, "__TAURI_INTERNALS__", {
    configurable: true,
    value: {
      transformCallback(callback: (event: { payload: unknown }) => void) {
        const callbackId = ++nextCallbackId;
        callbacks.set(callbackId, callback);
        return callbackId;
      },
      invoke(command: string, arguments_: { event?: string; handler?: number }) {
        if (command === "plugin:event|listen" && arguments_.event && arguments_.handler) {
          eventCallbackIds.set(arguments_.event, arguments_.handler);
          return Promise.resolve(1);
        }
        return Promise.resolve();
      },
    },
  });
  Object.defineProperty(window, "__TAURI_EVENT_PLUGIN_INTERNALS__", {
    configurable: true,
    value: { unregisterListener: vi.fn() },
  });
});

afterEach(() => {
  getChatPermissionsMock.mockReset();
  getPendingAuthorizationRequestsMock.mockReset();
  getProactivePermissionsChatMock.mockReset();
  loadAgentBearerTokenMock.mockReset();
  setAgentBearerTokenMock.mockReset();
  loadUiConfigMock.mockReset();
  saveChatPermissionMock.mockReset();
});

describe("PermissionsWindow", () => {
  it("switches to proactive mode for the chat selected by the desktop command", async () => {
    getPendingAuthorizationRequestsMock.mockResolvedValue([]);
    getProactivePermissionsChatMock.mockResolvedValue({ chatId: 42, agentId: 7 });
    loadAgentBearerTokenMock.mockResolvedValue("token-7");
    getChatPermissionsMock.mockResolvedValue([]);

    const wrapper = mount(PermissionsWindow);
    await flushPromises();

    expect(getChatPermissionsMock).toHaveBeenCalledWith(42);
    expect(loadAgentBearerTokenMock).toHaveBeenCalledWith(7);
    expect(setAgentBearerTokenMock).toHaveBeenCalledWith("token-7");
    expect(loadUiConfigMock).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("Permissions des Chats");
    expect(wrapper.text()).not.toContain("Keine offenen Permissions.");
  });

  it("switches to proactive mode when the open event arrives after mount", async () => {
    getPendingAuthorizationRequestsMock.mockResolvedValue([]);
    loadUiConfigMock.mockResolvedValue({});
    getProactivePermissionsChatMock.mockResolvedValue(null);
    loadAgentBearerTokenMock.mockResolvedValue("token-7");
    getChatPermissionsMock.mockResolvedValue([]);

    const wrapper = mount(PermissionsWindow);
    await flushPromises();
    const callbackId = eventCallbackIds.get("proactive-permissions-for-chat");
    callbacks.get(callbackId ?? -1)?.({ payload: { chatId: 42, agentId: 7 } });
    await flushPromises();

    expect(getChatPermissionsMock).toHaveBeenCalledWith(42);
    expect(wrapper.text()).toContain("Permissions des Chats");
  });

  it("revokes permission when unchecked and saved", async () => {
    getPendingAuthorizationRequestsMock.mockResolvedValue([]);
    getProactivePermissionsChatMock.mockResolvedValue({ chatId: 42, agentId: 7 });
    loadAgentBearerTokenMock.mockResolvedValue("token-7");
    getChatPermissionsMock.mockResolvedValue([
      {
        id: 1,
        context: "web",
        key: "search",
        validityType: "duration",
        defaultExpiry: 3600,
        grant: { id: 10, expiresAt: new Date(Date.now() + 3600_000).toISOString() },
        readOnly: false,
      },
    ]);
    saveChatPermissionMock.mockResolvedValue({
      id: 1,
      context: "web",
      key: "search",
      validityType: "duration",
      defaultExpiry: 3600,
      grant: null,
      readOnly: false,
    });

    const wrapper = mount(PermissionsWindow);
    await flushPromises();

    const checkbox = wrapper.find('input[type="checkbox"]');
    await checkbox.setValue(false);

    const saveButton = wrapper.findAll("button").find((b) => b.text() === "Speichern")!;
    await saveButton.trigger("click");
    await flushPromises();

    expect(saveChatPermissionMock).toHaveBeenCalledWith(42, 1, false, undefined);
  });

  it("initializes the default UI agent only in reactive mode", async () => {
    getPendingAuthorizationRequestsMock.mockResolvedValue([]);
    getProactivePermissionsChatMock.mockResolvedValue(null);
    loadUiConfigMock.mockResolvedValue({});

    mount(PermissionsWindow);
    await flushPromises();

    expect(loadUiConfigMock).toHaveBeenCalledOnce();
    expect(getPendingAuthorizationRequestsMock).toHaveBeenCalledOnce();
  });

  it("shows a load error instead of the proactive empty state", async () => {
    getProactivePermissionsChatMock.mockResolvedValue({ chatId: 42, agentId: 7 });
    loadAgentBearerTokenMock.mockResolvedValue("token-7");
    getChatPermissionsMock.mockRejectedValue(new Error("backend unavailable"));
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const wrapper = mount(PermissionsWindow);
    await flushPromises();

    expect(wrapper.text()).toContain("Permissions konnten nicht geladen werden.");
    expect(wrapper.text()).not.toContain("Keine proaktiv verwaltbaren Permissions.");
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it("shows a load error when the proactive agent token cannot be loaded", async () => {
    getProactivePermissionsChatMock.mockResolvedValue({ chatId: 42, agentId: 7 });
    loadAgentBearerTokenMock.mockRejectedValue(new Error("token unavailable"));
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const wrapper = mount(PermissionsWindow);
    await flushPromises();

    expect(wrapper.text()).toContain("Permissions konnten nicht geladen werden.");
    expect(getChatPermissionsMock).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it("shows the proactive empty state after a successful empty load", async () => {
    getProactivePermissionsChatMock.mockResolvedValue({ chatId: 42, agentId: 7 });
    loadAgentBearerTokenMock.mockResolvedValue("token-7");
    getChatPermissionsMock.mockResolvedValue([]);

    const wrapper = mount(PermissionsWindow);
    await flushPromises();

    expect(wrapper.text()).toContain("Keine proaktiv verwaltbaren Permissions.");
    expect(wrapper.text()).not.toContain("Permissions konnten nicht geladen werden.");
  });

  it("shows a load error instead of the reactive empty state", async () => {
    getProactivePermissionsChatMock.mockResolvedValue(null);
    loadUiConfigMock.mockResolvedValue({});
    getPendingAuthorizationRequestsMock.mockRejectedValue(new Error("backend unavailable"));
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const wrapper = mount(PermissionsWindow);
    await flushPromises();

    expect(wrapper.text()).toContain("Permissions konnten nicht geladen werden.");
    expect(wrapper.text()).not.toContain("Keine offenen Permissions.");
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it("retries reactive loading after the UI configuration fails", async () => {
    vi.useFakeTimers();
    getProactivePermissionsChatMock.mockResolvedValue(null);
    loadUiConfigMock.mockRejectedValueOnce(new Error("backend unavailable"));
    getPendingAuthorizationRequestsMock.mockResolvedValue([]);
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const wrapper = mount(PermissionsWindow);
    await flushPromises();
    expect(wrapper.text()).toContain("Permissions konnten nicht geladen werden.");

    loadUiConfigMock.mockResolvedValue({});
    await vi.advanceTimersByTimeAsync(500);
    await flushPromises();

    expect(loadUiConfigMock).toHaveBeenCalledTimes(2);
    expect(getPendingAuthorizationRequestsMock).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("Keine offenen Permissions.");
    expect(wrapper.text()).not.toContain("Permissions konnten nicht geladen werden.");
    wrapper.unmount();
    errorSpy.mockRestore();
    vi.useRealTimers();
  });

  it("clears a reactive load error after a successful refresh", async () => {
    getProactivePermissionsChatMock.mockResolvedValue(null);
    loadUiConfigMock.mockResolvedValue({});
    getPendingAuthorizationRequestsMock.mockRejectedValueOnce(new Error("backend unavailable"));
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const wrapper = mount(PermissionsWindow);
    await flushPromises();
    expect(wrapper.text()).toContain("Permissions konnten nicht geladen werden.");

    getPendingAuthorizationRequestsMock.mockResolvedValue([{ id: "request-1", sourceLabel: "Agent", context: "web", key: "search", items: [], defaultExpiry: 3600, validityType: "duration" }]);
    const callbackId = eventCallbackIds.get("reactive-permissions");
    callbacks.get(callbackId ?? -1)?.({ payload: undefined });
    await flushPromises();

    expect(wrapper.text()).not.toContain("Permissions konnten nicht geladen werden.");
    expect(wrapper.text()).toContain("Agent");
    errorSpy.mockRestore();
  });
});
