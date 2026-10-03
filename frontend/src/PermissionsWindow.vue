<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import PermissionDetails from "./components/PermissionDetails.vue";
import { loadUiConfig } from "./uiConfig";
import { getProactivePermissionsChat, type ProactivePermissionsChat } from "./services/permissionsWindow";
import { BACKEND_BASE_URL, abortAuthorization, confirmAuthorization, getChatPermissions, getPendingAuthorizationRequests, loadPrincipalBearerToken, saveChatPermission, setPrincipalBearerToken, type PendingAuthorizationRequest, type ProactivePermission } from "./services/backend";

const requests = ref<PendingAuthorizationRequest[]>([]);
const selectedId = ref<string>();
const selected = computed(() => requests.value.find((request) => request.id === selectedId.value));
const selectedItems = ref<number[]>([]);
const durationHours = ref(10);
const proactiveChatId = ref<number>();
const proactivePrincipalId = ref<number>();
const proactivePermissions = ref<ProactivePermission[]>([]);
const proactiveSelection = ref<Record<number, { granted: boolean; expiresAt: string }>>({});
const loadError = ref(false);
const mode = computed(() => proactiveChatId.value === undefined ? "reactive" : "proactive");
let events: EventSource | undefined;
let refreshPoll: number | undefined;
let unlistenProactive: UnlistenFn | undefined;
let unlistenReactive: UnlistenFn | undefined;

