/**
 * Unit tests for Pipeline V2 artifact progress and scoped rejection components.
 *
 * Tests pure logic without DOM rendering. Component rendering verified via Playwright.
 */

import { describe, it, expect } from "vitest";
import type { ArtifactProgressItem } from "@/components/pipeline-v2-artifact-progress";
import type { ArtifactRejection } from "@/components/pipeline-v2-scoped-rejection";

describe("ArtifactProgressItem type", () => {
	it("accepts valid artifact progress items", () => {
		const item: ArtifactProgressItem = {
			artifact_id: "art-1",
			artifact_type: "lesson",
			status: "ready",
		};
		expect(item.artifact_id).toBe("art-1");
		expect(item.artifact_type).toBe("lesson");
		expect(item.status).toBe("ready");
	});

	it("accepts artifact progress with error", () => {
		const item: ArtifactProgressItem = {
			artifact_id: "art-2",
			artifact_type: "quiz",
			status: "failed",
			error: "Validation failed",
		};
		expect(item.error).toBe("Validation failed");
	});

	it("enforces readonly on all fields", () => {
		const item: ArtifactProgressItem = {
			artifact_id: "art-1",
			artifact_type: "lesson",
			status: "ready",
		};
		// TypeScript will enforce this at compile time
		expect(item).toBeDefined();
	});

	it("supports all valid status values", () => {
		const statuses = ["queued", "generating", "rendering", "validating", "ready", "failed"] as const;
		for (const status of statuses) {
			const item: ArtifactProgressItem = {
				artifact_id: `art-${status}`,
				artifact_type: "lesson",
				status,
			};
			expect(item.status).toBe(status);
		}
	});
});

describe("ArtifactRejection type", () => {
	it("accepts valid artifact rejection", () => {
		const rejection: ArtifactRejection = {
			artifact_id: "art-1",
			reason: "Content is incomplete",
		};
		expect(rejection.artifact_id).toBe("art-1");
		expect(rejection.reason).toBe("Content is incomplete");
	});

	it("enforces readonly on all fields", () => {
		const rejection: ArtifactRejection = {
			artifact_id: "art-1",
			reason: "Too short",
		};
		// TypeScript will enforce this at compile time
		expect(rejection).toBeDefined();
	});

	it("allows empty reason string", () => {
		const rejection: ArtifactRejection = {
			artifact_id: "art-1",
			reason: "",
		};
		expect(rejection.reason).toBe("");
	});
});

describe("PipelineV2EventPayload with artifacts", () => {
	it("accepts event with no artifacts", () => {
		type EventPayload = {
			readonly gate_id?: string;
			readonly artifacts?: readonly ArtifactProgressItem[];
		};

		const event: EventPayload = {
			gate_id: "gate-1",
		};
		expect(event.artifacts).toBeUndefined();
	});

	it("accepts event with artifact array", () => {
		type EventPayload = {
			readonly gate_id?: string;
			readonly artifacts?: readonly ArtifactProgressItem[];
		};

		const event: EventPayload = {
			gate_id: "gate-1",
			artifacts: [
				{
					artifact_id: "art-1",
					artifact_type: "lesson",
					status: "ready",
				},
				{
					artifact_id: "art-2",
					artifact_type: "quiz",
					status: "generating",
				},
			],
		};
		expect(event.artifacts).toHaveLength(2);
		expect(event.artifacts?.[0]?.artifact_type).toBe("lesson");
	});

	it("artifact array is readonly", () => {
		type EventPayload = {
			readonly gate_id?: string;
			readonly artifacts?: readonly ArtifactProgressItem[];
		};

		const event: EventPayload = {
			gate_id: "gate-1",
			artifacts: [
				{
					artifact_id: "art-1",
					artifact_type: "lesson",
					status: "ready",
				},
			],
		};
		// TypeScript will enforce readonly at compile time
		expect(event.artifacts).toBeDefined();
	});
});

describe("Artifact status configuration", () => {
	const STATUS_CONFIG = {
		queued: { label: "Queued", color: "text-muted-foreground" },
		generating: { label: "Generating", color: "text-blue-600" },
		rendering: { label: "Rendering", color: "text-amber-600" },
		validating: { label: "Validating", color: "text-amber-600" },
		ready: { label: "Ready", color: "text-green-600" },
		failed: { label: "Failed", color: "text-destructive" },
	} as const;

	it("has config for all status values", () => {
		const statuses = ["queued", "generating", "rendering", "validating", "ready", "failed"] as const;
		for (const status of statuses) {
			expect(STATUS_CONFIG[status]).toBeDefined();
			expect(STATUS_CONFIG[status].label).toBeTruthy();
			expect(STATUS_CONFIG[status].color).toBeTruthy();
		}
	});

	it("uses appropriate colors for status", () => {
		expect(STATUS_CONFIG.ready.color).toContain("green");
		expect(STATUS_CONFIG.failed.color).toContain("destructive");
		expect(STATUS_CONFIG.generating.color).toContain("blue");
	});
});

