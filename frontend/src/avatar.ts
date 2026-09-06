import { parse } from "yaml";

export const ACTIVE_AVATAR_ID = "frieda1";

export type Avatar = {
  name: string;
  imageUrl: string;
};

type AvatarConfig = {
  name: string;
};

const avatarYamlFiles = import.meta.glob(
  "./assets/avatars/*/avatar.yaml",
  {
    eager: true,
    query: "?raw",
    import: "default",
  },
) as Record<string, string>;

const avatarImageFiles = import.meta.glob(
  "./assets/avatars/*/standard.png",
  {
    eager: true,
    query: "?url",
    import: "default",
  },
) as Record<string, string>;

let activeAvatar: Avatar | undefined;

function requireAsset(
  files: Record<string, string>,
  path: string,
): string {
  const value = files[path];

  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Required avatar asset is missing: ${path}`);
  }

  return value;
}

export function parseAvatarConfig(raw: string): AvatarConfig {
  const parsed = parse(raw);

  if (
    parsed === null
    || typeof parsed !== "object"
    || Array.isArray(parsed)
  ) {
    throw new Error("avatar.yaml must contain a YAML object");
  }

  const name = (parsed as Record<string, unknown>).name;

  if (typeof name !== "string" || name.trim().length === 0) {
    throw new Error("avatar.yaml must contain a non-empty name");
  }

  return {
    name: name.trim(),
  };
}

export function loadAvatar(id: string): Avatar {
  const yamlPath = `./assets/avatars/${id}/avatar.yaml`;
  const imagePath = `./assets/avatars/${id}/standard.png`;

  const config = parseAvatarConfig(
    requireAsset(avatarYamlFiles, yamlPath),
  );

  return {
    name: config.name,
    imageUrl: requireAsset(avatarImageFiles, imagePath),
  };
}

export function initializeActiveAvatar(): Avatar {
  activeAvatar = loadAvatar(ACTIVE_AVATAR_ID);
  return activeAvatar;
}

export function getActiveAvatar(): Avatar {
  activeAvatar ??= loadAvatar(ACTIVE_AVATAR_ID);
  return activeAvatar;
}