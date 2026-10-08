<script setup lang="ts">
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  computed,
  useTemplateRef,
  watch,
} from "vue";
import type { UnlistenFn } from "@tauri-apps/api/event";

import {

  getBackendSnapshot,
  listenToBackendLifecycle,
} from "./services/backendLifecycle";
import { loadUiConfig, type UiConfig } from "./uiConfig";
import { BACKEND_BASE_URL } from "./services/backend";

import {
  resizeAvatarWindow,
  setWindowInputRegions,
  type InputRegionRect,
} from "./services/inputShape";
import { exitAvalon } from "./services/appLifecycle";
import { showChatWindow } from "./services/chatWindow";
import { showConfirmationWindow } from "./services/confirmationWindow";
import { startAvatarWindowDrag } from "./services/windowDrag";
import { setAvatarWindowTitle } from "./services/windowTitle";
import {
  listenToAvatarRuntimeState,
  type AvatarRuntimeState,
} from "./services/avatarState";
import {
  listenToAudioCallChanged,
  publishAudioCallChanged,
} from "./services/audioCallEvents";
import { useTransientChat } from "./composables/useTransientChat";
import {
  completeAudioCallTurn,
  consumeAudioCallSpeech,
  endAudioCall,
  getAudioCallStatus,
  notifyTtsPlaybackEnded,
  startAudioCall,
  synthesizeSpeech,
  getPendingAuthorizationRequests,
  getPendingWorkflowConfirmation,
} from "./services/backend";
import { requestRuntimeWarmUp } from "./services/runtimeWarmup";
import { eventBroker } from "./services/eventBroker";

const uiConfig = ref<UiConfig>();

const AVATAR_DRAG_THRESHOLD_PX = 5;
const AVATAR_MIN_PERCENT = 50;
const AVATAR_MAX_PERCENT = 150;
const AVATAR_SCALE_STEP_PERCENT = 10;
const AVATAR_WINDOW_MIN_WIDTH_PX = 320;
const AVATAR_WINDOW_PADDING_PX = 48;

const backendStatus = ref("initializing");
const backendLogs = ref<string[]>([]);
const avatarScalePercent = ref(100);
const avatarRuntimeState = ref<AvatarRuntimeState>({ state: "standard", backendPending: false });
const animationFrame = ref(0);
const pendingPermissionCount = ref(0);
let permissionEvents: EventSource | undefined;
let workflowConfirmationEvents: EventSource | undefined;
const avatarStage = useTemplateRef<HTMLDivElement>("avatarStage");
const avatarRegion = useTemplateRef<HTMLDivElement>("avatarRegion");
const avatarImage = useTemplateRef<HTMLImageElement>("avatarImage");
const permissionsButton = useTemplateRef<HTMLButtonElement>("permissionsButton");
const audioButton = useTemplateRef<HTMLButtonElement>("audioButton");
const exitButton = useTemplateRef<HTMLButtonElement>("exitButton");

let avatarPointerStart: { x: number; y: number } | undefined;
let avatarLoaded = false;
let avatarSyncRunning = false;
let avatarSyncPending = false;
let uiConfigLoading = false;
let unlisten: UnlistenFn | undefined;
let unlistenAvatarState: UnlistenFn | undefined;
let unlistenAudioCall: UnlistenFn | undefined;
let animationTimer: number | undefined;
let isUnmounted = false;
let audioStatusSyncPromise: Promise<void> | undefined;
let audioStatusSyncPending = false;
let audioStatusAbortController: AbortController | undefined;
let dialogGreetingAudio: HTMLAudioElement | undefined;
let dialogGreetingCompletion: (() => void) | undefined;
let dialogTtsAudio: HTMLAudioElement | undefined;
let dialogTtsUrl: string | undefined;
let dialogTtsPlaybackId: string | undefined;
let dialogTtsCompletion: (() => void) | undefined;

const {
  messages: dialogMessages,
  errorMessage: dialogError,
  selectChat,
  sendDialogAudio,
  abortDialogTurn,
} = useTransientChat();
const isDialogActive = ref(false);
const isDialogSpeaking = ref(false);
const isDialogThinking = ref(false);

const activeAnimation = computed(() => uiConfig.value?.avatar.animations.find(
  (animation) => animation.key === avatarRuntimeState.value.state,
));

