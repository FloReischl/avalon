<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

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
        class="new-chat-button"
        type="button"
        data-testid="new-chat"
        @click="newChat"
      >
        New Chat
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
          <div class="message-content">{{ message.content }}</div>
        </article>
      </section>

      <footer class="composer">
        <textarea
          v-model="input"
          data-testid="chat-input"
          aria-label="Nachricht"
          placeholder="Nachricht an Frieda"
          :disabled="isGenerating"
          rows="3"
          @keydown="handleInputKeydown"
        />

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
            type="button"
            data-testid="stop-chat"
            aria-label="Antwort stoppen"
            @click="stop"
          >
            Stop
          </button>

          <button
            v-else
            type="button"
            data-testid="send-chat"
            aria-label="Nachricht senden"
            :disabled="input.length === 0"
            @click="send"
          >
            Send
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

.chat-history-placeholder {
  padding: 1rem;
  color: #666666;
  font-size: 0.9rem;
}

.sidebar-splitter {
  flex: 0 0 5px;
  cursor: col-resize;
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
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.message-user {
  text-align: right;
}

.message-assistant {
  text-align: left;
}

.composer {
  padding: 1rem 1.5rem 1.5rem;
  border-top: 1px solid #d8d8d8;
}

.composer textarea {
  width: 100%;
  resize: vertical;
  box-sizing: border-box;
  font: inherit;
}

.composer-actions {
  min-height: 2.25rem;
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
