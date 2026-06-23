"use client";

import { useEffect } from "react";
import { ErrorBoundary } from "@/components/error-boundary";
import { initGlobalErrorHandlers, logger } from "@/lib/logger";

interface RootLayoutClientProps {
	children: React.ReactNode;
}

/**
 * Client-side root layout wrapper.
 * Initializes global error handlers and wraps children in ErrorBoundary.
 * Separated from the Server Component root layout to allow metadata export.
 */
export function RootLayoutClient({ children }: RootLayoutClientProps) {
	useEffect(() => {
		initGlobalErrorHandlers(logger);
	}, []);

	return <ErrorBoundary>{children}</ErrorBoundary>;
}
