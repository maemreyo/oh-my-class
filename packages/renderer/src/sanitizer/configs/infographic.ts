import type { IOptions } from "sanitize-html";
import { BASE_CONFIG } from "../base-config.js";

const SVG_TAGS = [
  "svg", "g", "path", "circle", "rect", "line", "polyline", "polygon",
  "text", "tspan", "defs", "linearGradient", "stop", "clipPath", "use",
  "symbol", "title", "desc",
];

export const INFOGRAPHIC_CONFIG: IOptions = {
  ...BASE_CONFIG,
  allowedTags: [...(BASE_CONFIG.allowedTags as string[]), ...SVG_TAGS],
  allowedAttributes: {
    ...BASE_CONFIG.allowedAttributes,
    "svg": ["xmlns", "viewBox", "width", "height", "aria-label", "role"],
    "path": ["d", "fill", "stroke", "stroke-width"],
    "g": ["transform", "fill", "stroke"],
    "text": ["x", "y", "text-anchor", "dominant-baseline", "fill", "font-size"],
    "circle": ["cx", "cy", "r", "fill", "stroke"],
    "rect": ["x", "y", "width", "height", "rx", "ry", "fill", "stroke"],
    "line": ["x1", "y1", "x2", "y2", "stroke", "stroke-width"],
    "linearGradient": ["id", "x1", "y1", "x2", "y2"],
    "stop": ["offset", "stop-color", "stop-opacity"],
    "use": ["href", "x", "y", "width", "height"],
    "polyline": ["points", "fill", "stroke", "stroke-width"],
    "polygon": ["points", "fill", "stroke", "stroke-width"],
    "tspan": ["x", "y", "dx", "dy"],
    "symbol": ["id", "viewBox"],
    "defs": [],
    "clipPath": ["id"],
  },
};
