import type { IOptions } from "sanitize-html";
import { BASE_CONFIG } from "../base-config.js";

export const LESSON_CONFIG: IOptions = {
  ...BASE_CONFIG,
  allowedTags: [
    ...(BASE_CONFIG.allowedTags as string[]),
    "a", "details", "summary",
  ],
};
