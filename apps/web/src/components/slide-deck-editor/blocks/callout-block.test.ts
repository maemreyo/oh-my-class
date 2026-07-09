import { SlideDeckBlockSchema } from "@oh-my-class/schemas";
import { describe, expect, it } from "vitest";
import { BLOCK_BODY_MAX } from "../block-constraints";
import { applyCalloutEdit } from "./callout-block";

const block = SlideDeckBlockSchema.parse({ block_id: "block-goal", block_type: "callout", body: "Original callout" });

describe("applyCalloutEdit", () => {
	it("accepts a valid callout edit", () => {
		expect(applyCalloutEdit(block, "New callout body").body).toBe("New callout body");
	});

	it("rejects an empty callout and keeps the original body", () => {
		expect(applyCalloutEdit(block, "  ").body).toBe("Original callout");
	});

	it("clamps a callout longer than the registry max", () => {
		const draft = "z".repeat(BLOCK_BODY_MAX + 10);
		expect(applyCalloutEdit(block, draft).body).toHaveLength(BLOCK_BODY_MAX);
	});
});
