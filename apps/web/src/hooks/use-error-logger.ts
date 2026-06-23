"use client";

import { logger } from "@/lib/logger";

export interface UseErrorLoggerReturn {
	logError: (error: Error, extra?: Record<string, unknown>) => void;
}

export function useErrorLogger(componentName?: string): UseErrorLoggerReturn {
	const component = componentName ?? "anonymous";

	const logError = (error: Error, extra?: Record<string, unknown>) => {
		const boundLogger = logger.bind({ component });
		boundLogger.error("Component error", {
			error_message: error.message,
			stack: error.stack,
			...extra,
		});

		try {
			fetch("/webhook/error", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					component,
					error_message: error.message,
					stack: error.stack,
					extra,
					timestamp: new Date().toISOString(),
				}),
			}).catch(() => {
				// Silently ignore fetch failures to never throw to caller
			});
		} catch {
			// Silently ignore any error to never throw to caller
		}
	};

	return { logError };
}
