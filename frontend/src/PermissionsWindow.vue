<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import PermissionDetails from "./components/PermissionDetails.vue";
import { getProactivePermissionsChatId } from "./services/permissionsWindow";
import { BACKEND_BASE_URL, abortAuthorization, confirmAuthorization, getChatPermissions, getPendingAuthorizationRequests, saveChatPermission, type PendingAuthorizationRequest, type ProactivePermission } from "./services/backend";

const requests = ref<PendingAuthorizationRequest[]>([]);
const selectedId = ref<string>();
const selected = computed(() => requests.value.find((request) => request.id === selectedId.value));
const selectedItems = ref<number[]>([]);
const durationHours = ref(10);
const proactiveChatId = ref<number>();
const proactivePermissions = ref<ProactivePermission[]>([]);
const proactiveSelection = ref<Record<number, { granted: boolean; expiresAt: string }>>({});
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
  return new Date(value.getTime() - value.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}
function initializeProactiveSelection(permissions: ProactivePermission[]) {
  proactiveSelection.value = Object.fromEntries(permissions.map((permission) => [permission.id, {
    granted: Boolean(permission.grant),
    expiresAt: localDateTime(permission.grant ? new Date(permission.grant.expiresAt) : new Date(Date.now() + permission.defaultExpiry * 1000)),
  }]));
}
async function openProactivePermissions(chatId: number) {
  stopRefreshPolling();
  proactiveChatId.value = chatId;
  proactivePermissions.value = await getChatPermissions(chatId);
  initializeProactiveSelection(proactivePermissions.value);
}
function stopRefreshPolling() { if (refreshPoll !== undefined) { window.clearInterval(refreshPoll); refreshPoll = undefined; } }
async function refresh() {
  requests.value = await getPendingAuthorizationRequests();
  if (!selected.value) selectRequest(requests.value[0]);
  if (requests.value.length > 0) stopRefreshPolling();
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
    if (permission.readOnly || !selection?.granted) continue;
    await saveChatPermission(chatId, permission.id, permission.validityType === "duration" ? new Date(selection.expiresAt).toISOString() : undefined);
  }
  await openProactivePermissions(chatId);
}
function cancelProactive() { proactiveChatId.value = undefined; proactivePermissions.value = []; proactiveSelection.value = {}; refreshForEventWindow(); }
onMounted(async () => {
  refreshForEventWindow();
  if (typeof EventSource !== "undefined") { events = new EventSource(`${BACKEND_BASE_URL}/api/v1/authorization-requests/events`); events.addEventListener("authorization_requests_changed", refreshForEventWindow); }
  unlistenProactive = await listen<number>("proactive-permissions-for-chat", (event) => { void openProactivePermissions(event.payload); });
  unlistenReactive = await listen("reactive-permissions", cancelProactive);
  const chatId = await getProactivePermissionsChatId();
  if (chatId !== null) await openProactivePermissions(chatId);
});
onBeforeUnmount(() => { events?.close(); stopRefreshPolling(); unlistenProactive?.(); unlistenReactive?.(); });
</script>
<template>
  <main class="permissions">
    <template v-if="mode === 'reactive'">
      <aside><button v-for="request in requests" :key="request.id" @click="selectRequest(request)">{{ request.sourceLabel }}<br><small>{{ request.context }}.{{ request.key }}</small></button></aside>
      <PermissionDetails v-if="selected" :context="selected.context" :permission-key="selected.key" :validity-type="selected.validityType" :granted="false">
        <label v-for="(item, index) in selected.items" :key="index"><input v-model="selectedItems" type="checkbox" :value="index">{{ item }}</label>
        <label v-if="selected.validityType !== 'permanent'">Stunden <input v-model.number="durationHours" type="number" min="1" max="8760"></label>
        <footer><button @click="abort">Abbrechen</button><button @click="confirm">Bestätigen</button></footer>
      </PermissionDetails><section v-else><p>Keine offenen Permissions.</p></section>
    </template>
    <section v-else class="proactive-permissions"><h1>Permissions des Chats</h1><p v-if="proactivePermissions.length === 0">Keine proaktiv verwaltbaren Permissions.</p>
      <PermissionDetails v-for="permission in proactivePermissions" :key="permission.id" :context="permission.context" :permission-key="permission.key" :validity-type="permission.validityType" :granted="Boolean(permission.grant)" :read-only="permission.readOnly">
        <template v-if="permission.readOnly"><p>Range-Grants können nur beim Capability-Request geändert werden.</p></template>
        <template v-else><label><input v-model="proactiveSelection[permission.id].granted" type="checkbox"> Erteilen</label><label v-if="permission.validityType === 'duration'">Ablaufdatum und -zeit <input v-model="proactiveSelection[permission.id].expiresAt" type="datetime-local"></label></template>
      </PermissionDetails><footer><button @click="cancelProactive">Abbrechen</button><button @click="saveProactive">Speichern</button></footer>
    </section>
  </main>
</template>
<style scoped>.permissions{display:grid;grid-template-columns:16rem 1fr;min-height:100vh;color:#111;font-family:sans-serif}.permissions aside{padding:1rem;border-right:1px solid #ddd}.permissions aside button{display:block;width:100%;margin-bottom:.5rem;text-align:left}.permissions label{display:block;margin:.7rem 0}.permissions footer,.proactive-permissions>footer{margin:1.5rem;display:flex;gap:.75rem}.proactive-permissions{grid-column:1 / -1}.proactive-permissions>.permission-details{border-bottom:1px solid #ddd}</style>
