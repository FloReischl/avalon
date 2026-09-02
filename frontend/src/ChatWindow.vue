<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import MarkdownMessage from "./components/MarkdownMessage.vue";

import { useTransientChat } from "./composables/useTransientChat";

const {
  messages,
  input,
  isGenerating,
  errorMessage,
  send,
  stop,
} = useTransientChat();


const messagesElement = ref<HTMLElement>();
const isComposerExpanded = ref(false);

type MarkdownMessageInstance = {
  getRenderedHtml: () => string;
};

const messageRenderers = new Map<number, MarkdownMessageInstance>();

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

  if (renderer?.getRenderedHtml) {
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

function newChat() {
  if (isGenerating.value) {
    stop();
  }

  if (
    messages.value.length === 0
    && input.value.length === 0
    && errorMessage.value === undefined
  ) {
    return;
  }

  messages.value = [];
  input.value = "";
  errorMessage.value = undefined;
}


function handleInputKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter") {
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

      <div class="chat-history-placeholder">
        Noch keine gespeicherten Chats
      </div>
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
        ref="messagesElement"
        class="messages"
        data-testid="messages"
        aria-live="polite"
      >
        <article
          v-for="(message, index) in messages"
          :key="index"
          class="message"
          :class="`message-${message.role}`"
          :data-testid="`message-${message.role}`"
        >
          <div class="message-role">
            {{ message.role === "user" ? "Du" : "Frieda" }}
          </div>
          <MarkdownMessage
            :ref="(instance) => setMessageRenderer(index, instance)"
            class="message-content"
            :content="message.content"
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
              disabled
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

          <textarea
            v-model="input"
            data-testid="chat-input"
            aria-label="Nachricht"
            placeholder="Nachricht an Frieda"
            :disabled="isGenerating"
            rows="3"
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

.messages {
  flex: 1;
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

.message-assistant {
  text-align: left;
}

.composer {
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

.composer textarea {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0.75rem 3.5rem 0.75rem 0.85rem;
  box-sizing: border-box;
  border: 0;
  resize: none;
  outline: none;
  background: transparent;
  color: inherit;
  font-family: ui-monospace, "Consolas", "Liberation Mono", monospace;
  font-size: 0.95rem;
  line-height: 1.45;
  tab-size: 4;
}

.composer textarea::placeholder {
  color: #999999;
}

.composer textarea:disabled {
  background: #f5f5f5;
  color: #777777;
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

</style>
