import type { IOptions } from "sanitize-html";
import { BASE_CONFIG } from "../base-config.js";

export const QUIZ_CONFIG: IOptions = {
  ...BASE_CONFIG,
  allowedTags: [
    ...(BASE_CONFIG.allowedTags as string[]),
    "fieldset", "legend", "label", "input", "button",
  ],
  allowedAttributes: {
    ...BASE_CONFIG.allowedAttributes,
    "input": ["type", "name", "value", "checked", "disabled", "id"],
    "label": ["for"],
    "button": ["type", "aria-expanded", "aria-controls", "id"],
  },
};
