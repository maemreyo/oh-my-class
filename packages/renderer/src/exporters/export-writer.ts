import { render } from "../core/render.js";
import type { ManifestStore, RenderedDocument } from "../core/manifest-store.js";
import type { RenderRequest } from "../core/types.js";
import type { PluginRegistry } from "../core/registry.js";
import type { ThemeResolver } from "../core/theme-resolver.js";

type ExportWriterOptions = {
  readonly registry?: PluginRegistry;
  readonly themeResolver?: ThemeResolver;
};

export class ExportWriter {
  readonly #store: ManifestStore;

  constructor(store: ManifestStore) {
    this.#store = store;
  }

  write(requestId: string): RenderedDocument | undefined {
    return this.#store.get(requestId);
  }

  async rerender(request: RenderRequest, options: ExportWriterOptions = {}): Promise<RenderedDocument> {
    const response = await render(request, options);
    return this.#store.put(request.context.requestId, response.html, response.manifest);
  }

  storeResponse(response: { html: string; manifest: import("../core/types.js").RenderManifest }, requestId: string): RenderedDocument {
    return this.#store.put(requestId, response.html, response.manifest);
  }
}
