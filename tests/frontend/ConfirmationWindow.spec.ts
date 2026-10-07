import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const {
  abortAuthorizationMock, confirmAuthorizationMock, getChatPermissionsMock,
  getPendingAuthorizationRequestsMock, getProactiveConfirmationChatMock,
  hideConfirmationWindowMock, loadAgentBearerTokenMock, setAgentBearerTokenMock, loadUiConfigMock,
  saveChatPermissionMock, getPendingWorkflowConfirmationMock, confirmWorkflowConfirmationMock,
  cancelWorkflowConfirmationMock, callbacks, eventCallbackIds,
} = vi.hoisted(() => ({
  abortAuthorizationMock: vi.fn(), confirmAuthorizationMock: vi.fn(),
  getChatPermissionsMock: vi.fn(), getPendingAuthorizationRequestsMock: vi.fn(),
  getProactiveConfirmationChatMock: vi.fn(), loadAgentBearerTokenMock: vi.fn(),
  hideConfirmationWindowMock: vi.fn(), setAgentBearerTokenMock: vi.fn(), loadUiConfigMock: vi.fn(), saveChatPermissionMock: vi.fn(),
  getPendingWorkflowConfirmationMock: vi.fn(), confirmWorkflowConfirmationMock: vi.fn(), cancelWorkflowConfirmationMock: vi.fn(),
  callbacks: new Map<number, (event: { payload: unknown }) => void>(),
  eventCallbackIds: new Map<string, number>(),
}));

vi.mock("../../frontend/src/services/backend", () => ({
  BACKEND_BASE_URL: "http://test", abortAuthorization: abortAuthorizationMock,
  confirmAuthorization: confirmAuthorizationMock, getChatPermissions: getChatPermissionsMock,
  getPendingAuthorizationRequests: getPendingAuthorizationRequestsMock,
  getPendingWorkflowConfirmation: getPendingWorkflowConfirmationMock,
  confirmWorkflowConfirmation: confirmWorkflowConfirmationMock,
  cancelWorkflowConfirmation: cancelWorkflowConfirmationMock,
  loadAgentBearerToken: loadAgentBearerTokenMock, saveChatPermission: saveChatPermissionMock,
  setAgentBearerToken: setAgentBearerTokenMock,
}));
vi.mock("../../frontend/src/services/confirmationWindow", () => ({
  getProactiveConfirmationChat: getProactiveConfirmationChatMock,
  hideConfirmationWindow: hideConfirmationWindowMock,
}));
vi.mock("../../frontend/src/uiConfig", () => ({ loadUiConfig: loadUiConfigMock }));
vi.mock("../../frontend/src/components/ConfirmationGrid.vue", () => ({
  default: {
    props: ["model", "selectedRowIds"],
    emits: ["update:selectedRowIds"],
    template: `<section data-testid="confirmation-grid"><div v-for="row in model.rows" :key="row.id" :data-testid="'grid-row-' + row.id">{{ Object.values(row.cells).join('|') }}</div><button type="button" data-testid="select-all" @click="$emit('update:selectedRowIds', model.rows.map((row) => row.id))">select</button></section>`,
  },
}));

import ConfirmationWindow from "../../frontend/src/ConfirmationWindow.vue";

function reactiveRequest(id = "request-1") {
  return { id, sourceLabel: "Agent", context: "web", key: "search", items: ["query"], defaultExpiry: 3600, validityType: "duration" as const };
}
function proactivePermission(overrides: Record<string, unknown> = {}) {
  return { id: 1, context: "web", key: "search", validityType: "duration" as const, defaultExpiry: 3600, grant: null, readOnly: false, ...overrides };
}

beforeEach(() => {
  let nextCallbackId = 0;
  callbacks.clear(); eventCallbackIds.clear();
  Object.defineProperty(window, "__TAURI_INTERNALS__", { configurable: true, value: {
    transformCallback(callback: (event: { payload: unknown }) => void) { const id = ++nextCallbackId; callbacks.set(id, callback); return id; },
    invoke(command: string, arguments_: { event?: string; handler?: number }) {
      if (command === "plugin:event|listen" && arguments_.event && arguments_.handler) eventCallbackIds.set(arguments_.event, arguments_.handler);
      return Promise.resolve(1);
    },
  } });
  Object.defineProperty(window, "__TAURI_EVENT_PLUGIN_INTERNALS__", { configurable: true, value: { unregisterListener: vi.fn() } });
  getPendingWorkflowConfirmationMock.mockResolvedValue(null);
  confirmWorkflowConfirmationMock.mockResolvedValue(undefined);
  cancelWorkflowConfirmationMock.mockResolvedValue(undefined);
});
afterEach(() => vi.restoreAllMocks());

