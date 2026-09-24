import { invoke } from "@tauri-apps/api/core";

export async function showPermissionsWindow(): Promise<void> {
  await invoke("show_permissions_window");
}
