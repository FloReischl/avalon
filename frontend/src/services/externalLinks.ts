import { isTauri } from "@tauri-apps/api/core";
import { openUrl } from "@tauri-apps/plugin-opener";

const EXTERNAL_PROTOCOLS = new Set([
  "http:",
  "https:",
  "mailto:",
  "tel:",
]);

export async function openExternalLink(href: string): Promise<void> {
  const url = new URL(href, window.location.href);

  if (!EXTERNAL_PROTOCOLS.has(url.protocol)) {
    throw new Error(`Unsupported external link protocol: ${url.protocol}`);
  }

  if (isTauri()) {
    await openUrl(url.href);
    return;
  }

  window.open(url.href, "_blank", "noopener,noreferrer");
}
