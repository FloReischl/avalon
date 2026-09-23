import type { AudioCallStatus } from "./backend";

export function boundCallChatToSelect(
  status: AudioCallStatus,
  selectedChatId: number | undefined,
): number | undefined {
  if (
    !status.active
    || status.chat_id === null
    || status.chat_id === selectedChatId
  ) {
    return undefined;
  }

  return status.chat_id;
}