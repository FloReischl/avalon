import { isTauri } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { createApp } from "vue";

import App from "./App.vue";
import ChatWindow from "./ChatWindow.vue";
import { initializeActiveAvatar } from "./avatar";
import "./styles.css";

async function bootstrap() {
  const avatar = initializeActiveAvatar();
  const currentWindow = isTauri()
    ? getCurrentWindow()
    : undefined;
  const isChatWindow = currentWindow?.label === "chat";

  if (currentWindow) {
    await currentWindow.setTitle(
      isChatWindow ? "Chat Window" : avatar.name,
    );

  }

  createApp(isChatWindow ? ChatWindow : App).mount("#app");
}

void bootstrap().catch((error) => {
  console.error("[startup] failed to initialize Avalo", error);
});

