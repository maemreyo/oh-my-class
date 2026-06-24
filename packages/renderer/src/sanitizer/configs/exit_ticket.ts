import type { IOptions } from "sanitize-html";
import { WORKSHEET_CONFIG } from "./worksheet.js";

// Exit ticket has short-answer fields and optional MC radio inputs — same as worksheet
export const EXIT_TICKET_CONFIG: IOptions = WORKSHEET_CONFIG;

export default EXIT_TICKET_CONFIG;
