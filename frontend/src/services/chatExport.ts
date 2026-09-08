import { save } from "@tauri-apps/plugin-dialog";
import { writeTextFile } from "@tauri-apps/plugin-fs";

import {
  getChat,
  type PersistentMessage,
} from "./backend";

export function buildChatMarkdown(
  messages: PersistentMessage[],
  avatarName: string,
): string {
  if (messages.length === 0) {
    return "";
  }

  const sections = messages.map((message) => {
    const role = message.role === "user"
      ? "User"
      : avatarName;

    return `# ${role}\n\n${message.content}`;
  });

  return `${sections.join("\n---\n")}\n`;
}

export function sanitizeChatExportFilename(
  title: string,
): string {
  const sanitized = title
    .replace(/[\u0000-\u001f<>:"/\\|?*]/g, "_")
    .replace(/[. ]+$/g, "")
    .trim();

  return `${sanitized || "chat"}.md`;
}

interface ChatExportDependencies {
  getChat: typeof getChat;
  save: typeof save;
  writeTextFile: typeof writeTextFile;
}

const defaultChatExportDependencies: ChatExportDependencies = {
  getChat,
  save,
  writeTextFile,
};

export async function exportChatToMarkdown(
  chatId: number,
  avatarName: string,
  dependencies: ChatExportDependencies = defaultChatExportDependencies,
): Promise<void> {
  const chat = await dependencies.getChat(chatId);

  const filePath = await dependencies.save({
    defaultPath: sanitizeChatExportFilename(chat.title),
    filters: [
      {
        name: "Markdown",
        extensions: ["md"],
      },
    ],
  });

  if (filePath === null) {
    return;
  }

  await dependencies.writeTextFile(
    filePath,
    buildChatMarkdown(chat.messages, avatarName),
  );
}