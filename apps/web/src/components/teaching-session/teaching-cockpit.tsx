"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { gatewayUrl } from "@/lib/api-client";
import { AiBlockRewriteConfirmModal } from "@/components/slide-deck-editor/ai-block-rewrite-confirm-modal";
import { resolveRewriteSuggestionPayload } from "@/components/slide-deck-editor/block-rewrite-controls";
import { usePacingNudgePreference, useSetPacingNudgePreference } from "@/hooks/use-pacing-nudge-preference";
import {
	useTeachingSessionLive,
	type TeachingSessionLiveEvent,
} from "@/hooks/use-teaching-session-live";
import type { SessionRole } from "@/lib/session-token";
import {
	BRANCH_CONTENT_TYPES,
	type BranchContentType,
	isBehindPace,
	isControllerRole,
	nextActionHint,
	shouldClearAnnotation,
} from "./teaching-cockpit-logic";

export interface BranchOption {
	/** The slide the branch lives on -- validated content, supplied by the
	 * caller (deck data), never invented by the cockpit itself. */
	readonly slide_id: string;
	readonly branch_id: string;
	readonly label: string;
}

export interface TeachingCockpitProps {
	readonly sessionId: string;
	readonly sessionToken: string;
	readonly role: SessionRole;
	/** Validated branch options for the *current* slide (base AC5: branch
	 * actions map to validated content, never gated suggestions the cockpit
	 * invented). Empty when the current slide has no branches. */
	readonly branchOptions?: readonly BranchOption[];
	/** SDTF-02's planned duration for the current slide, minutes -- the only
	 * input the opt-in pacing nudge compares elapsed time against. */
	readonly currentSlidePlannedMinutes?: number | null;
	/** Teacher-only notes/AI suggestions for the current slide -- content
	 * sourced elsewhere; the cockpit only gates *visibility* to controller. */
	readonly teacherNotes?: readonly string[];
	/** The current slide's body text, supplied by the caller (deck data) --
	 * the only input the on-the-fly "Generate a new suggestion" branch
	 * fallback (TSP-06) rewrites. `null`/absent disables that action, same
	 * "no snapshot yet -> disabled trigger" rule SDE-08's
	 * `BlockRewriteControls` already uses. */
	readonly currentSlideBody?: string | null;
}

const CONNECTION_COPY: Readonly<Record<string, { label: string; tone: string }>> = {
	connecting: { label: "Connecting…", tone: "text-muted-foreground" },
	connected: { label: "Live", tone: "text-emerald-600 dark:text-emerald-400" },
	reconnecting: { label: "Reconnecting — presentation keeps running", tone: "text-amber-600 dark:text-amber-400" },
	offline: { label: "Offline — presentation keeps running", tone: "text-destructive" },
};

/**
 * Teacher live-session cockpit (TSP-04, ADR-046). A PANEL alongside the
 * standalone slide-deck presentation surface, never a replacement for it --
 * every connection-state branch below only ever changes this component's own
 * render, so a `GET /stream` outage degrades the cockpit, not the projected
 * slides (see `services/gateway/routers/teaching_session_live.py`'s stream
 * route for the degrade-to-polling behavior this reflects).
 *
 * Deliberately excludes: raw per-student response walls, student ranking,
 * and post-lesson analytics (a separate, deeper view per the base ACs) --
 * this is the during-class surface only.
 */
export function TeachingCockpit({
	sessionId,
	sessionToken,
	role,
	branchOptions = [],
	currentSlidePlannedMinutes = null,
	teacherNotes = [],
	currentSlideBody = null,
}: TeachingCockpitProps) {
	const { connection, state, onEvent } = useTeachingSessionLive(sessionId, sessionToken);
	const isController = isControllerRole(role);
	const connectionCopy = CONNECTION_COPY[connection];

	return (
		<div className="flex w-full flex-col gap-3" data-testid="teaching-cockpit">
			<ConnectionBanner label={connectionCopy.label} tone={connectionCopy.tone} />

			<Card>
				<CardHeader>
					<CardTitle className="text-base">Current activity</CardTitle>
				</CardHeader>
				<CardContent className="flex flex-col gap-2 text-sm">
					<p>
						Slide: <span className="font-medium">{state.current_slide_id ?? "Not started"}</span>
					</p>
					{state.open_interaction_id && (
						<p>
							Open interaction: <span className="font-medium">{state.open_interaction_id}</span>
						</p>
					)}
					<NextActionHint state={state} />
				</CardContent>
			</Card>

			{isController && (
				<PacingNudge
					currentSlideId={state.current_slide_id}
					plannedMinutes={currentSlidePlannedMinutes}
				/>
			)}

			<ClassSignal tallies={state.tallies} />

			{isController && (
				<BranchOptions
					sessionId={sessionId}
					sessionToken={sessionToken}
					currentSlideId={state.current_slide_id}
					manualOptions={branchOptions}
					currentSlideBody={currentSlideBody}
				/>
			)}

			{isController && teacherNotes.length > 0 && (
				<Card>
					<CardHeader>
						<CardTitle className="text-base">Teacher notes &amp; AI suggestions</CardTitle>
					</CardHeader>
					<CardContent className="flex flex-col gap-1 text-sm text-muted-foreground">
						{teacherNotes.map((note, index) => (
							// eslint-disable-next-line react/no-array-index-key -- static, caller-supplied list
							<p key={index}>{note}</p>
						))}
					</CardContent>
				</Card>
			)}

			<AnnotationOverlay currentSlideId={state.current_slide_id} ended={state.ended} onEvent={onEvent} />
		</div>
	);
}

