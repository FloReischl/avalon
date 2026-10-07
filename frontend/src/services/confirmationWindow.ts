import { invoke } from "@tauri-apps/api/core";

export async function showConfirmationWindow(): Promise<void> {
  await invoke("show_confirmation_window");
}

export async function hideConfirmationWindow(): Promise<void> {
  await invoke("hide_confirmation_window");
}

export interface ProactiveConfirmationChat {
  chatId: number;
  agentId: number;
}

export async function showConfirmationWindowForChat(chatId: number, agentId: number): Promise<void> {
  await invoke("show_confirmation_window_for_chat", { chatId, agentId });
}

export async function getProactiveConfirmationChat(): Promise<ProactiveConfirmationChat | null> {
  return invoke<ProactiveConfirmationChat | null>("get_proactive_confirmation_chat");
}
