import { SlideDeckBlockSchema } from "@oh-my-class/schemas";
import { describe, expect, it } from "vitest";
import { BLOCK_BODY_MAX } from "../block-constraints";
import { applyHeadingEdit } from "./heading-block";

// Parsed through the real schema (not a hand-typed literal) so the fixture
// always satisfies the current contract, including any new optional fields
// with schema defaults added later.
const block = SlideDeckBlockSchema.parse({ block_id: "block-title", block_type: "heading", body: "Original heading" });

describe("applyHeadingEdit", () => {
	it("accepts a valid heading edit", () => {
		expect(applyHeadingEdit(block, "New heading").body).toBe("New heading");
	});

	it("rejects an empty heading and keeps the original body", () => {
		expect(applyHeadingEdit(block, "   ").body).toBe("Original heading");
	});

	it("clamps a heading longer than the registry max instead of erroring", () => {
		const draft = "x".repeat(BLOCK_BODY_MAX + 100);
		const result = applyHeadingEdit(block, draft);
		expect(result.body).toHaveLength(BLOCK_BODY_MAX);
	});

	it("stores markup as literal text — there is no HTML acceptance path", () => {
		const html = "<b>bold</b>";
		expect(applyHeadingEdit(block, html).body).toBe(html);
	});

	it("does not mutate other block fields", () => {
		const result = applyHeadingEdit(block, "Updated");
		expect(result.block_id).toBe(block.block_id);
		expect(result.block_type).toBe("heading");
	});
});
