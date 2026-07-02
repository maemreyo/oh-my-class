import { RendererError, RendererErrorCategory, RendererErrorCode } from "./errors.js";
import type { ArtifactKindPlugin, PluginMetadata } from "./types.js";

export class PluginRegistry {
  readonly #plugins = new Map<string, ArtifactKindPlugin<Record<string, unknown>>>();

  register(plugin: ArtifactKindPlugin<Record<string, unknown>>): void {
    if (this.#plugins.has(plugin.kind)) {
      throw new RendererError({
        code: RendererErrorCode.DuplicateKind,
        category: RendererErrorCategory.Registry,
        message: `Renderer plugin kind already registered: ${plugin.kind}`,
        details: { kind: plugin.kind },
      });
    }
    this.#plugins.set(plugin.kind, plugin);
  }

  get(kind: string): ArtifactKindPlugin<Record<string, unknown>> {
    const plugin = this.#plugins.get(kind);
    if (plugin) return plugin;
    throw new RendererError({
      code: RendererErrorCode.UnknownKind,
      category: RendererErrorCategory.Registry,
      message: `Renderer plugin kind is not registered: ${kind}`,
      details: { kind },
    });
  }

  metadata(): readonly PluginMetadata[] {
    return [...this.#plugins.values()].map((plugin) => ({
      kind: plugin.kind,
      version: plugin.version,
      templateVersion: plugin.templateVersion,
      themeVersion: plugin.themeVersion,
      supportedAudiences: plugin.audience.supported,
      supportsPrint: plugin.capabilities.supportsPrint,
      sanitizerPolicyVersion: plugin.sanitizerPolicy.version,
    }));
  }
}

export function createPluginRegistry(plugins: readonly ArtifactKindPlugin<Record<string, unknown>>[]): PluginRegistry {
  const registry = new PluginRegistry();
  for (const plugin of plugins) registry.register(plugin);
  return registry;
}
