"use client";

import type { UnitSessionProgress, SessionPlan } from "@/hooks/use-unit";

export type { SessionPlan };

export interface UnitSessionCardProps {
	sessionProgress: UnitSessionProgress;
	sessionPlan?: SessionPlan;
	onReview?: () => void;
	onRetry?: () => void;
	onForceStart?: () => void;
}

const STATUS_CONFIG: Record<
	UnitSessionProgress["status"],
	{ label: string; colorClass: string; bgClass: string }
> = {
	pending:    { label: "Pending",     colorClass: "text-gray-600",  bgClass: "bg-gray-100"  },
	generating: { label: "Generating…", colorClass: "text-blue-700",  bgClass: "bg-blue-100"  },
	in_review:  { label: "In review",   colorClass: "text-amber-700", bgClass: "bg-amber-100" },
	approved:   { label: "Approved",    colorClass: "text-green-700", bgClass: "bg-green-100" },
	failed:     { label: "Failed",      colorClass: "text-red-700",   bgClass: "bg-red-100"   },
	blocked:    { label: "Blocked",     colorClass: "text-orange-700",bgClass: "bg-orange-100"},
};

export function UnitSessionCard({
	sessionProgress,
	sessionPlan,
	onReview,
	onRetry,
	onForceStart,
}: UnitSessionCardProps) {
	const { status, progress_percent, session_id } = sessionProgress;
	const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;

	return (
		<div className="rounded-lg border border-gray-200 bg-white px-4 py-3 flex items-start gap-4">
			{/* Order index badge */}
			<div
				aria-hidden="true"
				className="shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-600"
			>
				{sessionPlan?.order_index ?? "–"}
			</div>

			{/* Content */}
			<div className="flex-1 min-w-0">
				<div className="flex items-center gap-2 flex-wrap">
					<span className="text-sm font-medium text-gray-900 truncate">
						{sessionPlan?.title ?? session_id}
					</span>
					<span
						className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg.bgClass} ${cfg.colorClass}`}
					>
						{cfg.label}
					</span>
				</div>

				{sessionPlan && (
					<p className="text-xs text-gray-500 mt-0.5 truncate">
						{sessionPlan.sub_topic} · {sessionPlan.duration_minutes}min ·{" "}
						<span className="font-medium">{sessionPlan.bloom_level_primary}</span> ·{" "}
						{sessionPlan.methodology_primary}
					</p>
				)}

				{/* Progress bar — only shown while generating */}
				{status === "generating" && (
					<div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden w-full">
						<div
							className="h-full bg-blue-500 rounded-full transition-all"
							style={{ width: `${progress_percent}%` }}
						/>
					</div>
				)}

				{/* Prerequisites */}
				{sessionPlan && sessionPlan.prerequisite_sessions.length > 0 && (
					<p className="mt-1.5 text-xs text-gray-400">
						Requires: {sessionPlan.prerequisite_sessions.join(", ")}
					</p>
				)}
			</div>

			{/* Action buttons — conditioned on status */}
			<div className="shrink-0 flex gap-2 items-center">
				{onReview && (
					<button
						type="button"
						onClick={onReview}
						className="text-xs px-2.5 py-1 rounded border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
					>
						Review
					</button>
				)}
				{onRetry && status === "failed" && (
					<button
						type="button"
						onClick={onRetry}
						className="text-xs px-2.5 py-1 rounded border border-red-300 text-red-700 hover:bg-red-50 transition-colors"
					>
						Retry
					</button>
				)}
				{onForceStart && status === "blocked" && (
					<button
						type="button"
						onClick={onForceStart}
						className="text-xs px-2.5 py-1 rounded border border-orange-300 text-orange-700 hover:bg-orange-50 transition-colors"
					>
						Start anyway
					</button>
				)}
			</div>
		</div>
	);
}
