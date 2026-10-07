<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";


import MarkdownComposer from "./components/MarkdownComposer.vue";
import MarkdownMessage from "./components/MarkdownMessage.vue";
import WorkflowDecorator from "./components/WorkflowDecorator.vue";

import watermarkUrl from "./assets/watermark.png";

import { useTransientChat } from "./composables/useTransientChat";
import { loadUiConfig, type UiConfig } from "./uiConfig";

import {
  abortAudioRecording as abortBackendAudioRecording,
  notifyTtsPlaybackEnded,
  startAudioRecording as startBackendAudioRecording,
  synthesizeSpeech,
  startAudioCall,
  getAudioCallStatus,
  BACKEND_BASE_URL,
  type Attachment,
  listenToWorkflowExecutions,
} from "./services/backend";
import {
  exportChatToMarkdown,
  getChatMarkdown,
} from "./services/chatExport";
import { showConfirmationWindowForChat } from "./services/confirmationWindow";
import { formatMessageTime } from "./services/messageTime";
import { requestRuntimeWarmUp } from "./services/runtimeWarmup";
import {
  publishAvatarRuntimeState,
  type AvatarVisualState,
} from "./services/avatarState";
import {
  listenToAudioCallChanged,
  publishAudioCallChanged,
} from "./services/audioCallEvents";
import { boundCallChatToSelect } from "./services/audioCallBinding";
import { setChatWindowTitle } from "./services/windowTitle";


const uiConfig = ref<UiConfig>();

const {

  messages,
  input,
  isGenerating,
  isDialogResponding,
  isDialogProcessing,
  backendPending,
  errorMessage,
  chatSummaries,
  selectedChatId,
  isChatCompressionFailed,
  refreshChats,
  refreshSelectedChat,
  selectChat,
  newChat,
  renameChat,
  setChatPinned,
  deleteChat,
  isChatRunning,
  send,

  sendAudio,
  sendDialogAudio,
  abortDialogTurn,
  stop,
} = useTransientChat();

watch(input, (value) => {
  if (value.length > 0) {
    requestRuntimeWarmUp();
  }
});

const messagesElement = ref<HTMLElement>();
const isComposerExpanded = ref(false);
const isRecording = ref(false);
const remainingRecordingSeconds = ref(30);
const isTtsSynthesizing = ref(false);
const isDialogActive = ref(false);
const isDialogTtsActive = ref(false);
const isTtsPlaying = ref(false);
const skipDialogTts = ref(false);
const callTurnActive = ref(false);
const boundCallActive = ref(false);
const selectedAttachments = ref<Attachment[] | undefined>();
let unlistenAudioCall: (() => void) | undefined;
let unlistenWorkflowExecutions: (() => void) | undefined;

const isBoundCallTurnActive = computed(() => callTurnActive.value);

function openAttachments(attachments: Attachment[]) {
  selectedAttachments.value = attachments;
}

function closeAttachments() {
  selectedAttachments.value = undefined;
}

async function refreshCallStatus() {
  try {
    const status = await getAudioCallStatus();
    const chatIdToSelect = boundCallChatToSelect(
      status,
      selectedChatId.value,
    );
    if (chatIdToSelect !== undefined) {
      await selectChat(chatIdToSelect);
    }

    const wasBoundCall = boundCallActive.value;
    const isBoundCall = status.active
      && status.chat_id === selectedChatId.value;

    boundCallActive.value = isBoundCall;
    callTurnActive.value = isBoundCall && status.turn_active;

    if (isBoundCall || wasBoundCall) {
      await refreshSelectedChat();
    }
  } catch (error) {
    console.error("[audio-call] failed to sync status", error);
  }

}

const isDialogRespondingOrSpeaking = computed(
  () => isDialogResponding.value || isDialogTtsActive.value,
);

const isDialogSpeaking = computed(
  () => isDialogActive.value && isTtsPlaying.value,
);

const avatarPending = computed(
  () => backendPending.value || isTtsSynthesizing.value,
);

const avatarVisualState = computed<AvatarVisualState>(() => {
  if (isRecording.value) return "listening";
  if (isTtsPlaying.value) return "speaking";
  // The audio does not speak until HTMLAudioElement.play() has resolved.
  // Fetching and decoding the WAV remains backend work, thus "thinking".
  if (isTtsSynthesizing.value) return "thinking";
  if (
    isDialogActive.value
    && !isDialogProcessing.value
    && !isDialogResponding.value
  ) return "listening";
  if (backendPending.value) return "thinking";
  if (isDialogActive.value) return "listening";
  return "standard";
});

watch(
  [avatarVisualState, avatarPending],
  ([state, pending]) => {
    void publishAvatarRuntimeState({ state, backendPending: pending })
      .catch((error) => {
        console.error("[avatar-state] failed to publish runtime state", error);
      });
  },
  { immediate: true },
);

const pinnedChats = computed(
  () => chatSummaries.value.filter((chat) => chat.pinned),
);
const historyChats = computed(
  () => chatSummaries.value.filter((chat) => !chat.pinned),
);

const chatWindowTitle = computed(() => {
  if (selectedChatId.value === undefined) {
    return "New Chat - Avalon";
  }

  const chat = chatSummaries.value.find(
    (summary) => summary.id === selectedChatId.value,
  );

  return `${chat?.title ?? "New Chat"} - Avalon`;
});

watch(
  chatWindowTitle,
  (title) => {
    void setChatWindowTitle(title).catch((error) => {
      console.error("[window-title] failed to update chat window title", error);
    });
  },
  { immediate: true },
);

const openChatMenuId = ref<number>();
const openExportMenuId = ref<number>();
const renameChatId = ref<number>();
const renameTitle = ref("");
const renameValidationError = ref<string>();
const deleteChatId = ref<number>();

let recordingTimer: number | undefined;


let recordingStartPending = false;
let recordingReleaseAction: "finish" | "abort" | undefined;

function clearRecordingTimer() {
  if (recordingTimer !== undefined) {
    window.clearInterval(recordingTimer);
    recordingTimer = undefined;
  }
}

function removeRecordingListeners() {
  window.removeEventListener("pointerup", finishAudioRecording);
  window.removeEventListener("pointercancel", abortAudioRecording);
}

function resetRecordingState() {
  clearRecordingTimer();
  removeRecordingListeners();
  isRecording.value = false;
  remainingRecordingSeconds.value = 30;
}

