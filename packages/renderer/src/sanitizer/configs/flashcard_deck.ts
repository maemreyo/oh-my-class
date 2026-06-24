import type { IOptions } from "sanitize-html";
import { BASE_CONFIG } from "../base-config.js";

export const FLASHCARD_DECK_CONFIG: IOptions = {
  ...BASE_CONFIG,
  allowedTags: [
    ...(BASE_CONFIG.allowedTags as string[]),
    "button",
  ],
  allowedAttributes: {
    ...BASE_CONFIG.allowedAttributes,
    "button": ["type", "aria-expanded", "aria-controls", "aria-pressed", "aria-label", "id"],
  },
};
