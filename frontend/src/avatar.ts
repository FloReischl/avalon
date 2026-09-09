import { parse } from "yaml";

import avatarConfig from "./assets/avatars/frieda1/avatar.yaml?raw";
import avatarImageUrl from "./assets/avatars/frieda1/standard.png?url";

export const ACTIVE_AVATAR_ID = "frieda1";


export type Avatar = {
  name: string;
  imageUrl: string;
};

type AvatarConfig = {
  name: string;
};

type AvatarAssets = {
  config: string;
  imageUrl: string;
};

const avatarAssets: Record<string, AvatarAssets> = {
  frieda1: {
    config: avatarConfig,
    imageUrl: avatarImageUrl,
  },
};

let activeAvatar: Avatar | undefined;

function requireAvatarAssets(id: string): AvatarAssets {
  const assets = avatarAssets[id];

  if (!assets) {
    throw new Error(`Required avatar asset is missing: ./assets/avatars/${id}/avatar.yaml`);
  }

  return assets;
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
  const assets = requireAvatarAssets(id);
  const config = parseAvatarConfig(assets.config);

  return {
    name: config.name,
    imageUrl: assets.imageUrl,
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