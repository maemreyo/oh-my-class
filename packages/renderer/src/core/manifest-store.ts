import type { RenderManifest } from "./types.js";

export type RenderedDocument = {
  readonly html: string;
  readonly manifest: RenderManifest;
  readonly storedAt: string;
};

export class ManifestStore {
  readonly #store = new Map<string, RenderedDocument>();

  put(requestId: string, html: string, manifest: RenderManifest): RenderedDocument {
    const doc: RenderedDocument = { html, manifest, storedAt: new Date().toISOString() };
    this.#store.set(requestId, doc);
    return doc;
  }

  get(requestId: string): RenderedDocument | undefined {
    return this.#store.get(requestId);
  }

  has(requestId: string): boolean {
    return this.#store.has(requestId);
  }

  delete(requestId: string): boolean {
    return this.#store.delete(requestId);
  }

  size(): number {
    return this.#store.size;
  }
}
