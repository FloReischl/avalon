import { invoke } from "@tauri-apps/api/core";

export async function showPermissionsWindow(): Promise<void> {
  await invoke("show_permissions_window");
}

export interface ProactivePermissionsChat {
  chatId: number;
  principalId: number;
}

export async function showPermissionsWindowForChat(
  chatId: number,
  principalId: number,
): Promise<void> {
  await invoke("show_permissions_window_for_chat", { chatId, principalId });
}

export async function getProactivePermissionsChat(): Promise<ProactivePermissionsChat | null> {
  return invoke<ProactivePermissionsChat | null>("get_proactive_permissions_chat");
}
