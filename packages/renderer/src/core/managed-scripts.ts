import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

import { RendererError, RendererErrorCategory, RendererErrorCode } from "./errors.js";
import type { ManagedScript, ManagedScriptDeclaration } from "./types.js";

function sha256(source: string): string {
  return createHash("sha256").update(source).digest("hex");
}

export function loadManagedScripts(declarations: readonly ManagedScriptDeclaration[] = []): readonly ManagedScript[] {
  return declarations.map((declaration) => {
    const source = readFileSync(declaration.sourcePath, "utf8");
    const digest = sha256(source);
    if (digest !== declaration.sha256) {
      throw new RendererError({
        code: RendererErrorCode.ExternalAsset,
        category: RendererErrorCategory.Policy,
        message: `Managed script hash mismatch for ${declaration.id}.`,
        details: { id: declaration.id, expected: declaration.sha256, actual: digest },
      });
    }
    return { id: declaration.id, source, sha256: digest };
  });
}

export function hashManagedScriptSource(source: string): string {
  return sha256(source);
}
