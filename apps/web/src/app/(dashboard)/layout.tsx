"use client";

import { ErrorBoundary } from "@/components/error-boundary";

export default function DashboardLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<div className="flex min-h-[100dvh] flex-col md:flex-row">
			{/* Sidebar */}
			<aside className="w-full border-b border-border bg-card p-4 md:w-64 md:border-b-0 md:border-r">
				<h1 className="text-lg font-semibold">oh-my-class</h1>
					<nav className="mt-6 space-y-1">
						<a
							href="/runs/new"
							className="block rounded-md px-3 py-2 text-sm hover:bg-accent"
						>
							New pack
						</a>
						<a
							href="/runs"
						className="block rounded-md px-3 py-2 text-sm hover:bg-accent"
					>
						Runs
					</a>
					<a
						href="/approvals"
						className="block rounded-md px-3 py-2 text-sm hover:bg-accent"
					>
						Approvals
					</a>
					<a
						href="/effectiveness"
						className="block rounded-md px-3 py-2 text-sm hover:bg-accent"
					>
						Effectiveness
					</a>
				</nav>
			</aside>

			{/* Main content */}
			<main className="min-w-0 flex-1 p-4 md:p-6">
				<ErrorBoundary>{children}</ErrorBoundary>
			</main>
		</div>
	);
}
