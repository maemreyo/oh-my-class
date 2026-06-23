"use client";

import React from "react";
import { logger } from "@/lib/logger";
import { ErrorFallback } from "./error-fallback";

interface ErrorBoundaryProps {
	children: React.ReactNode;
	fallback?: (error: Error, resetError: () => void) => React.ReactNode;
}

interface ErrorBoundaryState {
	hasError: boolean;
	error: Error | null;
}

/**
 * Error boundary that catches React component errors and renders a fallback UI.
 * Logs errors via the structured logger with component stack context.
 * Class component required for React.Component.getDerivedStateFromError + componentDidCatch.
 */
export class ErrorBoundary extends React.Component<
	ErrorBoundaryProps,
	ErrorBoundaryState
> {
	constructor(props: ErrorBoundaryProps) {
		super(props);
		this.state = {
			hasError: false,
			error: null,
		};
	}

	/**
	 * Update state so the next render will show the fallback UI.
	 * Called after an error has been thrown by a descendant component.
	 */
	static getDerivedStateFromError(error: Error): ErrorBoundaryState {
		return {
			hasError: true,
			error,
		};
	}

	/**
	 * Log the error and component stack for debugging.
	 * Called after an error has been thrown by a descendant component.
	 */
	componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
		logger.error("React component error caught", {
			component_stack: errorInfo.componentStack,
			error_message: error.message,
		});
	}

	/**
	 * Reset the error boundary state, allowing the UI to recover.
	 */
	resetError = (): void => {
		this.setState({
			hasError: false,
			error: null,
		});
	};

	render(): React.ReactNode {
		if (this.state.hasError && this.state.error) {
			return (
				this.props.fallback?.(this.state.error, this.resetError) ?? (
					<ErrorFallback
						error={this.state.error}
						resetError={this.resetError}
					/>
				)
			);
		}

		return this.props.children;
	}
}