function selectRequest(request: PendingAuthorizationRequest | undefined) {
  selectedId.value = request?.id;
  selectedItems.value = request ? request.items.map((_, index) => index) : [];
  durationHours.value = request ? Math.max(1, Math.round(request.defaultExpiry / 3600)) : 10;
}
function localDateTime(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  const hours = String(value.getHours()).padStart(2, "0");
  const minutes = String(value.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}
function initializeProactiveSelection(permissions: ProactivePermission[]) {
  proactiveSelection.value = Object.fromEntries(permissions.map((permission) => [permission.id, {
    granted: Boolean(permission.grant),
    expiresAt: localDateTime(permission.grant ? new Date(permission.grant.expiresAt) : new Date(Date.now() + permission.defaultExpiry * 1000)),
  }]));
}
async function openProactivePermissions({ chatId, principalId }: ProactivePermissionsChat) {
  stopRefreshPolling();
  proactiveChatId.value = chatId;
  proactivePrincipalId.value = principalId;
  proactivePermissions.value = [];
  proactiveSelection.value = {};
  try {
    setPrincipalBearerToken(await loadPrincipalBearerToken(principalId));
    proactivePermissions.value = await getChatPermissions(chatId);
    initializeProactiveSelection(proactivePermissions.value);
    loadError.value = false;
  } catch (error) {
    console.error("Could not load proactive permissions", error);
    loadError.value = true;
  }
}
async function openReactivePermissions() {
  proactiveChatId.value = undefined;
  proactivePrincipalId.value = undefined;
  proactivePermissions.value = [];
  proactiveSelection.value = {};
  refreshForEventWindow();
}
function stopRefreshPolling() { if (refreshPoll !== undefined) { window.clearInterval(refreshPoll); refreshPoll = undefined; } }
async function refresh() {
  try {
    await loadUiConfig();
    requests.value = await getPendingAuthorizationRequests();
    if (!selected.value) selectRequest(requests.value[0]);
    if (requests.value.length > 0) stopRefreshPolling();
    loadError.value = false;
  } catch (error) {
    console.error("Could not load pending authorization requests", error);
    loadError.value = true;
  }
}
function refreshForEventWindow() {
  if (mode.value !== "reactive") return;
  stopRefreshPolling(); void refresh(); let attempts = 0;
  refreshPoll = window.setInterval(() => { attempts += 1; void refresh(); if (attempts >= 10) stopRefreshPolling(); }, 500);
}
async function confirm() {
  if (!selected.value) return;
  await confirmAuthorization(selected.value.id, selectedItems.value, selected.value.validityType === "permanent" ? undefined : durationHours.value * 3600);
  await refresh();
}
async function abort() { if (selected.value) { await abortAuthorization(selected.value.id); await refresh(); } }
async function saveProactive() {
  const chatId = proactiveChatId.value;
  if (chatId === undefined) return;
  for (const permission of proactivePermissions.value) {
    const selection = proactiveSelection.value[permission.id];
    if (permission.readOnly) continue;
    const granted = Boolean(selection?.granted);
    const expiresAt = permission.validityType === "duration" && granted ? selection?.expiresAt : undefined;
    await saveChatPermission(chatId, permission.id, granted, expiresAt);
  }
  const principalId = proactivePrincipalId.value;
  if (principalId === undefined) return;
  await openProactivePermissions({ chatId, principalId });
}
function cancelProactive() { void openReactivePermissions(); }
onMounted(async () => {
  unlistenProactive = await listen<ProactivePermissionsChat>("proactive-permissions-for-chat", (event) => { void openProactivePermissions(event.payload); });
  unlistenReactive = await listen("reactive-permissions", cancelProactive);
  const chat = await getProactivePermissionsChat();
  if (chat !== null) {
    await openProactivePermissions(chat);
  } else {
    await openReactivePermissions();
  }
  if (typeof EventSource !== "undefined") { events = new EventSource(`${BACKEND_BASE_URL}/api/v1/authorization-requests/events`); events.addEventListener("authorization_requests_changed", refreshForEventWindow); }
});
onBeforeUnmount(() => { events?.close(); stopRefreshPolling(); unlistenProactive?.(); unlistenReactive?.(); });
</script>
<template>
  <main class="permissions">
    <template v-if="mode === 'reactive'">
      <section v-if="loadError"><p>Permissions konnten nicht geladen werden.</p></section>
      <template v-else><aside><button v-for="request in requests" :key="request.id" @click="selectRequest(request)">{{ request.sourceLabel }}<br><small>{{ request.context }}.{{ request.key }}</small></button></aside>
      <PermissionDetails v-if="selected" :context="selected.context" :permission-key="selected.key" :validity-type="selected.validityType" :granted="false">
        <label v-for="(item, index) in selected.items" :key="index"><input v-model="selectedItems" type="checkbox" :value="index">{{ item }}</label>
        <label v-if="selected.validityType !== 'permanent'">Stunden <input v-model.number="durationHours" type="number" min="1" max="8760"></label>
        <footer><button @click="abort">Abbrechen</button><button @click="confirm">Bestätigen</button></footer>
      </PermissionDetails><section v-else><p>Keine offenen Permissions.</p></section></template>
    </template>
    <section v-else class="proactive-permissions"><h1>Permissions des Chats</h1><p v-if="loadError">Permissions konnten nicht geladen werden.</p><p v-else-if="proactivePermissions.length === 0">Keine proaktiv verwaltbaren Permissions.</p>
      <PermissionDetails v-for="permission in proactivePermissions" :key="permission.id" :context="permission.context" :permission-key="permission.key" :validity-type="permission.validityType" :granted="Boolean(permission.grant)" :read-only="permission.readOnly">
        <template v-if="permission.readOnly"><p>Range-Grants können nur beim Capability-Request geändert werden.</p></template>
        <template v-else><label><input v-model="proactiveSelection[permission.id].granted" type="checkbox"> Erteilen</label><label v-if="permission.validityType === 'duration'">Ablaufdatum und -zeit <input v-model="proactiveSelection[permission.id].expiresAt" type="text" placeholder="YYYY-MM-DD HH:mm"></label></template>
      </PermissionDetails><footer><button @click="cancelProactive">Abbrechen</button><button @click="saveProactive">Speichern</button></footer>
    </section>
  </main>
</template>
<style scoped>.permissions{display:grid;grid-template-columns:16rem 1fr;min-height:100vh;color:#111;font-family:sans-serif}.permissions aside{padding:1rem;border-right:1px solid #ddd}.permissions aside button{display:block;width:100%;margin-bottom:.5rem;text-align:left}.permissions label{display:block;margin:.7rem 0}.permissions footer,.proactive-permissions>footer{margin:1.5rem;display:flex;gap:.75rem}.proactive-permissions{grid-column:1 / -1}.proactive-permissions>.permission-details{border-bottom:1px solid #ddd}</style>
