"use client";

import { useParams } from "next/navigation";
import { useUnit } from "@/hooks/use-unit";
import { UnitSessionCard } from "@/components/unit-session-card";

export default function UnitWorkspacePage() {
	const params = useParams();
	const parentRunId = params.parentRunId as string;
	const { data, isLoading, error, approveAll, spawnAnyway, exportUnit } = useUnit(parentRunId);

	if (isLoading) {
		return (
			<div className="p-8 text-center text-gray-500">
				Loading unit workspace…
			</div>
		);
	}

	if (error || !data) {
		return (
			<div className="p-8 text-center text-red-600">
				Failed to load unit. {String(error ?? "Not found.")}
			</div>
		);
	}

	const { sequence, sessions, aggregate, coherence_warnings: coherenceWarnings } = data;
	const groundingStatus = sequence.grounding_status;
	const showGroundingBanner = groundingStatus === "partial" || groundingStatus === "ungrounded";
	const approvalProgress = Math.round(
		(aggregate.approved_sessions / aggregate.total_sessions) * 100,
	);

	return (
		<div className="p-6 max-w-5xl mx-auto space-y-6">
			{/* Page header */}
			<div className="flex items-start justify-between gap-4">
				<div>
					<h1 className="text-2xl font-semibold text-gray-900">{sequence.topic}</h1>
					<p className="text-sm text-gray-500 mt-1">
						{sequence.grade_level} · {sequence.subject} · {sequence.locale}
					</p>
				</div>
				<div className="flex gap-2 shrink-0">
					<button
						type="button"
						onClick={() => void approveAll()}
						className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
					>
						Approve all
					</button>
					<button
						type="button"
						onClick={() => void exportUnit()}
						className="px-4 py-2 bg-gray-100 text-gray-800 rounded-md text-sm font-medium hover:bg-gray-200 transition-colors"
					>
						Export unit
					</button>
				</div>
			</div>

			{/* Progress banner */}
			<div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
				<div className="flex items-center justify-between text-sm">
					<span className="text-gray-600">
						<span className="font-semibold text-gray-900">{aggregate.approved_sessions}</span>
						/{aggregate.total_sessions} sessions approved
					</span>
					<span
						className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
							aggregate.status === "complete"
								? "bg-green-100 text-green-800"
								: aggregate.status === "partially_complete"
									? "bg-yellow-100 text-yellow-800"
									: "bg-blue-100 text-blue-800"
						}`}
					>
						{aggregate.status.replace(/_/g, " ")}
					</span>
				</div>
				<div className="mt-2 h-1.5 bg-gray-200 rounded-full overflow-hidden">
					<div
						className="h-full bg-blue-500 rounded-full transition-all"
						style={{ width: `${approvalProgress}%` }}
					/>
				</div>
			</div>

			{/* Grounding warning banner */}
			{showGroundingBanner && (
				<div
					role="alert"
					className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
				>
					<span className="font-medium">Grounding: {groundingStatus}.</span> This sequence was
					generated with limited curriculum grounding. Review all sessions carefully before
					approving.
				</div>
			)}

			{/* Coherence warnings */}
			{coherenceWarnings.length > 0 && (
				<div
					role="alert"
					className="rounded-lg border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-800 space-y-1"
				>
					<p className="font-medium">Advisory coherence warnings:</p>
					<ul className="list-disc ml-4 space-y-0.5">
						{coherenceWarnings.map((w) => (
							<li key={`${w.code}-${w.session_ids.join("-")}`}>{w.message}</li>
						))}
					</ul>
				</div>
			)}

			{/* Session cards */}
			<div className="space-y-3">
				{sessions.map((sessionProgress) => {
					const sessionPlan = sequence.sessions.find(
						(s) => s.session_id === sessionProgress.session_id,
					);

					return (
						<UnitSessionCard
							key={sessionProgress.session_id}
							sessionProgress={sessionProgress}
							sessionPlan={sessionPlan}
							onReview={
								sessionProgress.child_run_id
									? () => window.open(`/runs/${sessionProgress.child_run_id}`, "_blank")
									: undefined
							}
							onRetry={
								sessionProgress.status === "failed"
									? () => void spawnAnyway(sessionProgress.session_id)
									: undefined
							}
							onForceStart={
								sessionProgress.status === "blocked"
									? () => void spawnAnyway(sessionProgress.session_id)
									: undefined
							}
						/>
					);
				})}
			</div>
		</div>
	);
}