const avatarUrl = computed(() => activeAnimation.value?.spriteSetUrl
  ?? uiConfig.value?.avatar.standard.url ?? "");

const activeSprite = computed(() => {
  const sprites = activeAnimation.value?.sprites;
  return sprites?.[animationFrame.value % sprites.length];
});

const avatarRegionStyle = computed(() => {
  const sprite = activeSprite.value;
  if (!sprite) return { width: `${24 * avatarScalePercent.value / 100}rem` };
  const scale = avatarScalePercent.value / 100;
  return {
    width: `${sprite.width * scale}px`,
    height: `${sprite.height * scale}px`,
    overflow: "hidden",
  };
});

const avatarImageStyle = computed(() => {
  const sprite = activeSprite.value;
  if (!sprite) return {};
  const scale = avatarScalePercent.value / 100;
  return {
    // Override the generic responsive avatar rule.  A sprite sheet must keep
    // its intrinsic dimensions so the translated crop exposes one region.
    width: "auto",
    height: "auto",
    maxWidth: "none",
    transform: `scale(${scale}) translate(${-sprite.x}px, ${-sprite.y}px)`,
    transformOrigin: "top left",
  };
});

function resetAnimation() {
  animationFrame.value = 0;
  if (animationTimer !== undefined) window.clearInterval(animationTimer);
  const frameCount = activeAnimation.value?.sprites.length ?? 0;
  animationTimer = frameCount > 0
    ? window.setInterval(() => { animationFrame.value = (animationFrame.value + 1) % frameCount; }, 1000)
    : undefined;
}

