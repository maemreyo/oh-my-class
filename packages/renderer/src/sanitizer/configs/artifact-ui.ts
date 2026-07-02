import type { IOptions } from "sanitize-html";
import { BASE_CONFIG } from "../base-config.js";

/**
 * Sanitizer config for Artifact UI body content.
 *
 * Extends BASE_CONFIG with:
 * - Interactive elements: <button>, <details>, <summary>, <input type="hidden">
 * - SVG primitives for data visualizations (anchor-timeline, controlled-comparison)
 * - <a> with internal anchor hrefs only (#fragment — jump-to-target contract)
 *
 * <style> and <script> blocks live in <head> and are never passed to this config.
 * The existing sanitize() body-extraction pattern handles that invariant.
 */
export const ARTIFACT_UI_CONFIG: IOptions = {
  ...BASE_CONFIG,
  allowedTags: [
    ...(BASE_CONFIG.allowedTags as string[]),
    "button", "details", "summary",
    // SVG for data-viz primitives
    "svg", "g", "path", "circle", "rect", "line", "text", "tspan",
    "defs", "linearGradient", "stop",
  ],
  allowedAttributes: {
    ...BASE_CONFIG.allowedAttributes,
    "button": ["type", "data-toggle-reveal", "data-hide-after-reveal",
               "data-collapsed-label", "data-expanded-label",
               "data-toggle-group", "data-mode-toggle", "data-toggles-group",
               "data-jump-go", "aria-expanded", "aria-controls", "aria-checked"],
    "input":  ["type", "data-jump-input-el", "data-jump-to", "placeholder"],
    "a":      ["href"],   // href validated by exclusiveFilter (only #fragments allowed)
    "svg":    ["viewBox", "xmlns", "width", "height", "aria-hidden", "role"],
    "path":   ["d", "stroke", "fill", "stroke-width", "stroke-linecap"],
    "circle": ["cx", "cy", "r", "fill", "stroke"],
    "rect":   ["x", "y", "width", "height", "rx", "fill"],
    "line":   ["x1", "y1", "x2", "y2", "stroke", "stroke-width"],
    "text":   ["x", "y", "text-anchor", "dominant-baseline", "font-size", "fill"],
    "tspan":  ["x", "dy"],
    "stop":   ["offset", "stop-color", "stop-opacity"],
    "linearGradient": ["id", "x1", "y1", "x2", "y2"],
  },
  exclusiveFilter: (frame) => {
    // Block all http/https src references (from BASE_CONFIG)
    if (frame.attribs.src && !frame.attribs.src.startsWith("data:")) return true;
    // Allow only #fragment hrefs (jump-to-target contract), block all external URLs
    if (frame.attribs.href && !/^#/.test(frame.attribs.href)) return true;
    return false;
  },
};
