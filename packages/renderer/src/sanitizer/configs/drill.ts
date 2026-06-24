import type { IOptions } from "sanitize-html";
import { BASE_CONFIG } from "../base-config.js";
import { QUIZ_CONFIG } from "./quiz.js";

// Drill shares the quiz config — MC questions + radio inputs + reveal buttons
export const DRILL_CONFIG: IOptions = QUIZ_CONFIG;

export default DRILL_CONFIG;