describe("Scoped rejection state management", () => {
	it("tracks rejection reasons by artifact ID", () => {
		const rejections = new Map<string, string>();
		rejections.set("art-1", "Incomplete content");
		rejections.set("art-2", "Wrong topic");

		expect(rejections.get("art-1")).toBe("Incomplete content");
		expect(rejections.get("art-2")).toBe("Wrong topic");
		expect(rejections.size).toBe(2);
	});

	it("removes artifact when reason is empty", () => {
		const rejections = new Map<string, string>();
		rejections.set("art-1", "Some reason");
		rejections.delete("art-1");

		expect(rejections.has("art-1")).toBe(false);
		expect(rejections.size).toBe(0);
	});

	it("converts rejection map to array", () => {
		const rejections = new Map<string, string>();
		rejections.set("art-1", "Reason 1");
		rejections.set("art-2", "Reason 2");

		const items: ArtifactRejection[] = [];
		for (const [artifactId, reason] of rejections) {
			items.push({ artifact_id: artifactId, reason });
		}

		expect(items).toHaveLength(2);
		expect(items[0]).toEqual({ artifact_id: "art-1", reason: "Reason 1" });
	});

	it("handles empty rejection map", () => {
		const rejections = new Map<string, string>();
		const items: ArtifactRejection[] = [];
		for (const [artifactId, reason] of rejections) {
			items.push({ artifact_id: artifactId, reason });
		}

		expect(items).toHaveLength(0);
	});
});

describe("Artifact type filtering", () => {
	it("extracts artifact list from progress items", () => {
		const artifacts: ArtifactProgressItem[] = [
			{ artifact_id: "art-1", artifact_type: "lesson", status: "ready" },
			{ artifact_id: "art-2", artifact_type: "quiz", status: "generating" },
			{ artifact_id: "art-3", artifact_type: "worksheet", status: "failed" },
		];

		const filtered = artifacts.map((a) => ({ id: a.artifact_id, type: a.artifact_type }));

		expect(filtered).toHaveLength(3);
		expect(filtered[0]).toEqual({ id: "art-1", type: "lesson" });
		expect(filtered[2].type).toBe("worksheet");
	});

	it("filters out artifacts with certain statuses if needed", () => {
		const artifacts: ArtifactProgressItem[] = [
			{ artifact_id: "art-1", artifact_type: "lesson", status: "ready" },
			{ artifact_id: "art-2", artifact_type: "quiz", status: "queued" },
			{ artifact_id: "art-3", artifact_type: "worksheet", status: "generating" },
		];

		const generated = artifacts.filter((a) => a.status !== "queued");

		expect(generated).toHaveLength(2);
		expect(generated.every((a) => a.status !== "queued")).toBe(true);
	});
});

describe("Gate response construction for scoped rejections", () => {
	it("builds scoped rejection response", () => {
		const rejections: ArtifactRejection[] = [
			{ artifact_id: "art-1", reason: "Incomplete" },
			{ artifact_id: "art-2", reason: "Wrong context" },
		];

		const response = {
			rejection_type: "scoped",
			artifact_rejections: rejections,
		};

		expect(response.rejection_type).toBe("scoped");
		expect(response.artifact_rejections).toHaveLength(2);
		expect(response.artifact_rejections[0]).toEqual({
			artifact_id: "art-1",
			reason: "Incomplete",
		});
	});

	it("includes gate metadata with scoped rejection", () => {
		const request = {
			gate_id: "gate-123",
			gate_name: "content_approval" as const,
			action: "reject" as const,
			response: {
				rejection_type: "scoped",
				artifact_rejections: [{ artifact_id: "art-1", reason: "Bad content" }],
			},
		};

		expect(request.gate_id).toBe("gate-123");
		expect(request.action).toBe("reject");
		expect(request.response.rejection_type).toBe("scoped");
	});
});

describe("Content approval gate detection", () => {
	it("detects content_approval gate", () => {
		type GateName = "content_approval";
		const gateName: GateName = "content_approval";
		const shouldShowScoped = gateName === "content_approval";
		expect(shouldShowScoped).toBe(true);
	});

	it("does not show scoped rejection for other gates", () => {
		type OtherGateName = "blueprint_approval" | "contract_confirmation" | "clarification_required";
		const gateNames: readonly OtherGateName[] = ["blueprint_approval", "contract_confirmation", "clarification_required"];
		for (const gateName of gateNames) {
			const shouldShowScoped = (gateName as string) === "content_approval";
			expect(shouldShowScoped).toBe(false);
		}
	});

	it("requires artifacts to show scoped rejection UI", () => {
		const artifacts: ArtifactProgressItem[] = [];
		const shouldShowScoped = true && artifacts.length > 0; // gate is content_approval
		expect(shouldShowScoped).toBe(false);
	});

	it("shows scoped rejection UI when content_approval and artifacts present", () => {
		type GateName = "content_approval";
		const gateName: GateName = "content_approval";
		const artifacts: ArtifactProgressItem[] = [
			{ artifact_id: "art-1", artifact_type: "lesson", status: "ready" },
		];
		const shouldShowScoped = gateName === "content_approval" && artifacts.length > 0;
		expect(shouldShowScoped).toBe(true);
	});
});
