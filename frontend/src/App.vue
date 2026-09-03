<script setup lang="ts">
import {
  onBeforeUnmount,
  onMounted,
  ref,
  useTemplateRef,
} from "vue";
import type { UnlistenFn } from "@tauri-apps/api/event";

import friedaStandard from "./assets/avatars/frieda2/standard.png";
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

type AudioState = "idle" | "recording";

const MAX_AUDIO_SECONDS = 30;
const AVATAR_DRAG_THRESHOLD_PX = 5;

const backendStatus = ref("initializing");
const backendLogs = ref<string[]>([]);
const audioState = ref<AudioState>("idle");
const remainingRecordingSeconds = ref(MAX_AUDIO_SECONDS);
const avatarImage = useTemplateRef<HTMLImageElement>("avatarImage");
const audioButton = useTemplateRef<HTMLButtonElement>("audioButton");

let avatarPointerStart: { x: number; y: number } | undefined;
let recordingTimer: number | undefined;
let audioPointerHeld = false;
let unlisten: UnlistenFn | undefined;

function addLog(message: string) {
  backendLogs.value.push(message);
}

function initializeAvatar() {
  void applyAvatarInputShape();
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

  const button = audioButton.value;
  if (button) {
    const buttonBounds = button.getBoundingClientRect();

    if (buttonBounds.width > 0 && buttonBounds.height > 0) {
      rectangles.push({
        x: Math.round(buttonBounds.left * scale),
        y: Math.round(buttonBounds.top * scale),
        width: Math.max(1, Math.round(buttonBounds.width * scale)),
        height: Math.max(1, Math.round(buttonBounds.height * scale)),
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
  audioPointerHeld = false;
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
      class="avatar-region"
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
        :src="friedaStandard"
        alt="Frieda"
        data-testid="avatar"
        @load="initializeAvatar"
      />
    </div>

    <div class="audio-control">
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
      <span
        v-if="audioState === 'recording'"
        class="audio-countdown"
        data-testid="audio-countdown"
      >
        {{ remainingRecordingSeconds }}
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

