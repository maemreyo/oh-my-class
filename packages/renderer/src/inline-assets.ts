/**
 * Inlines CSS and validates no external URLs in final HTML output.
 * INVARIANT-04: HTML output MUST NOT contain any http(s):// asset reference.
 */

const _EXTERNAL_URL_PATTERN = /(?:href|src)\s*=\s*["']https?:\/\//gi;

export function inlineCss(html: string, _cssContent: string): string {
	// TODO: Inject CSS into <style> tag within HTML
	return html;
}

export function validateNoExternalUrls(_html: string): string[] {
	const violations: string[] = [];
	// TODO: Scan html for EXTERNAL_URL_PATTERN matches
	return violations;
}
