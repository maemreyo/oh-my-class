/**
 * Inlines CSS and validates no external URLs in final HTML output.
 * INVARIANT-04: HTML output MUST NOT contain any http(s):// asset reference.
 */

const EXTERNAL_URL_PATTERN = /(?:href|src)\s*=\s*["']https?:\/\/[^"']+["']/gi;

export function inlineCss(html: string, cssContent: string): string {
	const styleTag = `<style>\n${cssContent}\n</style>`;
	// Inject before </head> if present, otherwise prepend
	if (html.includes("</head>")) {
		return html.replace("</head>", `${styleTag}\n</head>`);
	}
	return `${styleTag}\n${html}`;
}

export function validateNoExternalUrls(html: string): string[] {
	const violations: string[] = [];
	let match: RegExpExecArray | null;
	const re = new RegExp(EXTERNAL_URL_PATTERN.source, "gi");
	while ((match = re.exec(html)) !== null) {
		violations.push(match[0]);
	}
	return violations;
}