function ConnectionBanner({ label, tone }: { readonly label: string; readonly tone: string }) {
	return (
		<div role="status" className={`text-xs font-medium ${tone}`} data-testid="cockpit-connection-state">
			{label}
		</div>
	);
}

/** Minimal-reading next action -- the one thing to read under classroom
 * pressure, not a dashboard's worth of state. */
function NextActionHint({ state }: { readonly state: { open_interaction_id: string | null; ended: boolean } }) {
	return (
		<p className="font-semibold" data-testid="cockpit-next-action">
			{state.ended ? nextActionHint(state) : `Next: ${nextActionHint(state)}`}
		</p>
	);
}

/** Class-level signal only (attempt/correct tallies per interaction) -- never
 * a per-student breakdown or ranking (base AC2). */
function ClassSignal({ tallies }: { readonly tallies: Readonly<Record<string, { attempt_count: number; correct_count: number }>> }) {
	const entries = Object.entries(tallies);
	return (
		<Card>
			<CardHeader>
				<CardTitle className="text-base">Class signal</CardTitle>
			</CardHeader>
			<CardContent className="text-sm">
				{entries.length === 0 ? (
					<p className="text-muted-foreground">No responses yet.</p>
				) : (
					<ul className="flex flex-col gap-1" data-testid="cockpit-class-signal">
						{entries.map(([interactionId, tally]) => (
							<li key={interactionId}>
								{interactionId}: {tally.correct_count}/{tally.attempt_count} correct
							</li>
						))}
					</ul>
				)}
			</CardContent>
		</Card>
	);
}

function PacingNudge({
	currentSlideId,
	plannedMinutes,
}: {
	readonly currentSlideId: string | null;
	readonly plannedMinutes: number | null;
}) {
	const { data: preference } = usePacingNudgePreference();
	const setPreference = useSetPacingNudgePreference();
	const [elapsedMs, setElapsedMs] = useState(0);
	const slideStartRef = useRef<number>(Date.now());

	useEffect(() => {
		slideStartRef.current = Date.now();
		setElapsedMs(0);
	}, [currentSlideId]);

	useEffect(() => {
		if (!preference?.enabled) return;
		const interval = setInterval(() => setElapsedMs(Date.now() - slideStartRef.current), 5_000);
		return () => clearInterval(interval);
	}, [preference?.enabled]);

	const behindPace = useMemo(() => isBehindPace(elapsedMs, plannedMinutes), [elapsedMs, plannedMinutes]);

	return (
		<Card>
			<CardHeader className="flex flex-row items-center justify-between space-y-0">
				<CardTitle className="text-base">Pacing</CardTitle>
				<label className="flex items-center gap-2 text-xs font-normal text-muted-foreground">
					<input
						type="checkbox"
						checked={preference?.enabled ?? false}
						onChange={(event) => setPreference.mutate(event.target.checked)}
						aria-label="Enable pacing nudge"
					/>
					Nudge me
				</label>
			</CardHeader>
			{preference?.enabled && (
				<CardContent className="text-sm" data-testid="cockpit-pacing-nudge">
					{behindPace ? (
						<p className="font-medium text-amber-600 dark:text-amber-400">
							Behind pace for this slide — consider moving on.
						</p>
					) : (
						<p className="text-muted-foreground">On pace.</p>
					)}
				</CardContent>
			)}
		</Card>
	);
}

interface PrecomputedBranchOption {
	readonly branch_id: string;
	readonly slide_id: string;
	readonly branch_type: BranchContentType;
	readonly label: string;
}

interface BranchSuggestionCandidate {
	readonly before: string;
	readonly after: string;
}

