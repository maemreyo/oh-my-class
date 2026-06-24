import type { IOptions } from "sanitize-html";
import { QUIZ_CONFIG } from "./quiz.js";

// Answer key shows all answers with explanations — same allowlist as quiz
export const ANSWER_KEY_CONFIG: IOptions = QUIZ_CONFIG;

export default ANSWER_KEY_CONFIG;
