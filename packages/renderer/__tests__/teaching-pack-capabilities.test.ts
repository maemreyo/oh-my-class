import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import { z } from "zod";

import { rendererPluginMetadata } from "../src/core/runtime.js";

const manifestUrl = new URL("../../../common/component_strategy_knowledge/capabilities/teaching_pack.json", import.meta.url);
const CapabilityManifestSchema = z.object({ renderer_plugins: z.array(z.string()) });

describe("teaching-pack capability manifest", () => {
  it("declares every runtime renderer plugin", async () => {
    const manifest = CapabilityManifestSchema.parse(
      JSON.parse(await readFile(fileURLToPath(manifestUrl), "utf8")),
    );

    expect(new Set(manifest.renderer_plugins)).toEqual(
      new Set(rendererPluginMetadata().map((plugin) => plugin.kind)),
    );
  });
});
