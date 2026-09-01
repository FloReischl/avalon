import { invoke } from "@tauri-apps/api/core";

export interface InputRegionRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export async function setWindowInputRegions(
  rectangles: InputRegionRect[],
): Promise<void> {
  await invoke("set_window_input_regions", { rectangles });
}
