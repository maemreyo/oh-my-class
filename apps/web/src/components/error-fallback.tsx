"use client";

import Link from "next/link";

interface ErrorFallbackProps {
	error: Error;
	resetError: () => void;
}

/**
 * Fallback UI displayed when an error is caught by ErrorBoundary.
 * Renders a styled error panel with error message, retry button, and dashboard link.
 * No external CDN references (invariant-04).
 */
export function ErrorFallback({ error, resetError }: ErrorFallbackProps) {
	return (
		<div className="flex min-h-screen items-center justify-center bg-background p-4">
			<div className="w-full max-w-md rounded-lg border border-border bg-card p-6">
				<div className="mb-4">
					<h2 className="text-lg font-semibold text-foreground">
						Something went wrong
					</h2>
					<p className="mt-2 text-sm text-muted-foreground">
						An unexpected error occurred. Try refreshing the page or go back to
						the dashboard.
					</p>
				</div>

				<div className="mb-6 rounded bg-destructive/10 p-3">
					<p className="font-mono text-xs text-destructive">
						{error.message || "Unknown error"}
					</p>
				</div>

				<div className="flex gap-3">
					<button
						type="button"
						onClick={resetError}
						className="flex-1 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
					>
						Try again
					</button>
					<Link
						href="/runs"
						className="flex-1 rounded-md border border-border bg-card px-4 py-2 text-center text-sm font-medium text-foreground hover:bg-accent transition-colors"
					>
						Go to dashboard
					</Link>
				</div>
			</div>
		</div>
	);
}
