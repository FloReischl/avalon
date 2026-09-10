<script setup lang="ts">
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useTemplateRef,
  watch,
} from "vue";
import type { UnlistenFn } from "@tauri-apps/api/event";

import {

  getBackendSnapshot,
  listenToBackendLifecycle,
} from "./services/backendLifecycle";
import { loadUiConfig, type UiConfig } from "./uiConfig";

import {
  resizeAvatarWindow,
  setWindowInputRegions,
  type InputRegionRect,
} from "./services/inputShape";
import { exitAvalo } from "./services/appLifecycle";
import { showChatWindow } from "./services/chatWindow";
import { startAvatarWindowDrag } from "./services/windowDrag";
import { setAvatarWindowTitle } from "./services/windowTitle";

type AudioState = "idle" | "recording";


const uiConfig = ref<UiConfig>();
const MAX_AUDIO_SECONDS = 30;

const AVATAR_DRAG_THRESHOLD_PX = 5;
const AVATAR_MIN_PERCENT = 50;
const AVATAR_MAX_PERCENT = 150;
const AVATAR_SCALE_STEP_PERCENT = 10;
const AVATAR_WINDOW_MIN_WIDTH_PX = 320;
const AVATAR_WINDOW_PADDING_PX = 48;

const backendStatus = ref("initializing");
const backendLogs = ref<string[]>([]);
const audioState = ref<AudioState>("idle");
const remainingRecordingSeconds = ref(MAX_AUDIO_SECONDS);
const avatarScalePercent = ref(100);
const avatarStage = useTemplateRef<HTMLDivElement>("avatarStage");
const avatarImage = useTemplateRef<HTMLImageElement>("avatarImage");
const audioButton = useTemplateRef<HTMLButtonElement>("audioButton");
const exitButton = useTemplateRef<HTMLButtonElement>("exitButton");

let avatarPointerStart: { x: number; y: number } | undefined;
let recordingTimer: number | undefined;
let audioPointerHeld = false;
let avatarLoaded = false;
let avatarSyncRunning = false;
let avatarSyncPending = false;
let uiConfigLoading = false;
let unlisten: UnlistenFn | undefined;

function addLog(message: string) {

  backendLogs.value.push(message);
}

async function syncAvatarWindowSize(): Promise<boolean> {
  if (!avatarLoaded || backendStatus.value !== "ready") {
    return false;
  }

  const stage = avatarStage.value;
  if (!stage) {
    return false;
  }

  const bounds = stage.getBoundingClientRect();
  if (bounds.width <= 0 || bounds.height <= 0) {
    return false;
  }

  const width = Math.max(
    AVATAR_WINDOW_MIN_WIDTH_PX,
    Math.ceil(bounds.width + AVATAR_WINDOW_PADDING_PX * 2),
  );
  const height = Math.ceil(
    bounds.height + AVATAR_WINDOW_PADDING_PX * 2,
  );

  try {
    await resizeAvatarWindow(width, height);
    return true;
  } catch (error) {
    console.error("[avatar-window] failed to resize avatar window", error);
    return false;
  }
}

function requestAvatarSync() {
  avatarSyncPending = true;

  if (avatarSyncRunning) {
    return;
  }

  avatarSyncRunning = true;
  void runAvatarSync();
}

async function runAvatarSync() {
  try {
    do {
      avatarSyncPending = false;

      await nextTick();
      const resizeRequested = await syncAvatarWindowSize();

      if (!resizeRequested) {
        await nextTick();
        await applyAvatarInputShape();
      }
    } while (avatarSyncPending);
  } finally {
    avatarSyncRunning = false;

    if (avatarSyncPending) {
      requestAvatarSync();
    }
  }
}

function handleAvatarWindowResize() {
  if (!avatarLoaded) {
    return;
  }

  void nextTick().then(() => applyAvatarInputShape());
}

async function changeAvatarScale(delta: number) {
  const nextScale = Math.min(
    AVATAR_MAX_PERCENT,
    Math.max(AVATAR_MIN_PERCENT, avatarScalePercent.value + delta),
  );

  if (nextScale === avatarScalePercent.value) {
    return;
  }

  avatarScalePercent.value = nextScale;
  requestAvatarSync();
}

function handleAvatarScaleKeydown(event: KeyboardEvent) {
  if (!event.ctrlKey || event.repeat) {
    return;
  }

  const increase =
    event.key === "+" ||
    event.code === "NumpadAdd";

  const decrease =
    event.key === "-" ||
    event.code === "NumpadSubtract";

  if (!increase && !decrease) {
    return;
  }

  event.preventDefault();

  void changeAvatarScale(
    increase ? AVATAR_SCALE_STEP_PERCENT : -AVATAR_SCALE_STEP_PERCENT,
  );
}

function initializeAvatar() {
  avatarLoaded = true;
  requestAvatarSync();
}

async function initializeUiConfig() {
  if (uiConfig.value || uiConfigLoading) {
    return;
  }

  uiConfigLoading = true;

  try {
    uiConfig.value = await loadUiConfig();
    await setAvatarWindowTitle(uiConfig.value.name);

  } catch (error) {
    console.error("[ui-config] failed to load UI config", error);
    backendStatus.value = "failed";
    addLog(
      error instanceof Error
        ? `Failed to load UI config: ${error.message}`
        : "Failed to load UI config",
    );
  } finally {
    uiConfigLoading = false;
  }
}

function clearRecordingTimer() {

  if (recordingTimer !== undefined) {
    window.clearInterval(recordingTimer);
    recordingTimer = undefined;
  }
}

