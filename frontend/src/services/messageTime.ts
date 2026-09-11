import type { ChatMessage } from "../types/chat";

const transientMessageTimes = new WeakMap<ChatMessage, Date>();

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function localDate(value: Date): string {
  return [
    value.getFullYear(),
    pad(value.getMonth() + 1),
    pad(value.getDate()),
  ].join("-");
}

function localTime(value: Date): string {
  return `${pad(value.getHours())}:${pad(value.getMinutes())}`;
}

export function formatMessageTime(
  message: ChatMessage,
  now = new Date(),
): string {
  let value: Date;

  if (message.created_at) {
    value = new Date(message.created_at);
  } else {
    const existing = transientMessageTimes.get(message);

    if (existing) {
      value = existing;
    } else {
      value = new Date(now);
      transientMessageTimes.set(message, value);
    }
  }

  if (Number.isNaN(value.getTime())) {
    return "";
  }

  if (localDate(value) === localDate(now)) {
    return localTime(value);
  }

  return `${localDate(value)} ${localTime(value)}`;
}