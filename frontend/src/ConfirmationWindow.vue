<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { isTauri } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import ConfirmationGrid from "./components/ConfirmationGrid.vue";
import type { ConfirmationGridModel } from "./components/confirmationGridModel";
import { loadUiConfig } from "./uiConfig";
import { getProactiveConfirmationChat, type ProactiveConfirmationChat } from "./services/confirmationWindow";
import {
  BACKEND_BASE_URL,
  abortAuthorization,
  confirmAuthorization,
  getChatPermissions,
  getPendingAuthorizationRequests,
  loadAgentBearerToken,
  saveChatPermission,
  setAgentBearerToken,
  type PendingAuthorizationRequest,
  type ProactivePermission,
} from "./services/backend";

const requests = ref<PendingAuthorizationRequest[]>([]);
const proactiveChatId = ref<number>();
const proactiveAgentId = ref<number>();
const proactivePermissions = ref<ProactivePermission[]>([]);
const selectedRequestIds = ref<string[]>([]);
const selectedPermissionIds = ref<string[]>([]);
const expiry = ref(toLocalInputValue(new Date(Date.now() + 10 * 60 * 60 * 1000)));
const loadError = ref(false);
const actionError = ref<string>();
const mode = computed(() => proactiveChatId.value === undefined ? "reactive" : "proactive");
let events: EventSource | undefined;
let refreshPoll: number | undefined;
let unlistenProactive: UnlistenFn | undefined;
let unlistenReactive: UnlistenFn | undefined;

function toLocalInputValue(value: Date): string {
  const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 16);
}
function formatExpiry(value: Date): string {
  return new Intl.DateTimeFormat("de-DE", { dateStyle: "short", timeStyle: "short" }).format(value);
}
function expiryFor(validityType: ProactivePermission["validityType"], defaultExpiry: number, grant?: { expiresAt: string } | null): string {
  if (validityType === "permanent") return "—";
  return formatExpiry(grant ? new Date(grant.expiresAt) : new Date(Date.now() + defaultExpiry * 1000));
}
const reactiveGrid = computed<ConfirmationGridModel>(() => ({
  columns: [
    { id: "context", label: "Context", minWidth: 130, flex: 1 },
    { id: "permission", label: "Permission", minWidth: 160, flex: 1 },
    { id: "approved", label: "Approved", minWidth: 110 },
    { id: "expiry", label: "Expiry", minWidth: 150 },
  ],
  rows: requests.value.map((request) => ({
    id: request.id,
    cells: {
      context: request.context,
      permission: request.key,
      approved: "",
      expiry: request.validityType === "permanent" ? "—" : expiryFor("duration", request.defaultExpiry),
    },
  })),
}));
const proactiveGrid = computed<ConfirmationGridModel>(() => ({
  columns: [
    { id: "context", label: "Context", minWidth: 130, flex: 1 },
    { id: "permission", label: "Permission", minWidth: 160, flex: 1 },
    { id: "approved", label: "Approved", minWidth: 110 },
    { id: "expiry", label: "Expiry", minWidth: 150 },
  ],
  rows: proactivePermissions.value.map((permission) => ({
    id: String(permission.id),
    cells: {
      context: permission.context,
      permission: permission.key,
      approved: permission.grant ? "✓" : "",
      expiry: expiryFor(permission.validityType, permission.defaultExpiry, permission.grant),
    },
  })),
}));

