export type TeachingPackRunStatus =
	| "pending"
	| "planning"
	| "researching"
	| "generating"
	| "reviewing"
	| "awaiting_approval"
	| "exporting"
	| "completed"
	| "failed"
	| "cancelled";

export type TeachingPackGateName =
	| "clarification_required"
	| "contract_confirmation"
	| "search_plan_confirmation"
	| "blueprint_approval"
	| "content_approval"
	| "unit_approval";

export type TeachingPackGateAction = "answer" | "approve" | "approve_selected" | "edit" | "reject" | "reject_selected";

export interface TeachingPackCreateRunRequest {
	readonly raw_request: string;
	readonly class_info: Readonly<Record<string, unknown>>;
}

export type TeachingBriefArtifactType = "lesson" | "worksheet" | "quiz" | "drill" | "recap" | "infographic" | "flashcard_deck" | "answer_key" | "roadmap" | "slide_deck";
export type TeachingBriefExportFormat = "html" | "gift" | "h5p" | "qti" | "anki_apkg" | "flashcard_tsv" | "pptx";

export interface TeachingBrief {
	readonly raw_request: string;
	readonly topic: string;
	readonly grade: number;
	readonly subject: string;
	readonly target_language: string;
	readonly instruction_language: string;
	readonly curriculum: string | null;
	readonly class_context: string;
	readonly artifact_types: readonly TeachingBriefArtifactType[];
	readonly export_formats: readonly TeachingBriefExportFormat[];
	readonly methodology: string | null;
	readonly research_policy: "basic" | "standard" | "rigorous";
	readonly must_include: string;
	readonly avoid: string;
	readonly always_review: boolean;
}

export interface TeachingBriefResponse extends TeachingBrief {
	readonly brief_id: string;
	readonly planning_review_required: boolean;
	readonly materiality_reasons: readonly string[];
}

export interface TeachingBriefLaunchResponse extends TeachingBriefResponse {
	readonly run_id: string;
	readonly job_id: string | null;
	readonly status: TeachingPackRunStatus;
	readonly queued: boolean;
}

export interface TeachingPackRunAcceptedResponse {
	readonly run_id: string;
	readonly job_id: string | null;
	readonly status: TeachingPackRunStatus;
	readonly queued: boolean;
}

export type ArtifactStatusValue =
	| "passed"
	| "regenerating"
	| "failed"
	| "skipped_due_dependency"
	| "escalated";

export interface ArtifactStatusItem {
	readonly artifact_id: string;
	readonly artifact_type: string;
	readonly status: ArtifactStatusValue;
	readonly summary: string;
	readonly teacher_action: string;
}

export interface ArtifactExplanation {
	readonly artifact_id: string;
	readonly artifact_type: string;
	readonly judge_rationale: string;
	readonly revision_count: number;
	readonly healing_history: readonly Readonly<Record<string, unknown>>[];
	readonly approval_mode: "manual" | "auto_approved" | string;
}

export interface TeachingPackPendingGateResponse {
	readonly gate_id: string;
	readonly gate_name: TeachingPackGateName;
	readonly allowed_actions: readonly TeachingPackGateAction[];
	readonly snapshot_ids: readonly string[];
}

export interface TeachingPackRunStatusResponse {
	readonly run_id: string;
	readonly status: TeachingPackRunStatus;
	readonly raw_request: string;
	readonly artifact_statuses?: readonly ArtifactStatusItem[];
	readonly pending_gate?: TeachingPackPendingGateResponse | null;
}

export interface TeachingPackResumeRequest {
	readonly gate_id: string;
	readonly gate_name: TeachingPackGateName;
	readonly action: TeachingPackGateAction;
	readonly response?: Readonly<Record<string, unknown>>;
}

export interface TeachingPackResumeAcceptedResponse {
	readonly run_id: string;
	readonly response_id: string;
	readonly job_id: string | null;
}

export interface TeachingPackRevisionAcceptedResponse {
	readonly run_id: string;
	readonly artifact_id: string;
	readonly job_id: string;
}

export interface TeachingPackCancelResponse {
	readonly run_id: string;
	readonly status: TeachingPackRunStatus;
	readonly cancelled_jobs: number;
}

export interface TeachingPackDeleteResponse {
	readonly run_id: string;
	readonly deleted: boolean;
}

export interface TeachingPackRestoreResponse {
	readonly run_id: string;
	readonly restored: boolean;
}
