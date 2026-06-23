import Link from "next/link";

/**
 * not-found.tsx — 404 page for unmatched routes.
 * Server component (no "use client" needed for static 404 page).
 * Renders a friendly 404 UI with navigation back to dashboard.
 * No external CDN references (invariant-04).
 */
export default function NotFound() {
	return (
		<div className="flex min-h-screen items-center justify-center bg-background p-4">
			<div className="w-full max-w-md rounded-lg border border-border bg-card p-6 text-center">
				<div className="mb-6">
					<h1 className="text-4xl font-bold text-foreground">404</h1>
					<h2 className="mt-4 text-lg font-semibold text-foreground">
						Page not found
					</h2>
					<p className="mt-2 text-sm text-muted-foreground">
						The page you're looking for doesn't exist or has been moved.
					</p>
				</div>

				<div className="flex flex-col gap-3">
					<Link
						href="/runs"
						className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
					>
						Back to dashboard
					</Link>
					<Link
						href="/"
						className="rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
					>
						Go to home
					</Link>
				</div>
			</div>
		</div>
	);
}
