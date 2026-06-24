import type { IOptions } from "sanitize-html";
import { BASE_CONFIG } from "../base-config.js";

// Reading passage is a static reading artifact — no interactive form elements
export const READING_PASSAGE_CONFIG: IOptions = BASE_CONFIG;

export default READING_PASSAGE_CONFIG;