async function startAudioRecording(event: PointerEvent) {
  if (
    event.button !== 0
    || isGenerating.value
    || isChatCompressionFailed.value
    || isRecording.value
    || recordingStartPending
  ) {
    return;
  }

  event.preventDefault();
  errorMessage.value = undefined;
  recordingStartPending = true;
  recordingReleaseAction = undefined;
  window.addEventListener("pointerup", finishAudioRecording);
  window.addEventListener("pointercancel", abortAudioRecording);

  try {
    await startBackendAudioRecording();
  } catch (error) {
    console.error("[audio] failed to start recording", error);
    recordingStartPending = false;
    recordingReleaseAction = undefined;
    removeRecordingListeners();
    errorMessage.value = "Audioaufnahme konnte nicht gestartet werden.";
    return;
  }

  recordingStartPending = false;

  if (recordingReleaseAction === "finish") {
    recordingReleaseAction = undefined;
    removeRecordingListeners();
    await sendAudio();
    return;
  }

  if (recordingReleaseAction === "abort") {
    recordingReleaseAction = undefined;
    removeRecordingListeners();
    try {
      await abortBackendAudioRecording();
    } catch (error) {
      console.error("[audio] failed to abort recording", error);
      errorMessage.value = "Audioaufnahme konnte nicht verworfen werden.";
    }
    return;
  }

  isRecording.value = true;
  recordingTimer = window.setInterval(() => {
    remainingRecordingSeconds.value -= 1;
    if (remainingRecordingSeconds.value <= 0) {
      void abortAudioRecording();
    }
  }, 1000);
}

async function finishAudioRecording() {
  if (recordingStartPending) {
    recordingReleaseAction = "finish";
    return;
  }
  if (!isRecording.value) {
    return;
  }
  resetRecordingState();
  await sendAudio();
}

async function abortAudioRecording() {
  if (recordingStartPending) {
    recordingReleaseAction = "abort";
    return;
  }
  if (!isRecording.value) {
    return;
  }
  resetRecordingState();
  try {
    await abortBackendAudioRecording();
  } catch (error) {
    console.error("[audio] failed to abort recording", error);
    errorMessage.value = "Audioaufnahme konnte nicht verworfen werden.";
  }
}

function closeChatMenu() {
  openChatMenuId.value = undefined;
  openExportMenuId.value = undefined;
}

function toggleChatMenu(chatId: number) {
  const isOpen = openChatMenuId.value === chatId;
  openChatMenuId.value = isOpen ? undefined : chatId;
  openExportMenuId.value = undefined;
}

function toggleExportMenu(chatId: number) {
  openExportMenuId.value =
    openExportMenuId.value === chatId ? undefined : chatId;
}

function openRenameDialog(chatId: number) {
  const chat = chatSummaries.value.find(
    (summary) => summary.id === chatId,
  );
  if (!chat) {
    return;
  }

  closeChatMenu();
  renameChatId.value = chatId;
  renameTitle.value = chat.title;
  renameValidationError.value = undefined;
}

function closeRenameDialog() {
  renameChatId.value = undefined;
  renameTitle.value = "";
  renameValidationError.value = undefined;
}

async function confirmRename() {
  const chatId = renameChatId.value;
  if (chatId === undefined) {
    return;
  }

  const title = renameTitle.value.trim();
  if (title.length === 0) {
    renameValidationError.value =
      "Der Chatname darf nicht leer sein.";
    return;
  }

  if (await renameChat(chatId, title)) {
    closeRenameDialog();
  }
}

function openDeleteDialog(chatId: number) {
  closeChatMenu();
  deleteChatId.value = chatId;
}

function closeDeleteDialog() {
  deleteChatId.value = undefined;
}

async function confirmDelete() {
  const chatId = deleteChatId.value;
  if (chatId === undefined) {
    return;
  }

  if (await deleteChat(chatId)) {
    closeDeleteDialog();
  }
}

function deleteChatTitle() {
  if (deleteChatId.value === undefined) {
    return "";
  }

  return chatSummaries.value.find(
    (chat) => chat.id === deleteChatId.value,
  )?.title ?? "";
}

async function togglePinned(
  chatId: number,
  pinned: boolean,
) {
  closeChatMenu();
  await setChatPinned(chatId, !pinned);
}

async function exportChat(chatId: number) {
  closeChatMenu();

  try {
    if (!uiConfig.value) {
      throw new Error("UI configuration has not been loaded.");
    }

    await exportChatToMarkdown(chatId, uiConfig.value.name);
  } catch (error) {

    console.error("[chat-export] failed to export chat", error);
    errorMessage.value = "Chat konnte nicht exportiert werden.";
  }
}

async function copyChatMarkdownToClipboard(chatId: number) {
  closeChatMenu();

  try {
    if (!uiConfig.value) {
      throw new Error("UI configuration has not been loaded.");
    }

    if (!navigator.clipboard?.writeText) {
      throw new Error("Clipboard API is not available.");
    }

    const markdown = await getChatMarkdown(
      chatId,
      uiConfig.value.name,
    );
    await navigator.clipboard.writeText(markdown);
  } catch (error) {
    console.error(
      "[chat-export] failed to copy chat to clipboard",
      error,
    );
    errorMessage.value = "Chat konnte nicht exportiert werden.";
  }
}

async function openPermissionsDialog(chatId: number) {
  closeChatMenu();
  try {
    const chat = chatSummaries.value.find((summary) => summary.id === chatId);
    if (chat === undefined) {
      throw new Error("Chat is missing from the chat list");
    }
    await showConfirmationWindowForChat(chatId, chat.agent_id);
  } catch (error) {
    console.error("[permissions] failed to show chat permissions", error);
    errorMessage.value = "Permissions konnten nicht geöffnet werden.";
  }
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") {
    return;
  }

  if (renameChatId.value !== undefined) {
    closeRenameDialog();
    return;
  }

  if (deleteChatId.value !== undefined) {
    closeDeleteDialog();
    return;
  }

  closeChatMenu();
}

async function handleWindowFocus() {
  await refreshChats();
  await refreshCallStatus();
}

