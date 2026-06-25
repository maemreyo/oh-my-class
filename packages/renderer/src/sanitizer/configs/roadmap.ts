import type { IOptions } from "sanitize-html";
import { BASE_CONFIG } from "../base-config.js";

export const ROADMAP_CONFIG: IOptions = {
  ...BASE_CONFIG,
  allowedTags: [
    ...(BASE_CONFIG.allowedTags as string[] ?? []),
    "section", "article", "aside", "nav", "header", "main", "footer",
    "figure", "figcaption", "details", "summary",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tr", "th", "td",
    "div", "span", "b", "i", "em", "strong", "small", "mark", "del", "ins",
    "a", "button",
  ],
  allowedAttributes: {
    ...(BASE_CONFIG.allowedAttributes as Record<string, string[]> ?? {}),
    "*": ["class", "id", "aria-label", "aria-labelledby", "role", "tabindex", "style"],
    "a": ["href", "target", "rel"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
  },
};

export default ROADMAP_CONFIG;
