import { ErrorBoundary } from "@/components/error-boundary";

// SDE-03: the slide deck editor is a dedicated full-screen surface, not part
// of the dashboard's narrow-column run-status chrome — this route group
// deliberately sits outside `(dashboard)` so it never inherits that layout's
// sidebar, even though both groups share the `/runs/...` URL prefix.
export default function DeckEditorLayout({ children }: { children: React.ReactNode }) {
	return (
		<div className="flex h-[100dvh] flex-col overflow-hidden bg-background">
			<ErrorBoundary>{children}</ErrorBoundary>
		</div>
	);
}
