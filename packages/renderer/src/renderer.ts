/**
 * Core renderer — takes ArtifactContent JSON and produces standalone HTML.
 * Uses Eta templates. All output is self-contained: no CDN, no external assets.
 */

import type { ArtifactContent } from "@oh-my-class/schemas";

export function renderArtifact(_data: ArtifactContent): string {
	// TODO: Select template based on data.artifact_type
	// TODO: Render via Eta template engine
	// TODO: Inline all CSS from branding/theme_{data.theme}.css
	// TODO: Run sanitizer
	throw new Error("Not yet implemented");
}

export function renderTemplate(
	_templateName: string,
	_data: Record<string, unknown>,
): string {
	// TODO: Use Eta to render template
	throw new Error("Not yet implemented");
}
