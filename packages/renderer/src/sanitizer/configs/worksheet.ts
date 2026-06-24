import type { IOptions } from "sanitize-html";
import { BASE_CONFIG } from "../base-config.js";

export const WORKSHEET_CONFIG: IOptions = {
  ...BASE_CONFIG,
  allowedTags: [
    ...(BASE_CONFIG.allowedTags as string[]),
    "fieldset", "legend", "label", "input", "textarea", "button",
  ],
  allowedAttributes: {
    ...BASE_CONFIG.allowedAttributes,
    "input": ["type", "name", "value", "placeholder", "id"],
    "textarea": ["name", "rows", "cols", "placeholder", "id"],
    "label": ["for"],
    "button": ["type", "aria-expanded", "aria-controls", "id"],
  },
};
