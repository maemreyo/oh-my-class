/**
 * DOMPurify server-side sanitization post-render.
 * Layer 3 security requirement.
 */

export function sanitizeHtml(html: string): string {
	// TODO: Use DOMPurify with safe config
	return html;
}
