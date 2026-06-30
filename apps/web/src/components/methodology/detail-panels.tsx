import { TimedQuizControls, type TimedQuizSettings } from "./timed-quiz-controls";

export interface MethodologyInspectorDetails {
	readonly contrastivePair?: {
		readonly title: string;
		readonly leftLabel: string;
		readonly rightLabel: string;
		readonly reason: string;
	};
	readonly filmActivity?: {
		readonly title: string;
		readonly context: string;
		readonly before: string;
		readonly during: string;
		readonly after: string;
	};
	readonly shyStudent?: {
		readonly intent: string;
		readonly requiredComponent: string;
		readonly coachingNotesSeparated: boolean;
	};
	readonly activeRecall?: {
		readonly intent: string;
		readonly requiredComponent: string;
		readonly revealSeparated: boolean;
	};
	readonly whyWrongReasoning?: {
		readonly questions: readonly WrongReasonQuestion[];
	};
	readonly timedQuiz?: {
		readonly settings: TimedQuizSettings;
		readonly timedItemCount: number;
		readonly totalItemCount: number;
	};
}

interface WrongReasonQuestion {
	readonly id: string;
	readonly prompt: string;
	readonly options: Readonly<Record<string, string>>;
	readonly answer: string;
	readonly wrongReasons: Readonly<Record<string, string>>;
}

export function MethodologyDetailPanels({
	declaredTags,
	details,
}: {
	readonly declaredTags: readonly string[];
	readonly details?: MethodologyInspectorDetails;
}) {
	return (
		<>
			{declaredTags.includes("concept_map") ? (
				<p className="mt-3 text-sm text-muted-foreground">
					Concept Map requires a vocabulary cluster or contrastive-pair structure: use <code>vocab_cluster</code> or <code>contrastive_pairs</code> so students can see grouping, relationships, and navigation.
				</p>
			) : null}
			{declaredTags.includes("contrastive_pairs") && details?.contrastivePair ? (
				<section className="mt-3 rounded-md border border-border bg-background p-3" aria-label="Contrastive Pairs details">
					<h4 className="font-medium">{details.contrastivePair.title}</h4>
					<div className="mt-2 grid gap-2 md:grid-cols-2">
						<div className="rounded-md border border-border p-2 text-sm">{details.contrastivePair.leftLabel}</div>
						<div className="rounded-md border border-border p-2 text-sm">{details.contrastivePair.rightLabel}</div>
					</div>
					<p className="mt-2 text-sm text-muted-foreground">{details.contrastivePair.reason}</p>
				</section>
			) : null}
			{declaredTags.includes("film_based") && details?.filmActivity ? (
				<section className="mt-3 rounded-md border border-border bg-background p-3" aria-label="Film Based details">
					<h4 className="font-medium">{details.filmActivity.title}</h4>
					<p className="mt-1 text-sm text-muted-foreground">{details.filmActivity.context}</p>
					<div className="mt-3 grid gap-2 md:grid-cols-3">
						<PhaseDetail title="Before watching" body={details.filmActivity.before} />
						<PhaseDetail title="While watching" body={details.filmActivity.during} />
						<PhaseDetail title="After watching" body={details.filmActivity.after} />
					</div>
				</section>
			) : null}
			{declaredTags.includes("shy_student_1on1") && details?.shyStudent ? (
				<section className="mt-3 rounded-md border border-border bg-background p-3" aria-label="Shy Student 1:1 details">
					<h4 className="font-medium">1:1 low-pressure roleplay</h4>
					<p className="mt-1 text-sm text-muted-foreground">{details.shyStudent.intent}</p>
					<div className="mt-3 grid gap-2 md:grid-cols-2">
						<div className="rounded-md border border-border p-2 text-sm">Required component: {details.shyStudent.requiredComponent}</div>
						<div className="rounded-md border border-border p-2 text-sm">{details.shyStudent.coachingNotesSeparated ? "Teacher-only coaching notes separated" : "Coaching note separation needed"}</div>
					</div>
				</section>
			) : null}
			{declaredTags.includes("active_recall") && details?.activeRecall ? (
				<section className="mt-3 rounded-md border border-border bg-background p-3" aria-label="Active Recall details">
					<h4 className="font-medium">Retrieval practice before support</h4>
					<p className="mt-1 text-sm text-muted-foreground">{details.activeRecall.intent}</p>
					<div className="mt-3 grid gap-2 md:grid-cols-2">
						<div className="rounded-md border border-border p-2 text-sm">Required component: {details.activeRecall.requiredComponent}</div>
						<div className="rounded-md border border-border p-2 text-sm">{details.activeRecall.revealSeparated ? "Reveal and rationale separated" : "Reveal separation needed"}</div>
					</div>
				</section>
			) : null}
			{declaredTags.includes("why_wrong_reasoning") && details?.whyWrongReasoning ? (
				<section className="mt-3 rounded-md border border-border bg-background p-3" aria-label="Why Wrong Reasoning details">
					<h4 className="font-medium">Distractor reasoning coverage</h4>
					<div className="mt-3 space-y-3">
						{details.whyWrongReasoning.questions.map((question) => (
							<WrongReasonQuestionPanel key={question.id} question={question} />
						))}
					</div>
				</section>
			) : null}
			{declaredTags.includes("timed_quiz") && details?.timedQuiz ? (
				<section className="mt-3 rounded-md border border-border bg-background p-3" aria-label="Timed Quiz details">
					<h4 className="font-medium">Timing metadata coverage</h4>
					<p className="mt-1 text-sm text-muted-foreground">{details.timedQuiz.timedItemCount} of {details.timedQuiz.totalItemCount} items include time badges.</p>
					<TimedQuizControls settings={details.timedQuiz.settings} />
				</section>
			) : null}
		</>
	);
}

function WrongReasonQuestionPanel({ question }: { readonly question: WrongReasonQuestion }) {
	const distractorKeys = Object.keys(question.options).filter((optionKey) => optionKey !== question.answer);
	return (
		<article className="rounded-md border border-border p-3" id={`question-card-${question.id}-wrong-reasons`}>
			<h5 className="text-sm font-medium">Question {question.id}</h5>
			<p className="mt-1 text-sm text-muted-foreground">{question.prompt}</p>
			<div className="mt-3 grid gap-2 md:grid-cols-2">
				{distractorKeys.map((optionKey) => {
					const reason = question.wrongReasons[optionKey]?.trim();
					return (
						<label key={optionKey} className="space-y-1 rounded-md border border-border p-2 text-sm">
							<span className="font-medium">Wrong reason for {optionKey}</span>
							<textarea className="min-h-16 w-full rounded-md border border-input bg-background px-3 py-2" readOnly value={reason ?? `Missing wrong reason for ${optionKey}`} />
						</label>
					);
				})}
			</div>
		</article>
	);
}

function PhaseDetail({ title, body }: { readonly title: string; readonly body: string }) {
	return (
		<div className="rounded-md border border-border p-2 text-sm">
			<p className="font-medium">{title}</p>
			<p className="mt-1 text-muted-foreground">{body}</p>
		</div>
	);
}
