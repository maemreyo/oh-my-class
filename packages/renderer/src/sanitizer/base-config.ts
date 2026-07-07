import type { IOptions } from "sanitize-html";

/**
 * Baseline allowlist used by all artifact types.
 * Each type extends this — never restricts below it.
 * Blocks all external URLs (only data: URIs allowed).
 */
export const BASE_CONFIG: IOptions = {
  allowedTags: [
    // structure
    "html", "head", "body", "main", "header", "footer", "section", "article",
    "aside", "nav",
    // headings + text
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "strong", "em", "b",
    "i", "u", "s",
    // lists
    "ul", "ol", "li", "dl", "dt", "dd",
    // tables
    "table", "thead", "tbody", "tr", "th", "td", "caption", "colgroup", "col",
    // media (inline only)
    "img", "figure", "figcaption",
    // semantic
    "blockquote", "pre", "code", "abbr", "mark", "time", "cite", "q",
    "button",
    // layout
    "div", "br", "hr",
    // meta (for base.html <head>)
    "meta", "title", "style", "link",
  ],
  allowedAttributes: {
    "*": [
      "class", "id", "lang", "dir",
      "aria-label", "aria-labelledby", "aria-describedby", "aria-hidden",
      "aria-expanded", "aria-controls", "aria-live", "aria-checked",
      "role", "tabindex", "data-*", "hidden",
    ],
    "a": ["href"],
    "button": ["type", "disabled", "aria-disabled"],
    "img": ["src", "alt", "loading", "decoding", "width", "height"],
    "meta": ["charset", "name", "content", "http-equiv"],
    "link": ["rel", "type"],
    "time": ["datetime"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
    "col": ["span"],
    "style": [],
  },
  allowedSchemes: ["data"],
  allowedSchemesAppliedToAttributes: ["src"],
  allowedClasses: { "*": ["*"] },
  exclusiveFilter: (frame) => {
    if (frame.attribs.src && !frame.attribs.src.startsWith("data:")) return true;
    if (frame.attribs.href && /^(https?:|javascript:)/i.test(frame.attribs.href)) return true;
    return false;
  },
};
