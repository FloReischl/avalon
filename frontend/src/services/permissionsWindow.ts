import { invoke } from "@tauri-apps/api/core";

export async function showPermissionsWindow(): Promise<void> {
  await invoke("show_permissions_window");
}

export async function showPermissionsWindowForChat(chatId: number): Promise<void> {
  await invoke("show_permissions_window_for_chat", { chatId });
}

export async function getProactivePermissionsChatId(): Promise<number | null> {
  return invoke<number | null>("get_proactive_permissions_chat_id");
}