function stopRefreshPolling() {
  if (refreshPoll !== undefined) { window.clearInterval(refreshPoll); refreshPoll = undefined; }
}
function resetExpiry(defaultExpiry: number) {
  expiry.value = toLocalInputValue(new Date(Date.now() + defaultExpiry * 1000));
}
async function openProactiveConfirmations({ chatId, agentId }: ProactiveConfirmationChat, clearActionError = true) {
  stopRefreshPolling();
  proactiveChatId.value = chatId;
  proactiveAgentId.value = agentId;
  proactivePermissions.value = [];
  selectedPermissionIds.value = [];
  if (clearActionError) actionError.value = undefined;
  try {
    setAgentBearerToken(await loadAgentBearerToken(agentId));
    proactivePermissions.value = await getChatPermissions(chatId);
    resetExpiry(proactivePermissions.value.find((permission) => permission.validityType === "duration")?.defaultExpiry ?? 10 * 60 * 60);
    loadError.value = false;
  } catch (error) {
    console.error("Could not load proactive confirmations", error);
    loadError.value = true;
  }
}
async function openReactiveConfirmations() {
  proactiveChatId.value = undefined;
  proactiveAgentId.value = undefined;
  proactivePermissions.value = [];
  selectedRequestIds.value = [];
  actionError.value = undefined;
  refreshForEventWindow();
}
async function refresh() {
  try {
    await loadUiConfig();
    requests.value = await getPendingAuthorizationRequests();
    selectedRequestIds.value = selectedRequestIds.value.filter((id) => requests.value.some((request) => request.id === id));
    resetExpiry(requests.value.find((request) => request.validityType === "duration")?.defaultExpiry ?? 10 * 60 * 60);
    if (requests.value.length > 0) stopRefreshPolling();
    loadError.value = false;
  } catch (error) {
    console.error("Could not load pending authorization requests", error);
    loadError.value = true;
  }
}
function refreshForEventWindow() {
  if (mode.value !== "reactive") return;
  stopRefreshPolling();
  void refresh();
  let attempts = 0;
  refreshPoll = window.setInterval(() => { attempts += 1; void refresh(); if (attempts >= 10) stopRefreshPolling(); }, 500);
}
function durationSeconds(): number {
  const expiresAt = new Date(expiry.value).getTime();
  if (!Number.isFinite(expiresAt) || expiresAt <= Date.now()) throw new Error("Expiry muss in der Zukunft liegen.");
  return Math.max(1, Math.round((expiresAt - Date.now()) / 1000));
}
function expiryIso(): string {
  durationSeconds();
  return new Date(expiry.value).toISOString();
}
async function approveReactive() {
  actionError.value = undefined;
  try {
    for (const request of requests.value.filter((entry) => selectedRequestIds.value.includes(entry.id))) {
      await confirmAuthorization(request.id, request.items.map((_, index) => index), request.validityType === "permanent" ? undefined : durationSeconds());
    }
  } catch (error) {
    console.error("Could not approve authorization requests", error);
    actionError.value = "Permissions konnten nicht geändert werden.";
  } finally { await refresh(); }
}
async function abortReactive() {
  actionError.value = undefined;
  try {
    for (const request of requests.value.filter((entry) => selectedRequestIds.value.includes(entry.id))) await abortAuthorization(request.id);
  } catch (error) {
    console.error("Could not abort authorization requests", error);
    actionError.value = "Permissions konnten nicht geändert werden.";
  } finally { await refresh(); }
}
async function updateProactive(granted: boolean) {
  const chatId = proactiveChatId.value;
  if (chatId === undefined) return;
  actionError.value = undefined;
  try {
    for (const permission of proactivePermissions.value.filter((entry) => selectedPermissionIds.value.includes(String(entry.id)) && !entry.readOnly)) {
      await saveChatPermission(chatId, permission.id, granted, granted && permission.validityType === "duration" ? expiryIso() : undefined);
    }
  } catch (error) {
    console.error("Could not update proactive permissions", error);
    actionError.value = "Permissions konnten nicht geändert werden.";
  } finally {
    const agentId = proactiveAgentId.value;
    if (agentId !== undefined) await openProactiveConfirmations({ chatId, agentId }, false);
  }
}
async function close() {
  if (isTauri()) await getCurrentWindow().hide();
}
onMounted(async () => {
  unlistenProactive = await listen<ProactiveConfirmationChat>("proactive-confirmations-for-chat", (event) => { void openProactiveConfirmations(event.payload); });
  unlistenReactive = await listen("reactive-confirmations", () => { void openReactiveConfirmations(); });
  const chat = await getProactiveConfirmationChat();
  if (chat !== null) await openProactiveConfirmations(chat); else await openReactiveConfirmations();
  if (typeof EventSource !== "undefined") {
    events = new EventSource(`${BACKEND_BASE_URL}/api/v1/authorization-requests/events`);
    events.addEventListener("authorization_requests_changed", refreshForEventWindow);
  }
});
onBeforeUnmount(() => { events?.close(); stopRefreshPolling(); unlistenProactive?.(); unlistenReactive?.(); });
</script>

<template>
  <main class="confirmation-window">
    <nav class="confirmation-tabs" aria-label="Confirmations"><button class="confirmation-tab confirmation-tab--active" type="button">Permissions</button></nav>
    <section class="confirmation-content">
      <p v-if="loadError">Permissions konnten nicht geladen werden.</p>
      <template v-else-if="mode === 'reactive'">
        <p v-if="requests.length === 0">Keine offenen Permissions.</p>
        <ConfirmationGrid v-else v-model:selected-row-ids="selectedRequestIds" :model="reactiveGrid" />
        <section class="confirmation-actions">
          <label>Expiry <input v-model="expiry" type="datetime-local"></label>
          <p v-if="actionError" class="confirmation-error">{{ actionError }}</p>
          <footer><button type="button" data-testid="approve-reactive" @click="approveReactive">Approve</button><button type="button" data-testid="abort-reactive" @click="abortReactive">Abort</button><button type="button" data-testid="close-confirmation" @click="close">Close</button></footer>
        </section>
      </template>
      <template v-else>
        <p v-if="proactivePermissions.length === 0">Keine proaktiv verwaltbaren Permissions.</p>
        <ConfirmationGrid v-else v-model:selected-row-ids="selectedPermissionIds" :model="proactiveGrid" />
        <section class="confirmation-actions">
          <label>Expiry <input v-model="expiry" type="datetime-local"></label>
          <p v-if="actionError" class="confirmation-error">{{ actionError }}</p>
          <footer><button type="button" data-testid="approve-proactive" @click="updateProactive(true)">Approve</button><button type="button" data-testid="revoke-proactive" @click="updateProactive(false)">Revoke</button><button type="button" data-testid="close-confirmation" @click="close">Close</button></footer>
        </section>
      </template>
    </section>
  </main>
</template>

<style scoped>
.confirmation-window { min-height: 100vh; color: #18191d; background: #f8f9fc; font-family: Inter, system-ui, sans-serif; }
.confirmation-tabs { display: flex; padding: .75rem 1rem 0; border-bottom: 1px solid #ccd1dc; background: #fff; }
.confirmation-tab { padding: .55rem 1rem; border: 0; border-bottom: 2px solid #2c6bed; color: #173d8f; background: transparent; font-weight: 650; }
.confirmation-content { padding: 1rem; }
.confirmation-actions { display: grid; gap: .75rem; margin-top: 1rem; }
.confirmation-actions label { display: flex; align-items: center; gap: .5rem; }
.confirmation-actions footer { display: flex; gap: .5rem; }
.confirmation-error { margin: 0; color: #a11b1b; }
</style>
