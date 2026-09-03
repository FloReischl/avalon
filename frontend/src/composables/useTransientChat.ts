import { ref } from "vue";

import {
  streamAudioResponse,
  streamChatMessage,
  type ConversationMessage,
} from "../services/backend";
import type { ChatMessage } from "../types/chat";

export type ChatStreamer = (
  messages: ConversationMessage[],
  handlers: {
    onChunk: (text: string) => void;
  },
  signal: AbortSignal,
) => Promise<void>;

export type AudioStreamer = (
  messages: ConversationMessage[],
  handlers: {
    onChunk: (text: string) => void;
  },
  signal: AbortSignal,
) => Promise<void>;

interface ActiveTurn {
  prompt: string;
  startIndex: number;
  assistantIndex: number;
  controller: AbortController;
  kind: "text" | "audio";
}

export function useTransientChat(
  streamMessage: ChatStreamer = streamChatMessage,
  streamAudio: AudioStreamer = streamAudioResponse,
) {
  const messages = ref<ChatMessage[]>([]);
  const input = ref("");
  const isGenerating = ref(false);
  const errorMessage = ref<string | undefined>();

  let activeTurn: ActiveTurn | undefined;

  function rollbackTurn(turn: ActiveTurn) {
    messages.value.splice(turn.startIndex);
    input.value = turn.prompt;
  }

  function conversationContext(): ConversationMessage[] {
    return messages.value
      .filter(
        (message) =>
          message.content.length > 0
          && !(message.role === "user" && message.kind === "audio"),
      )
      .map(({ role, content }) => ({ role, content }));
  }

  async function send() {
    if (isGenerating.value || input.value.length === 0) {
      return;
    }

    const prompt = input.value;
    const context = conversationContext();
    const startIndex = messages.value.length;
    const controller = new AbortController();

    const turn: ActiveTurn = {
      prompt,
      startIndex,
      assistantIndex: startIndex + 1,
      controller,
      kind: "text",
    };

    activeTurn = turn;
    errorMessage.value = undefined;
    input.value = "";
    isGenerating.value = true;

    messages.value.push(
      {
        role: "user",
        content: prompt,
      },
      {
        role: "assistant",
        content: "",
      },
    );

    try {
      await streamMessage(
        [...context, { role: "user", content: prompt }],
        {
          onChunk(text) {
            if (activeTurn !== turn) {
              return;
            }

            messages.value[turn.assistantIndex].content += text;
          },
        },
        controller.signal,
      );
    } catch {
      if (activeTurn !== turn) {
        return;
      }

      rollbackTurn(turn);

      if (!controller.signal.aborted) {
        errorMessage.value = "Antwort konnte nicht erzeugt werden.";
      }
    } finally {
      if (activeTurn === turn) {
        activeTurn = undefined;
        isGenerating.value = false;
      }
    }
  }

  async function sendAudio() {
    if (isGenerating.value) {
      return;
    }

    const context = conversationContext();
    const startIndex = messages.value.length;
    const controller = new AbortController();
    const turn: ActiveTurn = {
      prompt: "",
      startIndex,
      assistantIndex: startIndex + 1,
      controller,
      kind: "audio",
    };

    activeTurn = turn;
    errorMessage.value = undefined;
    isGenerating.value = true;
    messages.value.push(
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

    try {
      await streamAudio(
        context,
        {
          onChunk(text) {
            if (activeTurn === turn) {
              messages.value[turn.assistantIndex].content += text;
            }
          },
        },
        controller.signal,
      );
    } catch {
      if (activeTurn !== turn) {
        return;
      }

      messages.value.splice(turn.assistantIndex, 1);
      if (!controller.signal.aborted) {
        errorMessage.value = "Sprachantwort konnte nicht erzeugt werden.";
      }
    } finally {
      if (activeTurn === turn) {
        activeTurn = undefined;
        isGenerating.value = false;
      }
    }
  }

  function stop() {
    const turn = activeTurn;
    if (!turn) {
      return;
    }

    turn.controller.abort();
    if (turn.kind === "audio") {
      messages.value.splice(turn.assistantIndex, 1);
    } else {
      rollbackTurn(turn);
    }
    activeTurn = undefined;
    isGenerating.value = false;
  }

  return {
    messages,
    input,
    isGenerating,
    errorMessage,
    send,
    sendAudio,
    stop,
  };
}