onMounted(async () => {
  document.addEventListener("pointerdown", closeChatMenu);
  window.addEventListener("keydown", handleWindowKeydown);
  window.addEventListener("focus", handleWindowFocus);

  try {
    uiConfig.value = await loadUiConfig();
  } catch (error) {
    console.error("[startup] failed to load UI config", error);
    errorMessage.value = `UI-Konfiguration konnte nicht geladen werden: ${
      error instanceof Error ? error.message : String(error)
    }`;
    return;
  }

  await refreshChats(true, 20);
  await refreshCallStatus();

  try {
    unlistenAudioCall = await listenToAudioCallChanged(() => {
      void refreshCallStatus();
    });
  } catch (error) {
    console.error("[audio-call] failed to subscribe to call changes", error);
  }

  unlistenWorkflowExecutions = listenToWorkflowExecutions(() => {
    void refreshSelectedChat();
  });
});


onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", closeChatMenu);
  window.removeEventListener("keydown", handleWindowKeydown);
  window.removeEventListener("focus", handleWindowFocus);

  if (isRecording.value) {
    void abortBackendAudioRecording().catch((error) => {
      console.error("[audio] failed to abort recording during cleanup", error);
    });
  }

  if (isDialogActive.value) {
    isDialogActive.value = false;
    abortDialogTurn();
  }

  replaceCurrentTts();
  resetRecordingState();
  unlistenAudioCall?.();
  unlistenWorkflowExecutions?.();
});



type MarkdownMessageInstance = {
  getRenderedHtml: () => string;
  getPlainText: () => string;
};

const messageRenderers = new Map<number, MarkdownMessageInstance>();

let ttsAbortController: AbortController | undefined;
let ttsAudio: HTMLAudioElement | undefined;
let ttsObjectUrl: string | undefined;
let ttsPlaybackId: string | undefined;
let ttsRequestToken = 0;
let ttsCompletionResolver: (() => void) | undefined;


function cleanupTtsAudio() {
  isTtsPlaying.value = false;

  if (ttsAudio) {
    ttsAudio.onended = null;
    ttsAudio.onerror = null;
    ttsAudio.pause();
    ttsAudio = undefined;
  }

  if (ttsObjectUrl) {
    URL.revokeObjectURL(ttsObjectUrl);
    ttsObjectUrl = undefined;
  }

  const resolve = ttsCompletionResolver;
  ttsCompletionResolver = undefined;
  resolve?.();
}

function replaceCurrentTts() {
  ttsRequestToken += 1;
  ttsAbortController?.abort();
  ttsAbortController = undefined;
  cleanupTtsAudio();

  if (ttsPlaybackId) {
    void notifyTtsPlaybackEnded(ttsPlaybackId).catch((error) => {
      console.error("[tts] failed to notify playback end", error);
    });
    ttsPlaybackId = undefined;
  }
}


async function readMessageAloud(index: number) {
  const text = messageRenderers.get(index)?.getPlainText().trim() ?? "";
  if (!text || isTtsSynthesizing.value) {
    return;
  }

  replaceCurrentTts();

  const requestToken = ttsRequestToken;
  const controller = new AbortController();
  ttsAbortController = controller;
  isTtsSynthesizing.value = true;
  errorMessage.value = undefined;

  let playbackId: string | undefined;

  try {
    const tts = await synthesizeSpeech(
      text,
      controller.signal,
    );

    if (requestToken !== ttsRequestToken) {
      return;
    }

    playbackId = tts.playbackId;
    ttsPlaybackId = tts.playbackId;

    // fetch() has received the HTTP response headers: synthesis is complete

    // and WAV transfer has begun.
    isTtsSynthesizing.value = false;

    const audioBlob = await tts.response.blob();

    if (requestToken !== ttsRequestToken) {
      return;
    }

    ttsObjectUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(ttsObjectUrl);
    ttsAudio = audio;

    const playbackCompleted = new Promise<void>((resolve) => {
      ttsCompletionResolver = resolve;
    });

    audio.onended = () => {
      if (requestToken !== ttsRequestToken) {
        return;
      }

      cleanupTtsAudio();
      ttsPlaybackId = undefined;
      void notifyTtsPlaybackEnded(tts.playbackId).catch((error) => {
        console.error("[tts] failed to notify playback end", error);
      });
    };

    audio.onerror = () => {

      if (requestToken !== ttsRequestToken) {
        return;
      }

      console.error("[tts] audio playback failed", audio.error);
      cleanupTtsAudio();
      ttsPlaybackId = undefined;
      errorMessage.value = "Vorlesen fehlgeschlagen.";
      void notifyTtsPlaybackEnded(tts.playbackId).catch((error) => {
        console.error("[tts] failed to notify playback end", error);
      });
    };


    await audio.play();
    isTtsPlaying.value = true;
    await playbackCompleted;
  } catch (error) {
    if (
      requestToken !== ttsRequestToken
      || (
        error instanceof DOMException
        && error.name === "AbortError"
      )
    ) {
      return;
    }

    console.error("[tts] read aloud failed", error);
    errorMessage.value = "Vorlesen fehlgeschlagen.";

    if (playbackId) {
      void notifyTtsPlaybackEnded(playbackId).catch((notifyError) => {
        console.error("[tts] failed to notify playback end", notifyError);
      });
    }
  } finally {
    if (requestToken === ttsRequestToken) {
      isTtsSynthesizing.value = false;
      ttsAbortController = undefined;
    }
  }
}

async function runDialogLoop() {
  while (isDialogActive.value) {
    skipDialogTts.value = false;

    const result = await sendDialogAudio();

    if (!isDialogActive.value) {
      return;
    }

    if (!result) {
      isDialogActive.value = false;
      return;
    }

    if (!skipDialogTts.value) {
      await nextTick();

      isDialogTtsActive.value = true;
      try {
        await readMessageAloud(result.assistantIndex);
      } finally {
        isDialogTtsActive.value = false;
      }
    }
  }
}

function startDialog() {
  if (
    isDialogActive.value
    || isRecording.value
    || recordingStartPending
    || isGenerating.value
    || isChatCompressionFailed.value
  ) {
    return;
  }

  errorMessage.value = undefined;
  isDialogActive.value = true;
  void runDialogLoop();
}

function endDialog() {
  if (!isDialogActive.value || isDialogSpeaking.value) {
    return;
  }

  isDialogActive.value = false;
  abortDialogTurn();
}

function stopDialogAudio() {
  if (!isDialogSpeaking.value) {
    return;
  }

  skipDialogTts.value = true;

  replaceCurrentTts();
}

