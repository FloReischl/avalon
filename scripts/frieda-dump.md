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
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useTemplateRef,
} from "vue";
import type { UnlistenFn } from "@tauri-apps/api/event";

import friedaStandard from "./assets/avatars/frieda/standard.png";
import {
  getBackendSnapshot,
  listenToBackendLifecycle,
} from "./services/backendLifecycle";
import {
  setWindowInputRegions,
  type InputRegionRect,
} from "./services/inputShape";

type CompanionState = "idle" | "active";

const backendStatus = ref("initializing");
const backendLogs = ref<string[]>([]);
const companionState = ref<CompanionState>("idle");
const avatarImage = useTemplateRef<HTMLImageElement>("avatarImage");
const avatarRegion = useTemplateRef<HTMLDivElement>("avatarRegion");
const avatarPosition = ref<{ x: number; y: number } | null>(null);
const avatarStyle = computed(() =>
  avatarPosition.value
    ? {
        left: `${avatarPosition.value.x}px`,
        top: `${avatarPosition.value.y}px`,
      }
    : undefined,
);

const minimumVisibleAvatarPixels = 48;
const dragThresholdPixels = 3;

let dragState:
  | {
      pointerId: number;
      pointerStartX: number;
      pointerStartY: number;
      avatarStartX: number;
      avatarStartY: number;
      dragging: boolean;
    }
  | undefined;
let suppressNextAvatarClick = false;
let unlisten: UnlistenFn | undefined;

function addLog(message: string) {
  backendLogs.value.push(message);
}

function activateCompanion() {
  companionState.value = "active";
}

function initializeAvatar() {
  const region = avatarRegion.value;
  if (!region) {
    return;
  }

  const bounds = region.getBoundingClientRect();
  avatarPosition.value = {
    x: bounds.left,
    y: bounds.top,
  };

  void nextTick(applyAvatarInputShape);
}

async function applyAvatarInputShape() {
  const image = avatarImage.value;
  if (!image) {
    return;
  }

  const bounds = image.getBoundingClientRect();
  if (bounds.width <= 0 || bounds.height <= 0) {
    return;
  }

  const scale = window.devicePixelRatio || 1;
  const renderedWidth = Math.max(1, Math.round(bounds.width * scale));
  const renderedHeight = Math.max(1, Math.round(bounds.height * scale));
  const offsetX = Math.round(bounds.left * scale);
  const offsetY = Math.round(bounds.top * scale);

  const canvas = document.createElement("canvas");
  canvas.width = renderedWidth;
  canvas.height = renderedHeight;

  const context = canvas.getContext("2d", {
    willReadFrequently: true,
  });
  if (!context) {
    return;
  }

  context.drawImage(image, 0, 0, renderedWidth, renderedHeight);
  const pixels = context.getImageData(
    0,
    0,
    renderedWidth,
    renderedHeight,
  ).data;

  const rectangles: InputRegionRect[] = [];
  let activeRuns = new Map<string, InputRegionRect>();

  for (let y = 0; y < renderedHeight; y += 1) {
    const nextRuns = new Map<string, InputRegionRect>();
    let x = 0;

    while (x < renderedWidth) {
      const alpha = pixels[(y * renderedWidth + x) * 4 + 3];

      if (alpha <= 16) {
        x += 1;
        continue;
      }

      const runStart = x;
      x += 1;

      while (
        x < renderedWidth &&
        pixels[(y * renderedWidth + x) * 4 + 3] > 16
      ) {
        x += 1;
      }

      const runWidth = x - runStart;
      const absoluteX = offsetX + runStart;
      const absoluteY = offsetY + y;
      const key = `${absoluteX}:${runWidth}`;
      const existing = activeRuns.get(key);

      if (
        existing &&
        existing.y + existing.height === absoluteY
      ) {
        existing.height += 1;
        nextRuns.set(key, existing);
      } else {
        const rectangle: InputRegionRect = {
          x: absoluteX,
          y: absoluteY,
          width: runWidth,
          height: 1,
        };
        rectangles.push(rectangle);
        nextRuns.set(key, rectangle);
      }
    }

    activeRuns = nextRuns;
  }

  try {
    await setWindowInputRegions(rectangles);
    console.info(
      `[input-shape] applied ${rectangles.length} avatar rectangles`,
    );
  } catch (error) {
    console.error("[input-shape] failed to apply X11 input shape", error);
  }
}