describe("ConfirmationWindow", () => {
  it("shows the Permissions tab and reactive requests as grid rows", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue(null); loadUiConfigMock.mockResolvedValue({});
    getPendingAuthorizationRequestsMock.mockResolvedValue([reactiveRequest()]);
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    expect(wrapper.text()).toContain("Permissions");
    expect(wrapper.get('[data-testid="grid-row-request-1"]').text()).toContain("web|search||");
    expect(wrapper.text()).toContain("Approve"); expect(wrapper.text()).toContain("Abort");
  });

  it("uses the selected reactive rows and the shared expiry to approve complete requests", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue(null); loadUiConfigMock.mockResolvedValue({});
    getPendingAuthorizationRequestsMock.mockResolvedValue([reactiveRequest()]);
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    await wrapper.get('[data-testid="select-all"]').trigger("click");
    await wrapper.get('[data-testid="approve-reactive"]').trigger("click"); await flushPromises();
    expect(confirmAuthorizationMock).toHaveBeenCalledWith("request-1", [0], expect.any(Number));
  });

  it("opens proactive confirmations and renders Approved separately from selection", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue({ chatId: 42, agentId: 7 });
    loadAgentBearerTokenMock.mockResolvedValue("token-7");
    getChatPermissionsMock.mockResolvedValue([proactivePermission({ grant: { id: 10, expiresAt: "2026-10-07T18:20:00Z" } })]);
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    expect(loadUiConfigMock).not.toHaveBeenCalled();
    expect(wrapper.get('[data-testid="grid-row-1"]').text()).toContain("web|search|✓|");
  });

  it("approves selected duration and permanent proactive permissions in one batch", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue({ chatId: 42, agentId: 7 }); loadAgentBearerTokenMock.mockResolvedValue("token-7");
    getChatPermissionsMock.mockResolvedValue([proactivePermission(), proactivePermission({ id: 2, key: "copy", validityType: "permanent" })]);
    saveChatPermissionMock.mockResolvedValue({});
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    await wrapper.get('[data-testid="select-all"]').trigger("click");
    await wrapper.get('[data-testid="approve-proactive"]').trigger("click"); await flushPromises();
    expect(saveChatPermissionMock).toHaveBeenCalledWith(42, 1, true, expect.any(String));
    expect(saveChatPermissionMock).toHaveBeenCalledWith(42, 2, true, undefined);
  });

  it("keeps proactive range permissions read-only", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue({ chatId: 42, agentId: 7 }); loadAgentBearerTokenMock.mockResolvedValue("token-7");
    getChatPermissionsMock.mockResolvedValue([proactivePermission({ validityType: "range", readOnly: true })]);
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    await wrapper.get('[data-testid="select-all"]').trigger("click");
    await wrapper.get('[data-testid="approve-proactive"]').trigger("click"); await flushPromises();
    expect(saveChatPermissionMock).not.toHaveBeenCalled();
  });

  it("revokes an unapproved proactive permission without a UI error", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue({ chatId: 42, agentId: 7 }); loadAgentBearerTokenMock.mockResolvedValue("token-7");
    getChatPermissionsMock.mockResolvedValue([proactivePermission()]); saveChatPermissionMock.mockResolvedValue({});
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    await wrapper.get('[data-testid="select-all"]').trigger("click");
    await wrapper.get('[data-testid="revoke-proactive"]').trigger("click"); await flushPromises();
    expect(saveChatPermissionMock).toHaveBeenCalledWith(42, 1, false, undefined);
    expect(wrapper.text()).not.toContain("Permissions konnten nicht geändert werden.");
  });

  it("reloads the authoritative proactive state after an update error", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue({ chatId: 42, agentId: 7 }); loadAgentBearerTokenMock.mockResolvedValue("token-7");
    getChatPermissionsMock.mockResolvedValue([proactivePermission()]); saveChatPermissionMock.mockRejectedValue(new Error("offline"));
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    await wrapper.get('[data-testid="select-all"]').trigger("click"); await wrapper.get('[data-testid="approve-proactive"]').trigger("click"); await flushPromises();
    expect(getChatPermissionsMock).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain("Permissions konnten nicht geändert werden.");
    errorSpy.mockRestore();
  });

  it("keeps reactive reload recovery after UI configuration failure", async () => {
    vi.useFakeTimers(); getProactiveConfirmationChatMock.mockResolvedValue(null);
    loadUiConfigMock.mockRejectedValueOnce(new Error("offline")); getPendingAuthorizationRequestsMock.mockResolvedValue([]);
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    expect(wrapper.text()).toContain("Permissions konnten nicht geladen werden.");
    loadUiConfigMock.mockResolvedValue({}); await vi.advanceTimersByTimeAsync(500); await flushPromises();
    expect(wrapper.text()).toContain("Keine offenen Permissions.");
    wrapper.unmount(); vi.useRealTimers();
  });

  it("retries proactive loading while the backend is still starting", async () => {
    vi.useFakeTimers();
    getProactiveConfirmationChatMock.mockResolvedValue({ chatId: 42, agentId: 7 });
    loadAgentBearerTokenMock.mockRejectedValueOnce(new Error("backend unavailable"));
    getChatPermissionsMock.mockResolvedValue([proactivePermission()]);
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const wrapper = mount(ConfirmationWindow); await flushPromises();
    expect(wrapper.text()).toContain("Permissions konnten nicht geladen werden.");

    loadAgentBearerTokenMock.mockResolvedValue("token-7");
    await vi.advanceTimersByTimeAsync(500); await flushPromises();

    expect(getChatPermissionsMock).toHaveBeenCalledWith(42);
    expect(wrapper.get('[data-testid="grid-row-1"]').text()).toContain("web|search");
    expect(wrapper.text()).not.toContain("Permissions konnten nicht geladen werden.");
    wrapper.unmount(); errorSpy.mockRestore(); vi.useRealTimers();
  });

  it("leaves permissions unchanged when Close is used", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue(null); loadUiConfigMock.mockResolvedValue({});
    getPendingAuthorizationRequestsMock.mockResolvedValue([reactiveRequest()]);
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    await wrapper.get('[data-testid="close-confirmation"]').trigger("click");
    expect(hideConfirmationWindowMock).toHaveBeenCalledOnce();
    expect(confirmAuthorizationMock).not.toHaveBeenCalled();
    expect(abortAuthorizationMock).not.toHaveBeenCalled();
  });

  it("offers the Confirmations tab and renders the schema in its declared order", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue(null); loadUiConfigMock.mockResolvedValue({});
    getPendingAuthorizationRequestsMock.mockResolvedValue([]);
    getPendingWorkflowConfirmationMock.mockResolvedValue({
      id: "confirmation-1", executionId: 4,
      schema: { title: "Review topics", columns: [
        { key: "internal", type: "str", nullable: false, editable: false, visible: false },
        { key: "title", label: "Title", type: "str", nullable: false, editable: true, visible: true },
      ] }, rows: [{ internal: "4711", title: "Foo", avalon_confirmation: "unconfirmed" }],
    });
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    expect(wrapper.text()).toContain("Confirmations");
    expect(wrapper.text()).toContain("Review topics");
    const grid = wrapper.getComponent({ name: "ConfirmationGrid" });
    expect(grid.props("model").columns.map((column: { id: string }) => column.id)).toEqual(["internal", "title", "avalon_confirmation"]);
    expect(grid.props("model").columns[0].visible).toBe(false);
    expect(grid.props("model").columns[1].label).toBe("Title");
  });

  it("submits all rows only after every row is decided and valid", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue(null); loadUiConfigMock.mockResolvedValue({}); getPendingAuthorizationRequestsMock.mockResolvedValue([]);
    const confirmation = { id: "confirmation-1", executionId: 4, schema: { title: "Review", columns: [{ key: "title", type: "str", nullable: false, editable: true, visible: true }] }, rows: [{ title: "Foo", avalon_confirmation: "unconfirmed" }] };
    getPendingWorkflowConfirmationMock.mockResolvedValue(confirmation);
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    expect(wrapper.get('[data-testid="confirm-workflow"]').attributes("disabled")).toBeDefined();
    await wrapper.get('[data-testid="confirmation-grid"] [data-testid="select-all"]').trigger("click");
    await wrapper.get('[data-testid="approve-workflow"]').trigger("click"); await flushPromises();
    expect(wrapper.get('[data-testid="confirm-workflow"]').attributes("disabled")).toBeUndefined();
    await wrapper.get('[data-testid="confirm-workflow"]').trigger("click"); await flushPromises();
    expect(confirmWorkflowConfirmationMock).toHaveBeenCalledWith("confirmation-1", [{ title: "Foo", avalon_confirmation: "approved" }]);
  });

  it("cancels a workflow confirmation before hiding the window", async () => {
    getProactiveConfirmationChatMock.mockResolvedValue(null); loadUiConfigMock.mockResolvedValue({}); getPendingAuthorizationRequestsMock.mockResolvedValue([]);
    getPendingWorkflowConfirmationMock.mockResolvedValue({ id: "confirmation-1", executionId: 4, schema: { title: "Review", columns: [] }, rows: [] });
    const wrapper = mount(ConfirmationWindow); await flushPromises();
    await wrapper.get('[data-testid="cancel-workflow"]').trigger("click"); await flushPromises();
    expect(cancelWorkflowConfirmationMock).toHaveBeenCalledWith("confirmation-1");
    expect(hideConfirmationWindowMock).toHaveBeenCalled();
  });
});