function handleDialogButton() {
  if (
    selectedChatId.value === undefined
    || isChatCompressionFailed.value
  ) return;
  requestRuntimeWarmUp();
  void startAudioCall(selectedChatId.value)
    .then(async (status) => {
      boundCallActive.value = status.active
        && status.chat_id === selectedChatId.value;
      callTurnActive.value = boundCallActive.value && status.turn_active;
      await publishAudioCallChanged();
    })
    .catch((error) => {
      console.error("[audio-call] failed to delegate call to avatar", error);
      errorMessage.value = "Dialog konnte nicht gestartet werden.";
    });
}

const DEFAULT_SIDEBAR_WIDTH_PX = 280;
const MIN_SIDEBAR_WIDTH_PX = 220;
const MAX_SIDEBAR_WIDTH_RATIO = 0.45;

const sidebarWidth = ref(DEFAULT_SIDEBAR_WIDTH_PX);

function startSidebarResize(event: PointerEvent) {
  const startX = event.clientX;
  const startWidth = sidebarWidth.value;

  function handlePointerMove(moveEvent: PointerEvent) {
    const requestedWidth = startWidth + moveEvent.clientX - startX;
    const maxWidth = window.innerWidth * MAX_SIDEBAR_WIDTH_RATIO;

    sidebarWidth.value = Math.min(
      Math.max(requestedWidth, MIN_SIDEBAR_WIDTH_PX),
      maxWidth,
    );
  }

  function stopSidebarResize() {
    window.removeEventListener("pointermove", handlePointerMove);
    window.removeEventListener("pointerup", stopSidebarResize);
    window.removeEventListener("pointercancel", stopSidebarResize);
  }

  window.addEventListener("pointermove", handlePointerMove);
  window.addEventListener("pointerup", stopSidebarResize);
  window.addEventListener("pointercancel", stopSidebarResize);
}

watch(
  messages,
  async () => {
    await nextTick();

    const element = messagesElement.value;
    if (element) {
      element.scrollTop = element.scrollHeight;
    }
  },
  { deep: true },
);

function setMessageRenderer(index: number, instance: unknown) {
  const renderer = instance as MarkdownMessageInstance | null;

  if (renderer) {
    messageRenderers.set(index, renderer);
    return;
  }


  messageRenderers.delete(index);
}

async function copyMessage(index: number, content: string) {
  const renderedHtml = messageRenderers.get(index)?.getRenderedHtml() ?? "";
  const clipboard = navigator.clipboard;

  if (
    clipboard?.write
    && typeof ClipboardItem !== "undefined"
  ) {
    const item = new ClipboardItem({
      "text/plain": new Blob(
        [content],
        { type: "text/plain" },
      ),
      "text/html": new Blob(
        [renderedHtml],
        { type: "text/html" },
      ),
    });

    await clipboard.write([item]);
    return;
  }

  if (clipboard?.writeText) {
    await clipboard.writeText(content);
  }
}

function toggleComposerExpanded() {
  isComposerExpanded.value = !isComposerExpanded.value;
}

function sendComposerInput() {
  void send()
    .then(async () => {
      if (boundCallActive.value) {
        await publishAudioCallChanged();
      }
    })
    .catch((error) => {
      console.error("[audio-call] failed to publish chat response", error);
    });
  isComposerExpanded.value = false;
}


function handleInputKeydown(event: KeyboardEvent) {
  if (
    event.key !== "Enter"
    || isGenerating.value
    || isChatCompressionFailed.value
  ) {
    return;
  }

  if (event.ctrlKey) {
    event.preventDefault();
    sendComposerInput();
    return;
  }

  if (
    event.shiftKey
    || input.value.includes("\n")
  ) {
    return;
  }

  event.preventDefault();
  sendComposerInput();
}


</script>