function clampAvatarPosition(x: number, y: number) {
  const region = avatarRegion.value;
  if (!region) {
    return { x, y };
  }

  const width = region.offsetWidth;
  const height = region.offsetHeight;

  return {
    x: Math.min(
      window.innerWidth - minimumVisibleAvatarPixels,
      Math.max(minimumVisibleAvatarPixels - width, x),
    ),
    y: Math.min(
      window.innerHeight - minimumVisibleAvatarPixels,
      Math.max(minimumVisibleAvatarPixels - height, y),
    ),
  };
}

function handleAvatarPointerDown(event: PointerEvent) {
  const region = avatarRegion.value;
  if (!region || event.button !== 0) {
    return;
  }

  const bounds = region.getBoundingClientRect();
  dragState = {
    pointerId: event.pointerId,
    pointerStartX: event.clientX,
    pointerStartY: event.clientY,
    avatarStartX: bounds.left,
    avatarStartY: bounds.top,
    dragging: false,
  };

  region.setPointerCapture(event.pointerId);
}

function handleAvatarPointerMove(event: PointerEvent) {
  if (!dragState || dragState.pointerId !== event.pointerId) {
    return;
  }

  const deltaX = event.clientX - dragState.pointerStartX;
  const deltaY = event.clientY - dragState.pointerStartY;

  if (
    !dragState.dragging &&
    Math.hypot(deltaX, deltaY) < dragThresholdPixels
  ) {
    return;
  }

  dragState.dragging = true;
  suppressNextAvatarClick = true;
  avatarPosition.value = clampAvatarPosition(
    dragState.avatarStartX + deltaX,
    dragState.avatarStartY + deltaY,
  );

  void nextTick(applyAvatarInputShape);
}

function handleAvatarPointerUp(event: PointerEvent) {
  const region = avatarRegion.value;
  if (
    !region ||
    !dragState ||
    dragState.pointerId !== event.pointerId
  ) {
    return;
  }

  if (region.hasPointerCapture(event.pointerId)) {
    region.releasePointerCapture(event.pointerId);
  }

  dragState = undefined;
}

function handleAvatarPointerCancel(event: PointerEvent) {
  const region = avatarRegion.value;
  if (
    region &&
    region.hasPointerCapture(event.pointerId)
  ) {
    region.releasePointerCapture(event.pointerId);
  }

  dragState = undefined;
  suppressNextAvatarClick = false;
}

function handleAvatarClick() {
  if (suppressNextAvatarClick) {
    suppressNextAvatarClick = false;
    return;
  }

  activateCompanion();
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

    <div
      ref="avatarRegion"
      class="avatar-region"
      :style="avatarStyle"
      data-testid="avatar-region"
      @pointerdown="handleAvatarPointerDown"
      @pointermove="handleAvatarPointerMove"
      @pointerup="handleAvatarPointerUp"
      @pointercancel="handleAvatarPointerCancel"
      @click="handleAvatarClick"
    >
      <img
        ref="avatarImage"
        class="avatar"
        :src="friedaStandard"
        alt="Frieda"
        data-testid="avatar"
        @load="initializeAvatar"
      />
    </div>

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

.avatar-region {
  position: absolute;
  right: 1.5rem;
  bottom: 0;
  z-index: 3;
  display: block;
  width: min(42vw, 24rem);
  cursor: grab;
  touch-action: none;
}

.avatar-region:active {
  cursor: grabbing;
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