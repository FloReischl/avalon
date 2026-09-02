<script setup lang="ts">
import {
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
import { showChatWindow } from "./services/chatWindow";
import { startAvatarWindowDrag } from "./services/windowDrag";

type CompanionState = "idle" | "active";

const backendStatus = ref("initializing");
const backendLogs = ref<string[]>([]);
const companionState = ref<CompanionState>("idle");
const avatarImage = useTemplateRef<HTMLImageElement>("avatarImage");
const AVATAR_DRAG_THRESHOLD_PX = 5;

let suppressNextAvatarClick = false;
let avatarPointerStart: { x: number; y: number } | undefined;
let unlisten: UnlistenFn | undefined;

function addLog(message: string) {
  backendLogs.value.push(message);
}

function activateCompanion() {
  companionState.value = "active";
}

function initializeAvatar() {
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

function handleAvatarPointerDown(event: PointerEvent) {
  if (event.button !== 0) {
    return;
  }

  avatarPointerStart = {
    x: event.clientX,
    y: event.clientY,
  };
}

async function handleAvatarPointerMove(event: PointerEvent) {
  if (!avatarPointerStart) {
    return;
  }

  const deltaX = event.clientX - avatarPointerStart.x;
  const deltaY = event.clientY - avatarPointerStart.y;

  if (Math.hypot(deltaX, deltaY) < AVATAR_DRAG_THRESHOLD_PX) {
    return;
  }

  avatarPointerStart = undefined;
  suppressNextAvatarClick = true;

  try {
    await startAvatarWindowDrag();
  } catch (error) {
    suppressNextAvatarClick = false;
    console.error("[window-drag] failed to start window drag", error);
  }
}

function handleAvatarPointerUp() {
  avatarPointerStart = undefined;
}

function handleAvatarClick() {
  if (suppressNextAvatarClick) {
    suppressNextAvatarClick = false;
    return;
  }

  activateCompanion();
}

async function handleAvatarDoubleClick() {
  try {
    await showChatWindow();
  } catch (error) {
    console.error("[chat-window] failed to show chat window", error);
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
      @pointerdown="handleAvatarPointerDown"
      @pointermove="handleAvatarPointerMove"
      @pointerup="handleAvatarPointerUp"
      @pointercancel="handleAvatarPointerUp"
      @click="handleAvatarClick"
      @dblclick="handleAvatarDoubleClick"
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

