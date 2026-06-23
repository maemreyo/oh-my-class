export default function DashboardLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<div className="flex min-h-screen">
			{/* Sidebar */}
			<aside className="w-64 border-r border-border bg-card p-4">
				<h1 className="text-lg font-semibold">oh-my-class</h1>
				<nav className="mt-6 space-y-1">
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
				</nav>
			</aside>

			{/* Main content */}
			<main className="flex-1 p-6">{children}</main>
		</div>
	);
}
