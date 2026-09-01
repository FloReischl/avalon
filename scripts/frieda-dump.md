Project Path: avalo

Source Tree:

```txt
avalo
├── frontend
│   └── src
│       ├── App.vue
│       └── styles.css
└── src-tauri
    └── capabilities
        └── default.json

```

`frontend/src/App.vue`:

```vue
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import type { UnlistenFn } from "@tauri-apps/api/event";

import friedaStandard from "./assets/avatars/frieda/standard.png";
import {
  getBackendSnapshot,
  listenToBackendLifecycle,
} from "./services/backendLifecycle";

type CompanionState = "idle" | "active";

const backendStatus = ref("initializing");
const backendLogs = ref<string[]>([]);
const companionState = ref<CompanionState>("idle");
let unlisten: UnlistenFn | undefined;

function addLog(message: string) {
  backendLogs.value.push(message);
}

function toggleCompanion() {
  companionState.value =
    companionState.value === "idle" ? "active" : "idle";
}

onMounted(async () => {
  try {
    unlisten = await listenToBackendLifecycle({
      onStatus: (status) => {
        backendStatus.value = status;
      },
      onLog: addLog,
    });

    const snapshot = await getBackendSnapshot();
    backendStatus.value = snapshot.status;
    backendLogs.value = snapshot.logs;
  } catch (error) {
    backendStatus.value = "failed";
    addLog(
      error instanceof Error
        ? `Failed to initialize desktop lifecycle: ${error.message}`
        : "Failed to initialize desktop lifecycle",
    );
  }
});

onBeforeUnmount(() => {
  unlisten?.();
});
</script>

<template>
  <main class="companion-shell">
    <section
      v-if="backendStatus !== 'ready'"
      class="startup-panel"
      data-testid="startup-panel"
    >
      <header class="startup-header">
        <span>AVALO // LOCAL COMPANION</span>
        <span data-testid="backend-status">{{ backendStatus }}</span>
      </header>

      <div class="startup-log" data-testid="startup-log">
        <p v-for="(line, index) in backendLogs" :key="index">
          <span class="prompt">&gt;</span> {{ line }}
        </p>
        <p v-if="backendLogs.length === 0">
          <span class="prompt">&gt;</span> Initializing Avalo …
        </p>
      </div>
    </section>

    <section
      v-if="backendStatus === 'ready' && companionState === 'active'"
      class="active-panel"
      data-testid="active-panel"
    >
      <strong>Avalo</strong>
      <span>Active</span>
    </section>

    <button
      class="avatar-button"
      type="button"
      aria-label="Toggle Avalo companion"
      data-testid="avatar-button"
      @click="toggleCompanion"
    >
      <img
        class="avatar"
        :src="friedaStandard"
        alt="Frieda"
        data-testid="avatar"
      />
    </button>

    <span
      v-if="backendStatus === 'ready'"
      class="backend-ready-marker"
      data-testid="backend-status"
    >
      Backend ready
    </span>
  </main>
</template>


```
`frontend/src/styles.css`:

```css
:root {
  font-family: Inter, system-ui, sans-serif;
  color: #e8e8ea;
  background: transparent;
}

html,
body,
#app {
  width: 100%;
  min-height: 100%;
  margin: 0;
  background: transparent;
}

body {
  min-height: 100vh;
}

.companion-shell {
  box-sizing: border-box;
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.startup-panel {
  box-sizing: border-box;
  width: min(46rem, 100%);
  max-height: 60vh;
  overflow: hidden;
  border: 1px solid rgba(232, 232, 234, 0.45);
  background: rgba(12, 13, 16, 0.88);
  font-family: "DejaVu Sans Mono", "Liberation Mono", monospace;
  box-shadow: 0 0 2rem rgba(0, 0, 0, 0.35);
}

.startup-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.7rem 0.9rem;
  border-bottom: 1px solid rgba(232, 232, 234, 0.25);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.startup-log {
  box-sizing: border-box;
  max-height: calc(60vh - 2.5rem);
  overflow-y: auto;
  padding: 0.8rem 0.9rem;
  font-size: 0.8rem;
  line-height: 1.45;
}

.startup-log p {
  margin: 0 0 0.25rem;
  overflow-wrap: anywhere;
}

.prompt {
  opacity: 0.55;
}

.app-shell {
  width: min(42rem, calc(100% - 3rem));
  margin: 15vh auto;
}

.status {
  color: #9fa8ff;
}

.startup-panel {
  position: absolute;
  left: 2rem;
  bottom: 2rem;
  z-index: 2;
}

.avatar-button {
  position: absolute;
  right: 1.5rem;
  bottom: 0;
  z-index: 3;
  display: block;
  width: min(42vw, 24rem);
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.avatar-button:focus-visible {
  outline: 2px solid rgba(232, 232, 234, 0.8);
  outline-offset: 0.25rem;
}

.avatar {
  display: block;
  width: 100%;
  height: auto;
  user-select: none;
  -webkit-user-drag: none;
}

.active-panel {
  position: absolute;
  right: min(42vw, 25rem);
  bottom: 5rem;
  z-index: 2;
  display: flex;
  gap: 0.75rem;
  align-items: baseline;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(232, 232, 234, 0.35);
  background: rgba(12, 13, 16, 0.82);
  backdrop-filter: blur(0.5rem);
}

.active-panel span {
  opacity: 0.65;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.backend-ready-marker {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
}


```
`src-tauri/capabilities/default.json`:

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Default capability for Avalo",
  "windows": ["main"],
  "permissions": ["core:default"]
}
```