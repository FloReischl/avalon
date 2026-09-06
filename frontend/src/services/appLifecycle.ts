import { invoke } from "@tauri-apps/api/core";

export async function exitAvalo(): Promise<void> {
  await invoke("exit_app");
}