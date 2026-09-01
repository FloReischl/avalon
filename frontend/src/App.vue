<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, useTemplateRef } from "vue";
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
const avatarHit = ref(false);
let avatarAlphaContext: CanvasRenderingContext2D | null = null;
let avatarPixelWidth = 0;
let avatarPixelHeight = 0;
let unlisten: UnlistenFn | undefined;

function addLog(message: string) {
  backendLogs.value.push(message);
}

function toggleCompanion() {
  companionState.value =
    companionState.value === "idle" ? "active" : "idle";
}

function initializeAvatarAlphaMask() {
  const image = avatarImage.value;
  if (!image || image.naturalWidth === 0 || image.naturalHeight === 0) {
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;

  const context = canvas.getContext("2d", {
    willReadFrequently: true,
  });
  if (!context) {
    return;
  }

  context.drawImage(image, 0, 0);
  avatarAlphaContext = context;
  avatarPixelWidth = image.naturalWidth;
  avatarPixelHeight = image.naturalHeight;

  void applyAvatarInputShape();
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

function updateAvatarHit(event: PointerEvent) {
  const image = avatarImage.value;
  if (
    !image ||
    !avatarAlphaContext ||
    avatarPixelWidth === 0 ||
    avatarPixelHeight === 0
  ) {
    avatarHit.value = false;
    return;
  }

  const bounds = image.getBoundingClientRect();
  if (
    bounds.width === 0 ||
    bounds.height === 0 ||
    event.clientX < bounds.left ||
    event.clientX >= bounds.right ||
    event.clientY < bounds.top ||
    event.clientY >= bounds.bottom
  ) {
    avatarHit.value = false;
    return;
  }

  const pixelX = Math.min(
    avatarPixelWidth - 1,
    Math.floor(
      ((event.clientX - bounds.left) / bounds.width) * avatarPixelWidth,
    ),
  );
  const pixelY = Math.min(
    avatarPixelHeight - 1,
    Math.floor(
      ((event.clientY - bounds.top) / bounds.height) * avatarPixelHeight,
    ),
  );

  const alpha = avatarAlphaContext.getImageData(
    pixelX,
    pixelY,
    1,
    1,
  ).data[3];

  avatarHit.value = alpha > 16;
}

function handleAvatarClick() {
  if (avatarHit.value) {
    toggleCompanion();
  }
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
      class="avatar-region"
      data-testid="avatar-region"
      @pointermove="updateAvatarHit"
      @pointerleave="avatarHit = false"
      @click="handleAvatarClick"
    >
      <img
        ref="avatarImage"
        class="avatar"
        :src="friedaStandard"
        alt="Frieda"
        data-testid="avatar"
        @load="initializeAvatarAlphaMask"
      />

      <span
        class="hit-debug"
        :class="{ hit: avatarHit }"
        data-testid="hit-debug"
      >
        {{ avatarHit ? "HIT" : "MISS" }}
      </span>
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

