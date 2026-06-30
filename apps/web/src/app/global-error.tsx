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
						background-color: Canvas;
						color: CanvasText;
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
						border: 1px solid GrayText;
						background-color: Canvas;
						padding: 1.5rem;
					}
					h1 {
						font-size: 1.125rem;
						font-weight: 600;
						margin-bottom: 0.5rem;
					}
					p {
						font-size: 0.875rem;
						color: GrayText;
						margin-top: 0.5rem;
					}
					.error-box {
						margin-top: 1.5rem;
						margin-bottom: 1.5rem;
						border-radius: 0.375rem;
						background-color: Mark;
						padding: 0.75rem;
					}
					.error-box p {
						font-family: 'Courier New', monospace;
						font-size: 0.75rem;
						color: MarkText;
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
						background-color: Highlight;
						color: HighlightText;
					}
					.button-primary:hover {
						filter: brightness(0.92);
					}
					.button-secondary {
						background-color: ButtonFace;
						color: ButtonText;
						border: 1px solid GrayText;
					}
					.button-secondary:hover {
						filter: brightness(0.96);
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
