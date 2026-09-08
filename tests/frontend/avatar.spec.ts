import { describe, expect, it } from "vitest";

import {
  loadAvatar,
  parseAvatarConfig,
} from "../../frontend/src/avatar";

describe("avatar", () => {
  it("loads the configured active avatar data", () => {
    expect(loadAvatar("frieda1")).toMatchObject({
      name: "Frieda",
      imageUrl: expect.any(String),
    });
  });

  it("rejects an empty avatar name", () => {
    expect(
      () => parseAvatarConfig("name: '   '"),
    ).toThrow("avatar.yaml must contain a non-empty name");
  });

  it("rejects invalid avatar config", () => {
    expect(
      () => parseAvatarConfig("- invalid"),
    ).toThrow("avatar.yaml must contain a YAML object");
  });

  it("rejects a missing avatar", () => {
    expect(
      () => loadAvatar("does-not-exist"),
    ).toThrow(
      "Required avatar asset is missing: ./assets/avatars/does-not-exist/avatar.yaml",
    );
  });
});