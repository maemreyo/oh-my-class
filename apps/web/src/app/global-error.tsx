"use client";

import { logger } from "@/lib/logger";

/**
 * global-error.tsx — Catch-all error handler for the entire application.
 * Must be a Client Component with its own <html> and <body> tags (Next.js requirement).
 * Renders minimal error UI with inline critical CSS since it renders OUTSIDE the root layout.
 * Logs to structured logger and provides a reset mechanism.
 * No external CDN references (invariant-04).
 */
export default function GlobalError({
	error,
	reset,
}: {
	error: Error & { digest?: string };
	reset: () => void;
}) {
	// Log the critical error
	logger.error("Global application error", {
		message: error.message,
		digest: error.digest,
		stack: error.stack,
	});

	return (
		<html lang="vi">
			<head>
				<title>Error — oh-my-class</title>
				<meta charSet="utf-8" />
				<meta name="viewport" content="width=device-width, initial-scale=1" />
				<style>{`
					* {
						margin: 0;
						padding: 0;
						box-sizing: border-box;
					}
					html, body {
						width: 100%;
						height: 100%;
						font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
						background-color: #f9fafb;
						color: #1f2937;
					}
					body {
						display: flex;
						align-items: center;
						justify-content: center;
						padding: 1rem;
					}
					.container {
						max-width: 28rem;
						width: 100%;
						border-radius: 0.5rem;
						border: 1px solid #e5e7eb;
						background-color: #ffffff;
						padding: 1.5rem;
					}
					h1 {
						font-size: 1.125rem;
						font-weight: 600;
						margin-bottom: 0.5rem;
					}
					p {
						font-size: 0.875rem;
						color: #6b7280;
						margin-top: 0.5rem;
					}
					.error-box {
						margin-top: 1.5rem;
						margin-bottom: 1.5rem;
						border-radius: 0.375rem;
						background-color: #fee2e2;
						padding: 0.75rem;
					}
					.error-box p {
						font-family: 'Courier New', monospace;
						font-size: 0.75rem;
						color: #dc2626;
						margin: 0;
					}
					.button-group {
						display: flex;
						gap: 0.75rem;
					}
					button {
						flex: 1;
						border-radius: 0.375rem;
						padding: 0.5rem 1rem;
						font-size: 0.875rem;
						font-weight: 500;
						cursor: pointer;
						border: none;
						transition: background-color 0.2s;
					}
					.button-primary {
						background-color: #3b82f6;
						color: #ffffff;
					}
					.button-primary:hover {
						background-color: #2563eb;
					}
					.button-secondary {
						background-color: #e5e7eb;
						color: #1f2937;
						border: 1px solid #d1d5db;
					}
					.button-secondary:hover {
						background-color: #f3f4f6;
					}
				`}</style>
			</head>
			<body>
				<div className="container">
					<div>
						<h1>Something went wrong</h1>
						<p>
							A critical error occurred. Try refreshing the page or contact
							support if the problem persists.
						</p>
					</div>

					<div className="error-box">
						<p>{error.message || "Unknown error"}</p>
						{error.digest && (
							<p style={{ marginTop: "0.5rem" }}>ID: {error.digest}</p>
						)}
					</div>

					<div className="button-group">
						<button type="button" className="button-primary" onClick={reset}>
							Try again
						</button>
						<button
							type="button"
							className="button-secondary"
							onClick={() => {
								window.location.href = "/";
							}}
						>
							Go home
						</button>
					</div>
				</div>
			</body>
		</html>
	);
}
