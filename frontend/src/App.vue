<script setup lang="ts">
import { onMounted, ref } from "vue";

import { getBackendHealth } from "./services/backend";

const backendStatus = ref("Prüfe Backend …");

onMounted(async () => {
  try {
    const health = await getBackendHealth();
    backendStatus.value = `${health.service}: ${health.status}`;
  } catch {
    backendStatus.value = "Backend nicht erreichbar";
  }
});
</script>

<template>
  <main class="app-shell">
    <h1>Avalo</h1>
    <p>Lokaler Companion – Grundgerüst</p>
    <p class="status" data-testid="backend-status">{{ backendStatus }}</p>
  </main>
</template>