watch(() => avatarRuntimeState.value.state, resetAnimation, { immediate: true });
watch(animationFrame, () => {
  if (avatarLoaded) requestAvatarSync();
});

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

  if (window.innerWidth === width && window.innerHeight === height) {
    return false;
  }

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

  try {
    const response = await fetch(`${BACKEND_BASE_URL}/api/v1/ui/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ avatarZoom: nextScale / 100 }),
    });

    if (!response.ok) {
      throw new Error(`Failed to persist avatar zoom: ${response.status}`);
    }
  } catch (error) {
    console.error("[ui-settings] failed to persist avatar zoom", error);
  }
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
    if (uiConfig.value.avatarZoom !== undefined) {
      avatarScalePercent.value = Math.round(uiConfig.value.avatarZoom * 100);
    }
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

function stopDialogGreeting() {
  const complete = dialogGreetingCompletion;
  dialogGreetingCompletion = undefined;
  complete?.();
  dialogGreetingAudio?.pause();
  dialogGreetingAudio = undefined;
}

async function playDialogGreeting() {
  const greetingUrl = uiConfig.value?.avatar.greetingAudioUrl;
  if (!greetingUrl) {
    console.error("[avatar-call] greeting audio URL unavailable");
    return;
  }

  const audio = new Audio(greetingUrl);
  dialogGreetingAudio = audio;

  try {
    await new Promise<void>((resolve, reject) => {
      let settled = false;

      const finish = () => {
        if (settled) return;
        settled = true;
        dialogGreetingCompletion = undefined;
        resolve();
      };

      dialogGreetingCompletion = finish;
      audio.onended = finish;
      audio.onerror = () => {
        if (settled) return;
        settled = true;
        dialogGreetingCompletion = undefined;
        reject(
          audio.error
          ?? new Error("Avatar greeting audio playback failed"),
        );
      };

      void audio.play().catch((error) => {
        if (settled) return;
        settled = true;
        dialogGreetingCompletion = undefined;
        reject(error);
      });
    });
  } catch (error) {
    console.error("[avatar-call] greeting audio playback failed", error);
  } finally {
    if (dialogGreetingAudio === audio) {
      audio.pause();
      dialogGreetingAudio = undefined;
    }
    dialogGreetingCompletion = undefined;
  }
}

function stopDialogTts() {
  const complete = dialogTtsCompletion;
  dialogTtsCompletion = undefined;
  complete?.();
  dialogTtsAudio?.pause();
  dialogTtsAudio = undefined;
  if (dialogTtsUrl) URL.revokeObjectURL(dialogTtsUrl);
  dialogTtsUrl = undefined;
  isDialogSpeaking.value = false;
  if (dialogTtsPlaybackId) {
    void notifyTtsPlaybackEnded(dialogTtsPlaybackId).catch((error) =>
      console.error("[avatar-call] failed to notify TTS playback end", error),
    );
    dialogTtsPlaybackId = undefined;
  }
}

async function speakDialogResponse(index: number) {
  const text = dialogMessages.value[index]?.content.trim() ?? "";
  if (!text) return;
  isDialogThinking.value = true;
  try {
    const tts = await synthesizeSpeech(text, new AbortController().signal);
    dialogTtsPlaybackId = tts.playbackId;
    const blob = await tts.response.blob();
    dialogTtsUrl = URL.createObjectURL(blob);
    const audio = new Audio(dialogTtsUrl);
    dialogTtsAudio = audio;
    isDialogThinking.value = false;
    isDialogSpeaking.value = true;
    await new Promise<void>((resolve, reject) => {
      dialogTtsCompletion = resolve;
      audio.onended = () => {
        dialogTtsCompletion = undefined;
        resolve();
      };
      audio.onerror = () => {
        dialogTtsCompletion = undefined;
        reject(audio.error);
      };
      void audio.play().catch(reject);
    });
  } catch (error) {
    console.error("[avatar-call] TTS playback failed", error);
  } finally {
    stopDialogTts();
    isDialogThinking.value = false;
  }
}

async function runAvatarDialogLoop() {
  while (isDialogActive.value) {
    const result = await sendDialogAudio();
    if (!isDialogActive.value) return;
    if (!result) {
      if (dialogError.value) {
        await endAvatarDialog();
        return;
      }
      continue;
    }
    await speakDialogResponse(result.assistantIndex);
    try {
      await completeAudioCallTurn();
      await publishAudioCallChanged();
    } catch (error) {
      console.error("[avatar-call] failed to complete call turn", error);
    }
  }
}

async function startAvatarDialog(alreadyStarted = false, chatId?: number) {
  if (isDialogActive.value) return;

  try {
    const runtimeReady = requestRuntimeWarmUp();

    if (!alreadyStarted) {
      await startAudioCall();
    }

    if (chatId !== undefined) await selectChat(chatId);

    isDialogActive.value = true;
    dialogError.value = undefined;

    if (!alreadyStarted) {
      await publishAudioCallChanged();
    }

    if (await runtimeReady) {
      if (!isDialogActive.value) return;
      await playDialogGreeting();
    }

    if (!isDialogActive.value) return;
    void runAvatarDialogLoop();
  } catch (error) {
    console.error("[avatar-call] failed to start", error);
  }
}

function closePendingEventStreams() {
  permissionEvents?.close();
  permissionEvents = undefined;
  workflowConfirmationEvents?.close();
  workflowConfirmationEvents = undefined;
}

function openPendingEventStreams() {
  if (backendStatus.value !== "ready" || typeof EventSource === "undefined") {
    return;
  }

  if (!permissionEvents) {
    permissionEvents = new EventSource(
      "http://127.0.0.1:8095/api/v1/authorization-requests/events",
    );
    permissionEvents.addEventListener(
      "authorization_requests_changed",
      () => { void refreshPendingPermissionCount(); },
    );
  }

  if (!workflowConfirmationEvents) {
    workflowConfirmationEvents = new EventSource(
      "http://127.0.0.1:8095/api/v1/workflow-executions/confirmations/events",
    );
    workflowConfirmationEvents.addEventListener(
      "workflow_confirmations_changed",
      () => { void refreshPendingPermissionCount(); },
    );
  }
}

async function syncExternalAvatarCall(signal: AbortSignal) {
  try {
    const status = await getAudioCallStatus(signal);

    if (
      isUnmounted
      || signal.aborted
      || backendStatus.value !== "ready"
    ) {
      return;
    }

    if (status.active && !isDialogActive.value) {
      await startAvatarDialog(true, status.chat_id ?? undefined);
      if (
        isUnmounted
        || signal.aborted
        || backendStatus.value !== "ready"
      ) {
        return;
      }
    }

    if (
      status.active
      && status.pending_speech
      && !isDialogSpeaking.value
      && !isDialogThinking.value
    ) {
      const text = await consumeAudioCallSpeech(signal);
      if (
        isUnmounted
        || signal.aborted
        || backendStatus.value !== "ready"
      ) {
        return;
      }
      if (text) {
        dialogMessages.value.push({ role: "assistant", content: text });
        await speakDialogResponse(dialogMessages.value.length - 1);
        await completeAudioCallTurn();
        await publishAudioCallChanged();
      }
    }
  } catch (error) {
    if (signal.aborted) {
      return;
    }
    console.error("[avatar-call] failed to sync status", error);
  }
}

function requestExternalAvatarCallSync(): Promise<void> {
  if (
    isUnmounted
    || backendStatus.value !== "ready"
    || !uiConfig.value
  ) {
    return Promise.resolve();
  }

  audioStatusSyncPending = true;
  if (!audioStatusSyncPromise) {
    audioStatusSyncPromise = (async () => {
      while (
        audioStatusSyncPending
        && !isUnmounted
        && backendStatus.value === "ready"
        && uiConfig.value
      ) {
        audioStatusSyncPending = false;
        const controller = new AbortController();
        audioStatusAbortController = controller;
        await syncExternalAvatarCall(controller.signal);
      }
    })().finally(() => {
      audioStatusSyncPromise = undefined;
      audioStatusAbortController = undefined;
    });
  }

  return audioStatusSyncPromise;
}

function handleAvatarFocus() {
  void requestExternalAvatarCallSync();
}

function abortAudioStatusSync() {
  audioStatusSyncPending = false;
  audioStatusAbortController?.abort();
}

async function endAvatarDialog() {
  if (!isDialogActive.value) return;
  isDialogActive.value = false;
  abortDialogTurn();
  stopDialogGreeting();
  stopDialogTts();
  try {
    await endAudioCall();
    await publishAudioCallChanged();
  } catch (error) {
    console.error("[avatar-call] failed to end", error);
  }
}

function handleDialogButton() {
  if (!isDialogActive.value) {
    void startAvatarDialog();
  } else if (isDialogSpeaking.value) {
    stopDialogTts();
  } else {
    void endAvatarDialog();
  }
}

watch([isDialogActive, isDialogSpeaking, isDialogThinking], () => {
  avatarRuntimeState.value = {
    state: isDialogSpeaking.value ? "speaking" : isDialogActive.value ? (
      isDialogThinking.value ? "thinking" : "listening"
    ) : "standard",
    backendPending: isDialogThinking.value,
  };
});

async function applyAvatarInputShape() {
  const image = avatarImage.value;
  const region = avatarRegion.value;
  if (!image || !region) {
    return;
  }

  const bounds = activeSprite.value
    ? region.getBoundingClientRect()
    : image.getBoundingClientRect();
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

  const sprite = activeSprite.value;
  if (sprite) {
    context.drawImage(
      image,
      sprite.x,
      sprite.y,
      sprite.width,
      sprite.height,
      0,
      0,
      renderedWidth,
      renderedHeight,
    );
  } else {
    context.drawImage(image, 0, 0, renderedWidth, renderedHeight);
  }
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
    permissionsButton.value,
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

async function refreshPendingPermissionCount() {
  if (!uiConfig.value) return;

  try {
    const [requests, confirmation] = await Promise.all([
      getPendingAuthorizationRequests(), getPendingWorkflowConfirmation(),
    ]);
    pendingPermissionCount.value = requests.length + (confirmation === null ? 0 : 1);
  } catch (error) {
    console.error("[permissions] failed to refresh pending requests", error);
  }
}

async function openPermissions() {
  try { await showConfirmationWindow(); } catch (error) { console.error("[confirmations] failed to show window", error); }
}

async function handleExit() {
  try {
    await exitAvalon();
  } catch (error) {
    console.error("[app] failed to exit Avalon", error);
  }
}

onMounted(async () => {
  window.addEventListener("keydown", handleAvatarScaleKeydown);
  window.addEventListener("resize", handleAvatarWindowResize);
  window.addEventListener("focus", handleAvatarFocus);

  try {
    unlistenAudioCall = await listenToAudioCallChanged(() => {
      void requestExternalAvatarCallSync();
    });
  } catch (error) {
    console.error("[avatar-call] failed to subscribe to call changes", error);
  }

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

  try {
    unlistenAvatarState = await listenToAvatarRuntimeState((state) => {
      avatarRuntimeState.value = state;
    });
  } catch (error) {
    console.error("[avatar-state] failed to subscribe", error);
  }
});

watch(
  backendStatus,
  async (status) => {
    if (status !== "ready") {
      eventBroker.stop();
      closePendingEventStreams();
      abortAudioStatusSync();
      return;
    }

    eventBroker.start();
    openPendingEventStreams();

    if (!uiConfig.value) {
      await initializeUiConfig();
    }

    if (!uiConfig.value || backendStatus.value !== "ready") {
      return;
    }

    await refreshPendingPermissionCount();
    await requestExternalAvatarCallSync();

    if (avatarLoaded) {
      requestAvatarSync();
    }
  },
  { immediate: true },
);


onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleAvatarScaleKeydown);
  window.removeEventListener("resize", handleAvatarWindowResize);
  window.removeEventListener("focus", handleAvatarFocus);
  isUnmounted = true;
  abortAudioStatusSync();
  if (isDialogActive.value) void endAvatarDialog();
  unlisten?.();
  unlistenAvatarState?.();
  unlistenAudioCall?.();
  eventBroker.stop();
  closePendingEventStreams();
  if (animationTimer !== undefined) window.clearInterval(animationTimer);
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
        <span>AVALON // LOCAL COMPANION</span>
        <span data-testid="backend-status">{{ backendStatus }}</span>
      </header>

      <div class="startup-log" data-testid="startup-log">
        <p v-for="(line, index) in backendLogs" :key="index">
          <span class="prompt">&gt;</span> {{ line }}
        </p>
        <p v-if="backendLogs.length === 0">
          <span class="prompt">&gt;</span> Initializing Avalon …
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
        v-if="avatarRuntimeState.backendPending"
        class="avatar-balloon"
        data-testid="avatar-pending-balloon"
      >
        <span class="avatar-spinner" aria-hidden="true" />
        <span>Denke nach …</span>
      </div>

      <div
        ref="avatarRegion"
        class="avatar-region"
        :style="avatarRegionStyle"
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
          :src="avatarUrl"
          :alt="uiConfig.name"
          :style="avatarImageStyle"
          :data-avatar-state="avatarRuntimeState.state"
          :data-avatar-frame="animationFrame"
          crossorigin="anonymous"
          data-testid="avatar"
          @load="initializeAvatar"
        />
      </div>

      <div
        class="audio-control"
        :style="{ width: `${24 * avatarScalePercent / 100}rem` }"
      >
        <div class="avatar-control-buttons">
          <button ref="permissionsButton" class="audio-button permission-button" type="button" data-testid="permissions-button" aria-label="Permissions" title="Permissions" @click="openPermissions">
            <svg class="audio-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l8 3v6c0 5-3.4 9.4-8 11-4.6-1.6-8-6-8-11V5l8-3z"/><path d="M8 12h8M10 9v6M14 9v6"/></svg>
            <span v-if="pendingPermissionCount > 0" class="permission-badge">!</span>
          </button>
          <button
            ref="audioButton"
            class="audio-button"
            type="button"
            data-testid="avatar-call"
            :aria-label="!isDialogActive ? 'Dialog starten' : isDialogSpeaking ? 'Sprachausgabe stoppen' : 'Dialog beenden'"
            :title="!isDialogActive ? 'Dialog starten' : isDialogSpeaking ? 'Sprachausgabe stoppen' : 'Dialog beenden'"
            @click="handleDialogButton"
          >
            <svg
              class="audio-icon"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <rect v-if="isDialogSpeaking" x="7" y="7" width="10" height="10" />
              <path v-else d="M7.4 3.5l2.2 4.1-1.7 1.7a15 15 0 0 0 6.8 6.8l1.7-1.7 4.1 2.2c.5.3.7.8.5 1.3l-.9 2.8c-.2.5-.7.8-1.2.8C9.8 21.5 2.5 14.2 2.5 5.1c0-.5.3-1 .8-1.2l2.8-.9c.5-.2 1 .1 1.3.5z" />
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