<template>
  <main class="chat-window">
    <aside
      class="sidebar"
      data-testid="chat-sidebar"
      :style="{ width: `${sidebarWidth}px` }"
    >
      <header class="sidebar-header">
        <h1>Avalon</h1>
      </header>

      <button
        class="new-chat-button icon-button"
        type="button"
        data-testid="new-chat"
        aria-label="Neuer Chat"
        title="Neuer Chat"
        @click="newChat"
      >
        <svg
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            d="M12 5v14M5 12h14"
          />
        </svg>
      </button>

      <section
        class="chat-list-section chat-list-section--pinned"
        data-testid="pinned-chats"
      >

        <h2 class="chat-list-heading">
          Pinned Chats
        </h2>

        <nav
          class="chat-history"
          aria-label="Angeheftete Chats"
        >
          <div
            v-for="chat in pinnedChats"
            :key="chat.id"
            class="chat-history-item"
            :class="{
              'chat-history-item--selected': selectedChatId === chat.id,
            }"
            :data-testid="`chat-${chat.id}`"
            @click="selectChat(chat.id)"
          >
            <span
              class="chat-history-title"
              :title="chat.agent_name ? `${chat.title}\nAgent: ${chat.agent_name}` : chat.title"
            >
              {{ chat.agent_name ? `🤖 ${chat.title}` : chat.title }}
            </span>

            <span
              v-if="isChatRunning(chat.id)"
              class="chat-running-indicator"
              data-testid="chat-running"
              aria-label="Antwort läuft"
              title="Antwort läuft"
            />

            <div
              class="chat-menu-container"
              @click.stop
              @pointerdown.stop
            >
              <button
                class="chat-menu-button"
                type="button"
                :data-testid="`chat-menu-${chat.id}`"
                aria-label="Chat-Menü"
                title="Chat-Menü"
                @click="toggleChatMenu(chat.id)"
              >
                ⋮
              </button>

              <div
                v-if="openChatMenuId === chat.id"
                class="chat-menu"
                :data-testid="`chat-menu-popup-${chat.id}`"
                role="menu"
              >
                <button
                  class="chat-menu-item"
                  type="button"
                  role="menuitemcheckbox"
                  :aria-checked="chat.pinned"
                  :data-testid="`chat-pin-${chat.id}`"
                  @click="togglePinned(chat.id, chat.pinned)"
                >
                  Pin
                  <span class="chat-menu-check">
                    {{ chat.pinned ? "✓" : "" }}
                  </span>
                </button>
                <button
                  class="chat-menu-item"
                  type="button"
                  role="menuitem"
                  :data-testid="`chat-rename-${chat.id}`"
                  @click="openRenameDialog(chat.id)"
                >
                  Rename
                </button>
                <div class="chat-menu-submenu">
                  <button
                    class="chat-menu-item chat-menu-submenu-trigger"
                    type="button"
                    role="menuitem"
                    aria-haspopup="menu"
                    :aria-expanded="openExportMenuId === chat.id"
                    :data-testid="`chat-export-${chat.id}`"
                    @click="toggleExportMenu(chat.id)"
                  >
                    Export
                  </button>
                  <div
                    v-if="openExportMenuId === chat.id"
                    class="chat-menu-submenu-content"
                    role="menu"
                    :data-testid="`chat-export-submenu-${chat.id}`"
                  >
                    <button
                      class="chat-menu-item"
                      type="button"
                      role="menuitem"
                      :data-testid="`chat-export-download-${chat.id}`"
                      @click="exportChat(chat.id)"
                    >
                      Download Markdown File...
                    </button>
                    <button
                      class="chat-menu-item"
                      type="button"
                      role="menuitem"
                      :data-testid="`chat-export-clipboard-${chat.id}`"
                      @click="copyChatMarkdownToClipboard(chat.id)"
                    >
                      Markdown to Clipboard
                    </button>
                  </div>
                </div>
                <div class="chat-menu-separator" role="separator" />
                <button
                  class="chat-menu-item"
                  type="button"
                  role="menuitem"
                  :data-testid="`chat-permissions-${chat.id}`"
                  @click="openPermissionsDialog(chat.id)"
                >
                  Permissions
                </button>
                <div class="chat-menu-separator" role="separator" />
                <button
                  class="chat-menu-item chat-menu-item--danger"
                  type="button"
                  role="menuitem"
                  :data-testid="`chat-delete-${chat.id}`"
                  @click="openDeleteDialog(chat.id)"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </nav>
      </section>

      <section class="chat-list-section chat-list-section--history">
        <h2 class="chat-list-heading">
          Chats
        </h2>

        <div
          v-if="historyChats.length === 0"
          class="chat-history-placeholder"
        >
          Noch keine gespeicherten Chats
        </div>

        <nav
          v-else
          class="chat-history"
          aria-label="Gespeicherte Chats"
        >
          <div
            v-for="chat in historyChats"
            :key="chat.id"
            class="chat-history-item"
            :class="{
              'chat-history-item--selected': selectedChatId === chat.id,
            }"
            :data-testid="`chat-${chat.id}`"
            @click="selectChat(chat.id)"
          >
            <span
              class="chat-history-title"
              :title="chat.agent_name ? `${chat.title}\nAgent: ${chat.agent_name}` : chat.title"
            >
              {{ chat.agent_name ? `🤖 ${chat.title}` : chat.title }}
            </span>

            <span
              v-if="isChatRunning(chat.id)"
              class="chat-running-indicator"
              data-testid="chat-running"
              aria-label="Antwort läuft"
              title="Antwort läuft"
            />

            <div
              class="chat-menu-container"
              @click.stop
              @pointerdown.stop
            >
              <button
                class="chat-menu-button"
                type="button"
                :data-testid="`chat-menu-${chat.id}`"
                aria-label="Chat-Menü"
                title="Chat-Menü"
                @click="toggleChatMenu(chat.id)"
              >
                ⋮
              </button>

              <div
                v-if="openChatMenuId === chat.id"
                class="chat-menu"
                :data-testid="`chat-menu-popup-${chat.id}`"
                role="menu"
              >
                <button
                  class="chat-menu-item"
                  type="button"
                  role="menuitemcheckbox"
                  :aria-checked="chat.pinned"
                  :data-testid="`chat-pin-${chat.id}`"
                  @click="togglePinned(chat.id, chat.pinned)"
                >
                  Pin
                  <span class="chat-menu-check">
                    {{ chat.pinned ? "✓" : "" }}
                  </span>
                </button>
                <button
                  class="chat-menu-item"
                  type="button"
                  role="menuitem"
                  :data-testid="`chat-rename-${chat.id}`"
                  @click="openRenameDialog(chat.id)"
                >
                  Rename
                </button>
                <div class="chat-menu-submenu">
                  <button
                    class="chat-menu-item chat-menu-submenu-trigger"
                    type="button"
                    role="menuitem"
                    aria-haspopup="menu"
                    :aria-expanded="openExportMenuId === chat.id"
                    :data-testid="`chat-export-${chat.id}`"
                    @click="toggleExportMenu(chat.id)"
                  >
                    Export
                  </button>
                  <div
                    v-if="openExportMenuId === chat.id"
                    class="chat-menu-submenu-content"
                    role="menu"
                    :data-testid="`chat-export-submenu-${chat.id}`"
                  >
                    <button
                      class="chat-menu-item"
                      type="button"
                      role="menuitem"
                      :data-testid="`chat-export-download-${chat.id}`"
                      @click="exportChat(chat.id)"
                    >
                      Download Markdown File...
                    </button>
                    <button
                      class="chat-menu-item"
                      type="button"
                      role="menuitem"
                      :data-testid="`chat-export-clipboard-${chat.id}`"
                      @click="copyChatMarkdownToClipboard(chat.id)"
                    >
                      Markdown to Clipboard
                    </button>
                  </div>
                </div>
                <div class="chat-menu-separator" role="separator" />
                <button
                  class="chat-menu-item"
                  type="button"
                  role="menuitem"
                  :data-testid="`chat-permissions-${chat.id}`"
                  @click="openPermissionsDialog(chat.id)"
                >
                  Permissions
                </button>
                <div class="chat-menu-separator" role="separator" />
                <button
                  class="chat-menu-item chat-menu-item--danger"
                  type="button"
                  role="menuitem"
                  :data-testid="`chat-delete-${chat.id}`"
                  @click="openDeleteDialog(chat.id)"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </nav>
      </section>
    </aside>

    <div
      class="sidebar-splitter"
      data-testid="sidebar-splitter"
      role="separator"
      aria-orientation="vertical"
      @pointerdown="startSidebarResize"
    />

    <div
      v-if="renameChatId !== undefined"
      class="modal-backdrop"
      data-testid="rename-chat-dialog"
      @pointerdown.self="closeRenameDialog"
    >
      <form
        class="chat-dialog"
        @submit.prevent="confirmRename"
      >
        <h2>Chat umbenennen</h2>

        <input
          v-model="renameTitle"
          class="chat-dialog-input"
          data-testid="rename-chat-input"
          aria-label="Chatname"
          autofocus
        >

        <div
          v-if="renameValidationError"
          class="chat-dialog-validation"
          role="alert"
        >
          {{ renameValidationError }}
        </div>

        <div class="chat-dialog-actions">
          <button
            type="button"
            data-testid="rename-chat-cancel"
            @click="closeRenameDialog"
          >
            Cancel
          </button>
          <button
            type="submit"
            data-testid="rename-chat-confirm"
          >
            Rename
          </button>
        </div>
      </form>
    </div>

    <div
      v-if="deleteChatId !== undefined"
      class="modal-backdrop"
      data-testid="delete-chat-dialog"
      @pointerdown.self="closeDeleteDialog"
    >
      <section
        class="chat-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-chat-title"
      >
        <h2 id="delete-chat-title">
          Chat löschen
        </h2>

        <p>
          Chat ‚{{ deleteChatTitle() }}‘ wirklich löschen?
        </p>

        <div class="chat-dialog-actions">
          <button
            type="button"
            data-testid="delete-chat-cancel"
            @click="closeDeleteDialog"
          >
            Cancel
          </button>
          <button
            type="button"
            data-testid="delete-chat-confirm"
            @click="confirmDelete"
          >
            Delete
          </button>
        </div>
      </section>
    </div>

    <div
      v-if="selectedAttachments !== undefined"
      class="modal-backdrop"
      data-testid="message-attachments-dialog"
      @pointerdown.self="closeAttachments"
    >
      <section
        class="chat-dialog attachments-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="message-attachments-title"
      >
        <h2 id="message-attachments-title">Anhänge</h2>
        <ul class="attachment-list">
          <li v-for="attachment in selectedAttachments" :key="attachment.id">
            <span>{{ attachment.original_file_name }}</span>
            <a
              class="message-action-button icon-button"
              :href="`${BACKEND_BASE_URL}/api/v1/attachments/${attachment.id}/download`"
              :download="attachment.original_file_name"
              :aria-label="`${attachment.original_file_name} herunterladen`"
              title="Herunterladen"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3v12M7 10l5 5 5-5M5 20h14" />
              </svg>
            </a>
          </li>
        </ul>
        <div class="chat-dialog-actions">
          <button type="button" @click="closeAttachments">Schließen</button>
        </div>
      </section>
    </div>

    <section class="chat-main">
      <section
        v-show="!isComposerExpanded"
        class="messages-shell"
      >
        <img
          class="chat-watermark"
          :src="watermarkUrl"
          alt=""
          aria-hidden="true"
        >

        <section
          ref="messagesElement"
          class="messages"
          data-testid="messages"
          aria-live="polite"
        >
          <article
            v-for="(message, index) in messages"
            :key="index"
            class="message"
            :class="[
              `message-${message.role}`,
              { 'message-audio': message.kind === 'audio', 'message-progress': message.kind === 'progress' },
            ]"
            :data-testid="`message-${message.role}`"
          >
            <div v-if="message.kind !== 'progress'" class="message-role">
              {{ message.role === "user" ? "Du" : uiConfig?.name ?? "" }}
            </div>
            <MarkdownMessage
              v-if="message.kind !== 'progress'"
              :ref="(instance) => setMessageRenderer(index, instance)"
              class="message-content"
              :content="message.content"
              :preserve-line-breaks="message.role === 'user'"
            />
            <WorkflowDecorator
              v-if="message.kind === 'progress' && message.workflow_execution"
              :execution="message.workflow_execution"
              :messages="message.progress_messages ?? []"
            />


          <div
            class="message-actions"
            :data-testid="`message-actions-${message.role}`"
          >
            <span
              v-if="message.role === 'user'"
              class="message-time"
              data-testid="message-time"
            >
              {{ formatMessageTime(message) }}
            </span>

            <button
              class="message-action-button icon-button"
              type="button"
              data-testid="message-attachments"
              aria-label="Anhänge anzeigen"
              title="Anhänge anzeigen"
              :disabled="!message.attachments?.length"
              @click="openAttachments(message.attachments ?? [])"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M8.5 12.5 14.8 6.2a3.5 3.5 0 1 1 5 5l-7.8 7.8a5 5 0 0 1-7.1-7.1l7.3-7.3" />
              </svg>
            </button>

            <button
              class="message-action-button icon-button"
              type="button"
              data-testid="copy-message"
              aria-label="Nachricht kopieren"
              title="Nachricht kopieren"
              @click="copyMessage(index, message.content)"
            >
              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <rect x="9" y="9" width="10" height="10" rx="2" />
                <path d="M15 9V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2" />
              </svg>
            </button>

            <button
              v-if="message.role === 'assistant'"
              class="message-action-button icon-button"
              type="button"
              data-testid="read-aloud-message"
              aria-label="Vorlesen"
              title="Vorlesen"
              :disabled="isGenerating || isTtsSynthesizing"
              @click="readMessageAloud(index)"
            >

              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path d="M11 5 6 9H3v6h3l5 4V5Z" />
                <path d="M15 9a4 4 0 0 1 0 6M17.5 6.5a8 8 0 0 1 0 11" />
              </svg>
            </button>

            <button
              v-if="message.role === 'assistant'"
              class="message-action-button icon-button"
              type="button"
              data-testid="branch-message"
              aria-label="Neuen Chat ab hier starten"
              title="Neuen Chat ab hier starten"
              disabled
            >
              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle cx="6" cy="5" r="2" />
                <circle cx="18" cy="7" r="2" />
                <circle cx="18" cy="17" r="2" />
                <path d="M8 5h2a4 4 0 0 1 4 4v4a4 4 0 0 0 4 4M14 10a4 4 0 0 1 4-3" />
              </svg>
            </button>

            <button
              v-if="message.role === 'user'"
              class="message-action-button icon-button"
              type="button"
              data-testid="edit-message"
              aria-label="Nachricht bearbeiten"
              title="Nachricht bearbeiten"
              disabled
            >
              <svg
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path d="M4 20h4l11-11-4-4L4 16v4Z" />
                <path d="m13 7 4 4" />
              </svg>
            </button>

            <span
              v-if="message.role === 'assistant'"
              class="message-time"
              data-testid="message-time"
            >
              {{ formatMessageTime(message) }}
            </span>
            </div>
          </article>
        </section>
      </section>

      <footer

        class="composer"
        :class="{ 'composer--expanded': isComposerExpanded }"
      >
        <div class="composer-input">
          <button
            class="composer-expand-button icon-button"
            type="button"
            data-testid="toggle-composer"
            :aria-label="isComposerExpanded ? 'Eingabe verkleinern' : 'Eingabe vergrößern'"
            :title="isComposerExpanded ? 'Eingabe verkleinern' : 'Eingabe vergrößern'"
            @click="toggleComposerExpanded"
          >
            <svg
              v-if="!isComposerExpanded"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path d="M9 4H4v5M15 4h5v5M9 20H4v-5M15 20h5v-5" />
            </svg>
            <svg
              v-else
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path d="M4 9h5V4M20 9h-5V4M4 15h5v5M20 15h-5v5" />
            </svg>
          </button>

          <MarkdownComposer
            v-model="input"
            placeholder="Dein Prompt hier"
            :toolbar-enabled="isComposerExpanded"
            :disabled="isChatCompressionFailed"
            @keydown="handleInputKeydown"
          />



        </div>

        <div class="composer-actions">
          <div
            v-if="errorMessage"
            class="error-message"
            data-testid="chat-error"
            role="alert"
          >
            {{ errorMessage }}
          </div>

          <div
            v-if="isRecording"
            class="recording-status"
            data-testid="recording-status"
            role="status"
          >
            Aufnahme · {{ remainingRecordingSeconds }} s
          </div>

          <button
            class="icon-button audio-record-button"
            :class="{ 'audio-record-button--recording': isRecording }"
            type="button"
            data-testid="record-audio"
            aria-label="Sprachnachricht aufnehmen"
            title="Zum Aufnehmen gedrückt halten"
            :disabled="isGenerating || isDialogActive || isChatCompressionFailed"
            @pointerdown="startAudioRecording"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <rect x="9" y="3" width="6" height="11" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8" />
            </svg>
          </button>

          <button
            class="icon-button dialog-button"
            :class="{
              'dialog-button--active':
                isDialogActive && !isDialogSpeaking,
              'dialog-button--stop':
                isDialogSpeaking,
            }"
            type="button"
            data-testid="dialog-call"
            :aria-label="
              !isDialogActive
                ? 'Dialog starten'
                : isDialogSpeaking
                  ? 'Sprachausgabe stoppen'
                  : 'Dialog beenden'
            "
            :title="
              !isDialogActive
                ? 'Dialog starten'
                : isDialogSpeaking
                  ? 'Sprachausgabe stoppen'
                  : 'Dialog beenden'
            "
            :disabled="isRecording || recordingStartPending || isChatCompressionFailed"
            @click="handleDialogButton"
          >
            <svg
              v-if="isDialogSpeaking"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <rect x="7" y="7" width="10" height="10" />
            </svg>
            <svg
              v-else
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                d="M7.4 3.5l2.2 4.1-1.7 1.7a15 15 0 0 0 6.8 6.8l1.7-1.7 4.1 2.2c.5.3.7.8.5 1.3l-.9 2.8c-.2.5-.7.8-1.2.8C9.8 21.5 2.5 14.2 2.5 5.1c0-.5.3-1 .8-1.2l2.8-.9c.5-.2 1 .1 1.3.5z"
              />
            </svg>
          </button>


          <button
            v-if="isGenerating && !isDialogActive"
            class="icon-button"
            type="button"
            data-testid="stop-chat"
            aria-label="Antwort stoppen"
            title="Antwort stoppen"
            @click="stop"
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <rect x="7" y="7" width="10" height="10" />
            </svg>
          </button>

          <button
            v-else-if="!isDialogActive"
            class="icon-button"
            type="button"
            data-testid="send-chat"
            aria-label="Nachricht senden"
            title="Nachricht senden"
            :disabled="input.length === 0 || isDialogActive || isBoundCallTurnActive || isChatCompressionFailed"
            @click="sendComposerInput"
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path d="M12 19V5M6 11l6-6 6 6" />
            </svg>
          </button>
        </div>
      </footer>
    </section>
  </main>
