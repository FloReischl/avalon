import { invoke } from "@tauri-apps/api/core";

export async function showChatWindow(): Promise<void> {
  await invoke("show_chat_window");
}