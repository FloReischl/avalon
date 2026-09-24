import { invoke } from "@tauri-apps/api/core";

export async function exitAvalon(): Promise<void> {
  await invoke("exit_app");
}