</template>

<style scoped>
.chat-window {
  height: 100vh;
  display: flex;
  box-sizing: border-box;
  overflow: hidden;
  font-family: sans-serif;
  background: #f7f7f7;
  color: #1f1f1f;
}

.sidebar {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  overflow: visible;
  background: #eeeeee;
}

.sidebar-header {
  padding: 1rem 1.25rem;
}

.sidebar-header h1 {
  margin: 0;
  font-size: 1.25rem;
}

.new-chat-button {
  margin: 0 1rem 1rem;
}

.icon-button {
  width: 2.25rem;
  height: 2.25rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  padding: 0.4rem;
  box-sizing: border-box;
  border: 1px solid #cccccc;
  border-radius: 0.4rem;
  background: #ffffff;
  color: inherit;
  cursor: pointer;
}

.icon-button svg {
  width: 1.1rem;
  height: 1.1rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.icon-button:hover:not(:disabled) {
  background: #f2f2f2;
}

.icon-button:disabled {
  color: #aaaaaa;
  cursor: default;
}

.chat-list-section {
  position: relative;
  flex: 0 0 auto;
  min-height: 0;
}

.chat-list-section--pinned {
  z-index: 2;
}

.chat-list-section--pinned .chat-history {
  overflow: visible;
}

.chat-list-section--history {
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-list-heading {
  margin: 0;
  padding: 0.45rem 1rem;
  color: #666666;
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
}

.chat-history-placeholder {
  padding: 0.65rem 1rem 1rem;
  color: #666666;
  font-size: 0.9rem;
}

.chat-history {
  min-height: 0;
  overflow-y: auto;
  padding: 0 0.5rem 0.5rem;
}

.chat-list-section--history .chat-history {
  flex: 1;
}

.chat-history-item {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 0.75rem;
  box-sizing: border-box;
  border: 0;
  border-radius: 0.4rem;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.chat-history-item:hover {
  background: #e4e4e4;
}

.chat-history-item--selected {
  background: #dddddd;
}

.chat-history-title {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-menu-container {
  position: relative;
  z-index: 30;
  flex: 0 0 auto;
}

.chat-menu-button {
  width: 1.75rem;
  height: 1.75rem;
  padding: 0;
  border: 0;
  border-radius: 0.3rem;
  background: transparent;
  color: inherit;
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  visibility: hidden;
}

.chat-history-item:hover .chat-menu-button,
.chat-menu-container:focus-within .chat-menu-button {
  opacity: 1;
  visibility: visible;
}

.chat-menu-button:hover {
  background: #d8d8d8;
}

.chat-menu {
  position: absolute;
  z-index: 20;
  top: calc(100% + 0.2rem);
  right: 0;
  min-width: 9rem;
  padding: 0.25rem;
  border: 1px solid #cccccc;
  border-radius: 0.4rem;
  background: #ffffff;
  box-shadow: 0 0.3rem 0.8rem rgb(0 0 0 / 15%);
}

.chat-menu-submenu-content {
  padding-left: 0.6rem;
}

.chat-menu-submenu-trigger::after {
  content: "›";
  margin-left: auto;
  transform: rotate(0deg);
  transition: transform 0.15s ease;
}

.chat-menu-submenu-trigger[aria-expanded="true"]::after {
  transform: rotate(90deg);
}

.chat-menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.45rem 0.55rem;
  border: 0;
  border-radius: 0.3rem;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.chat-menu-item:hover:not(:disabled) {
  background: #eeeeee;
}

.chat-menu-item:disabled {
  color: #aaaaaa;
  cursor: default;
}

.chat-menu-item--danger {
  color: #a00000;
}

.chat-menu-check {
  width: 1rem;
  flex: 0 0 1rem;
  margin-left: auto;
  text-align: center;
}

.modal-backdrop {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(0 0 0 / 35%);
}

.chat-dialog {
  width: min(24rem, calc(100vw - 3rem));
  box-sizing: border-box;
  padding: 1.25rem;
  border-radius: 0.6rem;
  background: #ffffff;
  box-shadow: 0 0.6rem 2rem rgb(0 0 0 / 20%);
}

.chat-dialog h2 {
  margin: 0 0 1rem;
  font-size: 1.1rem;
}

.chat-dialog p {
  margin: 0 0 1rem;
}

.attachments-dialog {
  width: min(32rem, calc(100vw - 3rem));
}

.attachment-list {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.attachment-list li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.attachment-list span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-list a {
  margin-left: auto;
}

.chat-dialog-input {
  width: 100%;
  box-sizing: border-box;
  padding: 0.55rem 0.65rem;
  border: 1px solid #bbbbbb;
  border-radius: 0.35rem;
  font: inherit;
}

.chat-dialog-validation {
  margin-top: 0.5rem;
  color: #a00000;
  font-size: 0.85rem;
}

.chat-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}

.chat-dialog-actions button {
  padding: 0.45rem 0.8rem;
  border: 1px solid #bbbbbb;
  border-radius: 0.35rem;
  background: #ffffff;
  color: inherit;
  cursor: pointer;
}

.chat-dialog-actions button:hover {
  background: #eeeeee;
}


.chat-running-indicator {
  width: 0.55rem;
  height: 0.55rem;
  flex: 0 0 auto;
  border: 2px solid #a0a0a0;
  border-top-color: #333333;
  border-radius: 50%;
  animation: chat-running-spin 0.8s linear infinite;
}

@keyframes chat-running-spin {
  to {
    transform: rotate(360deg);
  }
}

.sidebar-splitter {
  position: relative;
  flex: 0 0 5px;
  cursor: col-resize;
  background: transparent;
}

.sidebar-splitter::after {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: 2px;
  width: 1px;
  background: #d8d8d8;
}

.chat-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.messages-shell {
  position: relative;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.chat-watermark {
  position: absolute;
  top: 50%;
  left: 50%;
  width: min(90%, 48rem);
  max-height: 90%;
  transform: translate(-50%, -50%);
  object-fit: contain;
  opacity: 0.1;
  pointer-events: none;
  user-select: none;
}

.messages {
  position: relative;
  z-index: 1;
  height: 100%;
  box-sizing: border-box;
  overflow-y: auto;
  padding: 1.5rem;
}


.message {
  max-width: 48rem;
  margin: 0 auto 1.5rem;
}

.message-role {
  margin-bottom: 0.35rem;
  font-weight: 600;
}

.message-content {
  overflow-wrap: anywhere;
}

.message-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-top: 0.4rem;
}

.message-action-button {
  width: 1.9rem;
  height: 1.9rem;
  padding: 0.35rem;
  border-color: transparent;
  background: transparent;
}

.message-time {
  margin: 0 0.2rem;
  color: #777777;
  font-size: 0.75rem;
  white-space: nowrap;
}

.message-user .message-actions {
  justify-content: flex-end;
}

.message-user {
  width: fit-content;
  max-width: min(75%, 42rem);
  margin-left: auto;
  margin-right: 0;
  padding: 0.75rem 1rem;
  border-radius: 1rem;
  background: #dbeafe;
  text-align: left;
}

.message-user .message-role {
  text-align: right;
}

.message-audio .message-content {
  color: #4b5563;
}

.message-assistant {
  text-align: left;
}

.composer {
  position: relative;
  z-index: 2;
  padding: 0.75rem 1.5rem 1rem;
  border-top: 1px solid #e2e2e2;
  background: #ffffff;
}


.composer-input {
  position: relative;
  height: 5.5rem;
  overflow: hidden;
  border: 1px solid #cccccc;
  border-radius: 0.5rem;
  background: #ffffff;
}

.composer--expanded {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.composer--expanded .composer-input {
  flex: 1;
  min-height: 0;
  height: auto;
}

.composer--expanded .composer-expand-button {
  top: 0.35rem;
}

.composer-expand-button {

  position: absolute;
  z-index: 1;
  top: 0.5rem;
  right: 0.5rem;
}

.composer-input:focus-within {
  border-color: #8baee8;
}


.composer-actions {
  min-height: 2rem;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 0.5rem;
}

.error-message {
  margin-right: auto;
  color: #a00000;
}

.recording-status {
  color: #a00000;
  font-size: 0.9rem;
}

.audio-record-button--recording {
  border-color: #b91c1c;
  background: #fee2e2;
  color: #b91c1c;
}

.dialog-button {
  color: #2563eb;
}

.dialog-button--active,
.dialog-button--stop {
  border-color: #b91c1c;
  background: #fee2e2;
  color: #b91c1c;
}

</style>
