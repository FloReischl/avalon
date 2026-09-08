import {
  computed,
  markRaw,
  reactive,
  ref,
} from "vue";

import {
  getChat,
  getChats,
  streamAudioResponse,
  streamChatMessage,
  type ChatStreamHandlers,
  type ChatStreamRequest,
  type ChatSummary,
  type ConversationMessage,
} from "../services/backend";
import type { ChatMessage } from "../types/chat";

export type ChatStreamer = (
  request: ChatStreamRequest,
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
) => Promise<void>;

export type AudioStreamer = (
  messages: ConversationMessage[],
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
) => Promise<void>;

interface ChatState {
  chatId?: number;
  messages: ChatMessage[];
  input: string;
  errorMessage?: string;
  activeTurn?: ActiveTurn;
}

interface ActiveTurn {
  prompt: string;
  startIndex: number;
  assistantIndex: number;
  controller: AbortController;
  kind: "text" | "audio";
  done: boolean;
}

function createChatState(
  chatId?: number,
  messages: ChatMessage[] = [],
): ChatState {
  return reactive({
    chatId,
    messages,
    input: "",
    errorMessage: undefined,
    activeTurn: undefined,
  });
}

export function useTransientChat(
  streamMessage: ChatStreamer = streamChatMessage,
  streamAudio: AudioStreamer = streamAudioResponse,
) {
  const currentState = ref<ChatState>(createChatState());
  const chatSummaries = ref<ChatSummary[]>([]);
  const chatStates = new Map<number, ChatState>();
  const runningChatIds = reactive(new Set<number>());

  const messages = computed({
    get: () => currentState.value.messages,
    set: (value: ChatMessage[]) => {
      currentState.value.messages = value;
    },
  });

  const input = computed({
    get: () => currentState.value.input,
    set: (value: string) => {
      currentState.value.input = value;
    },
  });

  const errorMessage = computed({
    get: () => currentState.value.errorMessage,
    set: (value: string | undefined) => {
      currentState.value.errorMessage = value;
    },
  });

  const isGenerating = computed(
    () =>
      currentState.value.activeTurn !== undefined
      && !currentState.value.activeTurn.done,
  );

  const selectedChatId = computed(
    () => currentState.value.chatId,
  );

  function rollbackTurn(
    state: ChatState,
    turn: ActiveTurn,
  ) {
    state.messages.splice(turn.startIndex);
    state.input = turn.prompt;
  }

  function conversationContext(
    state: ChatState,
  ): ConversationMessage[] {
    return state.messages
      .filter(
        (message) =>
          message.content.length > 0
          && !(message.role === "user" && message.kind === "audio"),
      )
      .map(({ role, content }) => ({ role, content }));
  }

  async function refreshChats(
    showError = false,
    attempts = 1,
  ) {
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      try {
        chatSummaries.value = await getChats();
        return;
      } catch (error) {
        console.error(error);

        if (attempt < attempts) {
          await new Promise((resolve) => {
            window.setTimeout(resolve, 500);
          });
          continue;
        }

        if (showError) {
          currentState.value.errorMessage =
            "Chatliste konnte nicht geladen werden.";
        }
      }
    }
  }

  async function selectChat(chatId: number) {
    if (currentState.value.chatId === chatId) {
      return;
    }

    const runningState = chatStates.get(chatId);
    if (runningState?.activeTurn) {
      currentState.value.input = "";
      runningState.input = "";
      currentState.value = runningState;
      return;
    }

    let detail;

    try {
      detail = await getChat(chatId);
    } catch (error) {
      console.error(error);
      currentState.value.errorMessage =
        "Chat konnte nicht geladen werden.";
      return;
    }

    currentState.value.input = "";

    const state = createChatState(
      detail.id,
      detail.messages.map(({ role, content }) => ({
        role,
        content,
      })),
    );

    chatStates.set(detail.id, state);
    currentState.value = state;
  }

  function newChat() {
    if (
      currentState.value.chatId === undefined
      && currentState.value.messages.length === 0
      && currentState.value.input.length === 0
      && currentState.value.errorMessage === undefined
    ) {
      return;
    }

    currentState.value.input = "";
    currentState.value = createChatState();
  }

  async function send() {
    const state = currentState.value;

    if (
      state.activeTurn
      || state.input.length === 0
    ) {
      return;
    }

    const prompt = state.input;
    const startIndex = state.messages.length;
    const controller = new AbortController();

    const turn: ActiveTurn = {
      prompt,
      startIndex,
      assistantIndex: startIndex + 1,
      controller,
      kind: "text",
      done: false,
    };

    state.activeTurn = markRaw(turn);
    state.errorMessage = undefined;
    state.input = "";

    state.messages.push(
      {
        role: "user",
        content: prompt,
      },
      {
        role: "assistant",
        content: "",
      },
    );

    if (state.chatId !== undefined) {
      runningChatIds.add(state.chatId);
    }

    const request: ChatStreamRequest = state.chatId === undefined
      ? { message: prompt }
      : {
          chatId: state.chatId,
          message: prompt,
        };

    try {
      await streamMessage(
        request,
        {
          onChat(chatId) {
            if (
              state.chatId !== undefined
              && state.chatId !== chatId
            ) {
              throw new Error("Chat stream returned a different chat ID");
            }

            state.chatId = chatId;
            chatStates.set(chatId, state);
            runningChatIds.add(chatId);
          },
          onChunk(text) {
            if (state.activeTurn !== turn) {
              return;
            }

            state.messages[turn.assistantIndex].content += text;
          },
          onDone() {
            if (state.activeTurn === turn) {
              turn.done = true;
            }
          },
        },
        controller.signal,
      );
    } catch {
      if (state.activeTurn !== turn) {
        return;
      }

      rollbackTurn(state, turn);

      if (!controller.signal.aborted) {
        state.errorMessage =
          "Antwort konnte nicht erzeugt werden.";
      }
    } finally {
      if (state.activeTurn === turn) {
        state.activeTurn = undefined;
      }

      if (state.chatId !== undefined) {
        runningChatIds.delete(state.chatId);
      }

      await refreshChats();
    }
  }

  async function sendAudio() {
    const state = currentState.value;

    if (state.activeTurn) {
      return;
    }

    const context = conversationContext(state);
    const startIndex = state.messages.length;
    const controller = new AbortController();

    const turn: ActiveTurn = {
      prompt: "",
      startIndex,
      assistantIndex: startIndex + 1,
      controller,
      kind: "audio",
      done: false,
    };

    state.activeTurn = markRaw(turn);
    state.errorMessage = undefined;

    state.messages.push(
      {
        role: "user",
        content: "🎤 Sprachnachricht",
        kind: "audio",
      },
      {
        role: "assistant",
        content: "",
      },
    );

    if (state.chatId !== undefined) {
      runningChatIds.add(state.chatId);
    }

    try {
      await streamAudio(
        context,
        {
          onChunk(text) {
            if (state.activeTurn === turn) {
              state.messages[turn.assistantIndex].content += text;
            }
          },
        },
        controller.signal,
      );
    } catch {
      if (state.activeTurn !== turn) {
        return;
      }

      state.messages.splice(turn.assistantIndex, 1);

      if (!controller.signal.aborted) {
        state.errorMessage =
          "Sprachantwort konnte nicht erzeugt werden.";
      }
    } finally {
      if (state.activeTurn === turn) {
        state.activeTurn = undefined;
      }

      if (state.chatId !== undefined) {
        runningChatIds.delete(state.chatId);
      }
    }
  }

  function stop() {
    const state = currentState.value;
    const turn = state.activeTurn;

    if (!turn) {
      return;
    }

    turn.controller.abort();

    if (turn.kind === "audio") {
      state.messages.splice(turn.assistantIndex, 1);
    } else {
      rollbackTurn(state, turn);
    }

    state.activeTurn = undefined;

    if (state.chatId !== undefined) {
      runningChatIds.delete(state.chatId);
    }
  }

  function isChatRunning(chatId: number) {
    return runningChatIds.has(chatId);
  }

  return {
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
  };
}