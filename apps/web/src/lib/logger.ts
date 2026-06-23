/**
 * Client-side structured logger for oh-my-class.
 * Outputs structured JSON to console in dev; stub for backend POST in prod.
 */

export type LogLevel = "debug" | "info" | "warn" | "error";

export type LogContext = {
	request_id?: string;
	teacher_id?: string;
	run_id?: string;
	step?: number;
	agent?: string;
	[key: string]: unknown;
};

const LEVEL_ORDER: Record<LogLevel, number> = {
	debug: 0,
	info: 1,
	warn: 2,
	error: 3,
};

type ConsoleMethod = "debug" | "info" | "warn" | "error";

export class OMCLogger {
	private context: LogContext;
	private minLevel: LogLevel;

	constructor(options?: { level?: LogLevel }) {
		this.context = {};
		this.minLevel = options?.level ?? "debug";
	}

	bind(context: LogContext): OMCLogger {
		const child = new OMCLogger({ level: this.minLevel });
		child.context = { ...this.context, ...context };
		return child;
	}

	debug(message: string, data?: Record<string, unknown>): void {
		this.log("debug", message, data);
	}

	info(message: string, data?: Record<string, unknown>): void {
		this.log("info", message, data);
	}

	warn(message: string, data?: Record<string, unknown>): void {
		this.log("warn", message, data);
	}

	error(message: string, data?: Record<string, unknown>): void {
		this.log("error", message, data);
	}

	private log(
		level: LogLevel,
		message: string,
		data?: Record<string, unknown>,
	): void {
		if (LEVEL_ORDER[level] < LEVEL_ORDER[this.minLevel]) return;

		const entry = {
			timestamp: new Date().toISOString(),
			level,
			message,
			...this.context,
			...data,
		};

		// Stub: in production, POST to backend logging endpoint
		if (process.env.NODE_ENV === "production") {
			// TODO: replace with actual backend POST
			return;
		}

		const method: ConsoleMethod = level;
		console[method](JSON.stringify(entry));
	}
}

export const logger = new OMCLogger({
	level: (process.env.NODE_ENV === "production" ? "info" : "debug") as LogLevel,
});

export function initGlobalErrorHandlers(logger: OMCLogger): void {
	if (typeof window === "undefined") return;

	window.addEventListener("unhandledrejection", (event) => {
		const reason =
			event.reason instanceof Error
				? { message: event.reason.message, stack: event.reason.stack }
				: { message: String(event.reason) };
		logger.error("Unhandled promise rejection", reason);
	});

	window.addEventListener("error", (event) => {
		logger.error("Uncaught error", {
			message: event.message,
			filename: event.filename,
			lineno: event.lineno,
			colno: event.colno,
		});
	});
}
