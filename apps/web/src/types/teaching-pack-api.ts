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
	| "content_approval";

export type TeachingPackGateAction = "answer" | "approve" | "edit" | "reject";

export interface TeachingPackCreateRunRequest {
	readonly raw_request: string;
	readonly class_info: Readonly<Record<string, unknown>>;
}

export interface TeachingPackRunAcceptedResponse {
	readonly run_id: string;
	readonly job_id: string | null;
	readonly status: TeachingPackRunStatus;
	readonly queued: boolean;
}

export interface TeachingPackRunStatusResponse {
	readonly run_id: string;
	readonly status: TeachingPackRunStatus;
	readonly raw_request: string;
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
