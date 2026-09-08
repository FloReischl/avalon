<script setup lang="ts">
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";

import MarkdownComposer from "./components/MarkdownComposer.vue";
import MarkdownMessage from "./components/MarkdownMessage.vue";

import watermarkUrl from "./assets/watermark.png";

import { getActiveAvatar } from "./avatar";

import { useTransientChat } from "./composables/useTransientChat";
import {
  abortAudioRecording as abortBackendAudioRecording,
  notifyTtsPlaybackEnded,
  startAudioRecording as startBackendAudioRecording,
  synthesizeSpeech,
} from "./services/backend";


const avatar = getActiveAvatar();

const {
  messages,
  input,
  isGenerating,
  errorMessage,
  chatSummaries,
  selectedChatId,
  refreshChats,
  selectChat,
  newChat,
  isChatRunning,
  send,
  sendAudio,
  stop,
} = useTransientChat();


const messagesElement = ref<HTMLElement>();
const isComposerExpanded = ref(false);
const isRecording = ref(false);
const remainingRecordingSeconds = ref(30);
const isTtsSynthesizing = ref(false);

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
  } catch {
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
    } catch {
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
  } catch {
    errorMessage.value = "Audioaufnahme konnte nicht verworfen werden.";
  }
}

onMounted(() => {
  void refreshChats(true, 20);
});

onBeforeUnmount(() => {
  if (isRecording.value) {
    void abortBackendAudioRecording();
  }

  replaceCurrentTts();
  resetRecordingState();
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


function cleanupTtsAudio() {
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
}

function replaceCurrentTts() {
  ttsRequestToken += 1;
  ttsAbortController?.abort();
  ttsAbortController = undefined;
  cleanupTtsAudio();

  if (ttsPlaybackId) {
    void notifyTtsPlaybackEnded(ttsPlaybackId);
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

    audio.onended = () => {
      if (requestToken !== ttsRequestToken) {
        return;
      }

      cleanupTtsAudio();
      ttsPlaybackId = undefined;
      void notifyTtsPlaybackEnded(tts.playbackId);
    };

    audio.onerror = () => {

      if (requestToken !== ttsRequestToken) {
        return;
      }

      cleanupTtsAudio();
      ttsPlaybackId = undefined;
      errorMessage.value = "Vorlesen fehlgeschlagen.";
      void notifyTtsPlaybackEnded(tts.playbackId);
    };


    await audio.play();
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

    errorMessage.value = "Vorlesen fehlgeschlagen.";

    if (playbackId) {
      void notifyTtsPlaybackEnded(playbackId);
    }
  } finally {
    if (requestToken === ttsRequestToken) {
      isTtsSynthesizing.value = false;
      ttsAbortController = undefined;
    }
  }
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


function handleInputKeydown(event: KeyboardEvent) {
  if (
    event.key !== "Enter"
    || isGenerating.value
  ) {
    return;
  }

  if (event.ctrlKey) {
    event.preventDefault();
    void send();
    return;
  }

  if (event.shiftKey || input.value.includes("\n")) {
    return;
  }

  event.preventDefault();
  void send();
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
        <h1>Avalo</h1>
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

      <div
        v-if="chatSummaries.length === 0"
        class="chat-history-placeholder"
      >
        Noch keine gespeicherten Chats
      </div>

      <nav
        v-else
        class="chat-history"
        aria-label="Gespeicherte Chats"
      >
        <button
          v-for="chat in chatSummaries"
          :key="chat.id"
          class="chat-history-item"
          :class="{
            'chat-history-item--selected': selectedChatId === chat.id,
          }"
          type="button"
          :data-testid="`chat-${chat.id}`"
          @click="selectChat(chat.id)"
        >
          <span
            class="chat-history-title"
            :title="chat.title"
          >
            {{ chat.title }}
          </span>

          <span
            v-if="isChatRunning(chat.id)"
            class="chat-running-indicator"
            data-testid="chat-running"
            aria-label="Antwort läuft"
            title="Antwort läuft"
          />
        </button>
      </nav>
    </aside>

    <div
      class="sidebar-splitter"
      data-testid="sidebar-splitter"
      role="separator"
      aria-orientation="vertical"
      @pointerdown="startSidebarResize"
    />

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
              { 'message-audio': message.kind === 'audio' },
            ]"
            :data-testid="`message-${message.role}`"
          >
            <div class="message-role">
              {{ message.role === "user" ? "Du" : avatar.name }}
            </div>
            <MarkdownMessage
              :ref="(instance) => setMessageRenderer(index, instance)"
              class="message-content"
              :content="message.content"
              :preserve-line-breaks="message.role === 'user'"
            />


          <div
            class="message-actions"
            :data-testid="`message-actions-${message.role}`"
          >
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
            :disabled="isGenerating"
            @pointerdown="startAudioRecording"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <rect x="9" y="3" width="6" height="11" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8" />
            </svg>
          </button>


          <button
            v-if="isGenerating"
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
            v-else
            class="icon-button"
            type="button"
            data-testid="send-chat"
            aria-label="Nachricht senden"
            title="Nachricht senden"
            :disabled="input.length === 0"
            @click="send"
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
  overflow: hidden;
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

.chat-history-placeholder {
  padding: 1rem;
  color: #666666;
  font-size: 0.9rem;
}

.chat-history {
  min-height: 0;
  overflow-y: auto;
  padding: 0 0.5rem 1rem;
}

.chat-history-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 0.75rem;
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
  opacity: 0.4;
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

</style>
