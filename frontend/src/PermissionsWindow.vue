<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { abortAuthorization, confirmAuthorization, getPendingAuthorizationRequests, type PendingAuthorizationRequest } from "./services/backend";

const requests = ref<PendingAuthorizationRequest[]>([]);
const selectedId = ref<string>();
const selected = computed(() => requests.value.find((request) => request.id === selectedId.value));
const selectedItems = ref<number[]>([]);
const durationHours = ref(10);
let events: EventSource | undefined;

async function refresh() {
  requests.value = await getPendingAuthorizationRequests();
  if (!selected.value) selectedId.value = requests.value[0]?.id;
  const request = selected.value;
  selectedItems.value = request ? request.items.map((_, index) => index) : [];
  durationHours.value = request ? Math.max(1, Math.round(request.defaultExpiry / 3600)) : 10;
}
async function confirm() { if (selected.value) { await confirmAuthorization(selected.value.id, selectedItems.value, selected.value.validityType === "permanent" ? undefined : durationHours.value * 3600); await refresh(); } }
async function abort() { if (selected.value) { await abortAuthorization(selected.value.id); await refresh(); } }
onMounted(async () => { await refresh(); events = new EventSource("http://127.0.0.1:8095/api/v1/authorization-requests/events"); events.addEventListener("authorization_requests_changed", () => { void refresh(); }); });
onBeforeUnmount(() => events?.close());
</script>
<template><main class="permissions"><aside><button v-for="request in requests" :key="request.id" @click="selectedId = request.id">{{ request.sourceLabel }}<br><small>{{ request.context }}.{{ request.key }}</small></button></aside><section v-if="selected"><h1>Permission</h1><p>{{ selected.context }}.{{ selected.key }}</p><label v-for="(item, index) in selected.items" :key="index"><input v-model="selectedItems" type="checkbox" :value="index">{{ item }}</label><label v-if="selected.validityType !== 'permanent'">Stunden <input v-model.number="durationHours" type="number" min="1" max="8760"></label><footer><button @click="abort">Abbrechen</button><button @click="confirm">Bestätigen</button></footer></section><section v-else><p>Keine offenen Permissions.</p></section></main></template>
<style scoped>.permissions{display:grid;grid-template-columns:16rem 1fr;min-height:100vh;font-family:sans-serif}.permissions aside{padding:1rem;border-right:1px solid #ddd}.permissions aside button{display:block;width:100%;margin-bottom:.5rem;text-align:left}.permissions section{padding:1.5rem}.permissions label{display:block;margin:.7rem 0}.permissions footer{margin-top:1.5rem;display:flex;gap:.75rem}</style>