function removeRecordingEndListeners() {
  window.removeEventListener("pointerup", finishAudioRecording);
  window.removeEventListener("pointercancel", abortAudioRecording);
}

function resetAudioRecordingState() {
  clearRecordingTimer();
  removeRecordingEndListeners();
  audioState.value = "idle";
  remainingRecordingSeconds.value = MAX_AUDIO_SECONDS;
}

function finishAudioRecording() {
  audioPointerHeld = false;

  if (audioState.value !== "recording") {
    return;
  }

  resetAudioRecordingState();
}

function abortAudioRecording() {
  audioPointerHeld = false;

  if (audioState.value !== "recording") {
    return;
  }

  resetAudioRecordingState();
}

function startAudioRecording(event: PointerEvent) {
  if (event.button !== 0 || audioPointerHeld || audioState.value === "recording") {
    return;
  }

  event.preventDefault();
  audioPointerHeld = true;

  window.addEventListener("pointerup", finishAudioRecording);
  window.addEventListener("pointercancel", abortAudioRecording);

  audioState.value = "recording";
  remainingRecordingSeconds.value = MAX_AUDIO_SECONDS;

  recordingTimer = window.setInterval(() => {
    remainingRecordingSeconds.value -= 1;

    if (remainingRecordingSeconds.value <= 0) {
      abortAudioRecording();
    }
  }, 1000);
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

  const controls: Array<HTMLElement | null> = [
    audioButton.value,
    exitButton.value,
  ];

  for (const control of controls) {
    if (!control) {
      continue;
    }

    const controlBounds = control.getBoundingClientRect();

    if (controlBounds.width > 0 && controlBounds.height > 0) {
      rectangles.push({
        x: Math.round(controlBounds.left * scale),
        y: Math.round(controlBounds.top * scale),
        width: Math.max(1, Math.round(controlBounds.width * scale)),
        height: Math.max(1, Math.round(controlBounds.height * scale)),
      });
    }
  }

  try {
    await setWindowInputRegions(rectangles);
    console.info(
      `[input-shape] applied ${rectangles.length} input rectangles`,
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

  try {
    await startAvatarWindowDrag();
  } catch (error) {
    console.error("[window-drag] failed to start window drag", error);
  }
}

function handleAvatarPointerUp() {
  avatarPointerStart = undefined;
}

async function handleAvatarDoubleClick() {
  try {
    await showChatWindow();
  } catch (error) {
    console.error("[chat-window] failed to show chat window", error);
  }
}

async function handleExit() {
  try {
    await exitAvalo();
  } catch (error) {
    console.error("[app] failed to exit Avalo", error);
  }
}

onMounted(async () => {
  window.addEventListener("keydown", handleAvatarScaleKeydown);
  window.addEventListener("resize", handleAvatarWindowResize);

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
    console.error(
      "[backend-lifecycle] failed to initialize desktop lifecycle",
      error,
    );
    backendStatus.value = "failed";
    addLog(
      error instanceof Error
        ? `Failed to initialize desktop lifecycle: ${error.message}`
        : "Failed to initialize desktop lifecycle",
    );
  }
});

watch(
  backendStatus,
  (status) => {
    if (status !== "ready") {
      return;
    }

    if (!uiConfig.value) {
      void initializeUiConfig();
      return;
    }

    if (avatarLoaded) {
      requestAvatarSync();
    }
  },
  { immediate: true },
);


onBeforeUnmount(() => {
  audioPointerHeld = false;
  window.removeEventListener("keydown", handleAvatarScaleKeydown);
  window.removeEventListener("resize", handleAvatarWindowResize);
  resetAudioRecordingState();
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

    <div
      v-if="uiConfig"
      ref="avatarStage"
      class="avatar-stage"
      data-testid="avatar-stage"
    >

      <div
        class="avatar-region"
        :style="{ width: `${24 * avatarScalePercent / 100}rem` }"
        data-testid="avatar-region"

        @pointerdown="handleAvatarPointerDown"
        @pointermove="handleAvatarPointerMove"
        @pointerup="handleAvatarPointerUp"
        @pointercancel="handleAvatarPointerUp"
        @dblclick="handleAvatarDoubleClick"
      >
        <img
          ref="avatarImage"
          class="avatar"
          :src="uiConfig.avatar.standard.url"
          :alt="uiConfig.name"

          data-testid="avatar"
          @load="initializeAvatar"
        />
      </div>

      <div
        class="audio-control"
        :style="{ width: `${24 * avatarScalePercent / 100}rem` }"
      >
        <div class="avatar-control-buttons">
          <button
            ref="audioButton"
            class="audio-button"
            :class="{ 'audio-button--recording': audioState === 'recording' }"
            type="button"
            aria-label="Push to talk"
            :aria-pressed="audioState === 'recording'"
            data-testid="audio-button"
            @pointerdown="startAudioRecording"
            @pointerup="finishAudioRecording"
            @pointercancel="abortAudioRecording"
          >
            <svg
              class="audio-icon"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21H8v2h8v-2h-3v-2.08A7 7 0 0 0 19 12h-2Z"
              />
            </svg>
          </button>

          <button
            ref="exitButton"
            class="audio-button"
            type="button"
            aria-label="Exit"
            title="Exit"
            data-testid="exit-button"
            @click="handleExit"
          >
            <svg
              class="audio-icon"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10"
              />
            </svg>
          </button>
        </div>

        <span
          v-if="audioState === 'recording'"
          class="audio-countdown"
          data-testid="audio-countdown"
        >
          {{ remainingRecordingSeconds }}
        </span>
      </div>

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