/**
 * TSP-06: precomputed branches are the zero-latency DEFAULT this component
 * fetches and lists first, with no LLM call on that path (amendment #2). The
 * on-the-fly "Generate a new suggestion" trigger is a secondary, explicitly
 * opt-in fallback below it -- selecting it never happens automatically, and
 * generating a candidate never makes anything visible to a
 * student/display role by itself (see `AiBlockRewriteConfirmModal`'s
 * "Apply"-only wiring below: only that click calls
 * `/branch-suggestions/apply`, which is the one path that can ever produce a
 * `branch_selected` event).
 */
function BranchOptions({
	sessionId,
	sessionToken,
	currentSlideId,
	manualOptions,
	currentSlideBody,
}: {
	readonly sessionId: string;
	readonly sessionToken: string;
	readonly currentSlideId: string | null;
	/** Caller-supplied branch options (validated content) layered on top of
	 * the cockpit's own precomputed-branch fetch -- kept for callers that
	 * already resolved options themselves; deduplicated by `branch_id`. */
	readonly manualOptions: readonly BranchOption[];
	readonly currentSlideBody: string | null;
}) {
	const [precomputed, setPrecomputed] = useState<readonly PrecomputedBranchOption[]>([]);
	const [pendingBranchId, setPendingBranchId] = useState<string | null>(null);
	const [aiFlowOpen, setAiFlowOpen] = useState(false);
	const [preset, setPreset] = useState<BranchContentType>("hint");
	const [freeform, setFreeform] = useState("");
	const [label, setLabel] = useState("");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [candidate, setCandidate] = useState<BranchSuggestionCandidate | null>(null);

	useEffect(() => {
		setPrecomputed([]);
		setCandidate(null);
		setAiFlowOpen(false);
		if (!currentSlideId) return;
		let cancelled = false;
		void (async () => {
			try {
				const response = await fetch(
					`${gatewayUrl()}/teaching-sessions/${sessionId}/branches?slide_id=${encodeURIComponent(currentSlideId)}`,
					{ headers: { Authorization: `Bearer ${sessionToken}` } },
				);
				if (!response.ok || cancelled) return;
				const data = (await response.json()) as { branches: PrecomputedBranchOption[] };
				if (!cancelled) setPrecomputed(data.branches);
			} catch {
				// ponytail: a failed fetch just leaves the precomputed list empty --
				// the AI fallback below still works, and the cockpit degrades to
				// its existing polling/offline behavior for everything else.
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [sessionId, sessionToken, currentSlideId]);

	const options: readonly BranchOption[] = useMemo(() => {
		const fromPrecomputed = precomputed.map((branch) => ({
			slide_id: branch.slide_id,
			branch_id: branch.branch_id,
			label: branch.label,
		}));
		const seen = new Set(fromPrecomputed.map((option) => option.branch_id));
		const extra = manualOptions.filter((option) => !seen.has(option.branch_id));
		return [...fromPrecomputed, ...extra];
	}, [precomputed, manualOptions]);

	const selectBranch = async (option: BranchOption) => {
		setPendingBranchId(option.branch_id);
		try {
			await fetch(`${gatewayUrl()}/teaching-sessions/${sessionId}/branch`, {
				method: "POST",
				headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
				body: JSON.stringify({ slide_id: option.slide_id, branch_id: option.branch_id }),
			});
		} finally {
			setPendingBranchId(null);
		}
	};

	const requestSuggestion = async () => {
		if (!currentSlideId || !currentSlideBody) return;
		setLoading(true);
		setError(null);
		try {
			const payload = resolveRewriteSuggestionPayload(preset, freeform);
			const response = await fetch(`${gatewayUrl()}/teaching-sessions/${sessionId}/branch-suggestions`, {
				method: "POST",
				headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
				body: JSON.stringify({ slide_id: currentSlideId, current_body: currentSlideBody, ...payload }),
			});
			if (!response.ok) throw new Error("Could not generate a branch suggestion.");
			const result = (await response.json()) as BranchSuggestionCandidate;
			setCandidate(result);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Could not generate a branch suggestion.");
		} finally {
			setLoading(false);
		}
	};

	const applySuggestion = async () => {
		if (!currentSlideId || !candidate) return;
		await fetch(`${gatewayUrl()}/teaching-sessions/${sessionId}/branch-suggestions/apply`, {
			method: "POST",
			headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
			body: JSON.stringify({
				slide_id: currentSlideId,
				branch_type: preset,
				label: label.trim() || preset,
				approved_body: candidate.after,
			}),
		});
		setCandidate(null);
		setAiFlowOpen(false);
		setFreeform("");
		setLabel("");
	};

	return (
		<Card>
			<CardHeader>
				<CardTitle className="text-base">Branch options</CardTitle>
			</CardHeader>
			<CardContent className="flex flex-col gap-3">
				<div className="flex flex-wrap gap-2" data-testid="cockpit-precomputed-branches">
					{options.length === 0 ? (
						<p className="text-sm text-muted-foreground">No precomputed branches for this slide.</p>
					) : (
						options.map((option) => (
							<Button
								key={option.branch_id}
								size="sm"
								variant="outline"
								disabled={pendingBranchId !== null}
								onClick={() => void selectBranch(option)}
							>
								{option.label}
							</Button>
						))
					)}
				</div>

				{!aiFlowOpen ? (
					<Button
						type="button"
						variant="ghost"
						size="sm"
						disabled={!currentSlideId || !currentSlideBody}
						onClick={() => setAiFlowOpen(true)}
					>
						Generate a new suggestion
					</Button>
				) : (
					<div className="flex flex-col gap-2 rounded-md border border-dashed border-border p-2">
						<div className="flex flex-wrap items-center gap-2">
							<select
								aria-label="Branch type"
								className="rounded-md border border-border bg-background px-2 py-1 text-sm"
								value={preset}
								onChange={(event) => setPreset(event.target.value as BranchContentType)}
							>
								{BRANCH_CONTENT_TYPES.map((type) => (
									<option key={type} value={type}>
										{type}
									</option>
								))}
							</select>
							<input
								type="text"
								aria-label="Freeform rewrite instruction (optional)"
								placeholder="Or describe how to adapt this (optional)"
								className="min-w-48 flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
								value={freeform}
								onChange={(event) => setFreeform(event.target.value)}
							/>
							<Button type="button" size="sm" disabled={loading} onClick={() => void requestSuggestion()}>
								{loading ? "Suggesting…" : "Suggest branch"}
							</Button>
							<Button type="button" variant="ghost" size="sm" onClick={() => setAiFlowOpen(false)}>
								Close
							</Button>
						</div>
						{error ? <p className="text-xs text-destructive">{error}</p> : null}
						{candidate ? (
							<>
								<input
									type="text"
									aria-label="Branch label"
									placeholder="Label shown on the branch button"
									className="rounded-md border border-border bg-background px-2 py-1 text-sm"
									value={label}
									onChange={(event) => setLabel(event.target.value)}
								/>
								<AiBlockRewriteConfirmModal
									blockLabel={`${preset} branch`}
									before={candidate.before}
									after={candidate.after}
									onApply={() => void applySuggestion()}
									onCancel={() => setCandidate(null)}
								/>
							</>
						) : null}
					</div>
				)}
			</CardContent>
		</Card>
	);
}

/** Ephemeral-only annotation overlay (TSP-04 amendment #1): pure client-side
 * drawing state, cleared on `slide_changed`/`session_ended` -- there is
 * deliberately no save/persist call anywhere in this component. */
function AnnotationOverlay({
	currentSlideId,
	ended,
	onEvent,
}: {
	readonly currentSlideId: string | null;
	readonly ended: boolean;
	readonly onEvent: (callback: (event: TeachingSessionLiveEvent) => void) => () => void;
}) {
	const canvasRef = useRef<HTMLCanvasElement>(null);
	const drawingRef = useRef(false);

	const clear = () => {
		const canvas = canvasRef.current;
		const ctx = canvas?.getContext("2d");
		if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
	};

	// Slide change is already visible via `currentSlideId` changing, but a
	// belt-and-suspenders listener on the raw stream events covers
	// `session_ended` too (which doesn't change `currentSlideId`).
	useEffect(() => onEvent((event) => {
		if (shouldClearAnnotation(event.name)) clear();
	}), [onEvent]);

	useEffect(() => {
		clear();
	}, [currentSlideId]);

	useEffect(() => {
		if (ended) clear();
	}, [ended]);

	const draw = (event: React.PointerEvent<HTMLCanvasElement>) => {
		const canvas = canvasRef.current;
		const ctx = canvas?.getContext("2d");
		if (!canvas || !ctx || !drawingRef.current) return;
		const rect = canvas.getBoundingClientRect();
		ctx.lineTo(event.clientX - rect.left, event.clientY - rect.top);
		ctx.stroke();
	};

	return (
		<canvas
			ref={canvasRef}
			data-testid="cockpit-annotation-overlay"
			className="h-40 w-full cursor-crosshair rounded-md border border-dashed border-border"
			width={640}
			height={160}
			onPointerDown={(event) => {
				drawingRef.current = true;
				const canvas = canvasRef.current;
				const ctx = canvas?.getContext("2d");
				const rect = canvas?.getBoundingClientRect();
				if (ctx && rect) ctx.moveTo(event.clientX - rect.left, event.clientY - rect.top);
			}}
			onPointerMove={draw}
			onPointerUp={() => {
				drawingRef.current = false;
			}}
			onPointerLeave={() => {
				drawingRef.current = false;
			}}
		/>
	);
}
