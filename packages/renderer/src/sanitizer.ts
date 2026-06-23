/**
 * Server-side HTML sanitizer — strips dangerous content.
 * Layer 3 security requirement.
 *
 * jsdom is not available in this environment, so sanitization uses
 * targeted regexes covering the threat model: injected scripts, event
 * handlers, and dangerous framing/embedding elements.
 */

// Matches <script ...>...</script> including multiline bodies
const SCRIPT_BLOCK_RE = /<script\b[^>]*>[\s\S]*?<\/script\s*>/gi;
// Matches self-closing <script ... />
const SCRIPT_SELF_CLOSE_RE = /<script\b[^>]*\/>/gi;
// Matches dangerous embedding/framing tags (open, close, or self-close)
const DANGEROUS_TAG_RE = /<\/?\s*(?:iframe|object|embed)\b[^>]*\/?>/gi;
// Matches inline event handlers: on<anything>="..." or on<anything>='...'
const EVENT_HANDLER_RE = /\s+on[a-z]\w*\s*=\s*(?:"[^"]*"|'[^']*'|[^\s/>]*)/gi;

export function sanitizeHtml(html: string): string {
	return html
		.replace(SCRIPT_BLOCK_RE, "")
		.replace(SCRIPT_SELF_CLOSE_RE, "")
		.replace(DANGEROUS_TAG_RE, "")
		.replace(EVENT_HANDLER_RE, "");
}
