import { SlideDeckBlockSchema } from "@oh-my-class/schemas";
import { describe, expect, it } from "vitest";
import { BLOCK_BODY_MAX } from "../block-constraints";
import { applyParagraphEdit } from "./paragraph-block";

const block = SlideDeckBlockSchema.parse({ block_id: "block-vocab-1", block_type: "paragraph", body: "Original paragraph" });

describe("applyParagraphEdit", () => {
	it("accepts a valid paragraph edit", () => {
		expect(applyParagraphEdit(block, "New paragraph body").body).toBe("New paragraph body");
	});

	it("rejects an empty paragraph and keeps the original body", () => {
		expect(applyParagraphEdit(block, "").body).toBe("Original paragraph");
	});

	it("clamps a paragraph longer than the registry max", () => {
		const draft = "y".repeat(BLOCK_BODY_MAX + 250);
		expect(applyParagraphEdit(block, draft).body).toHaveLength(BLOCK_BODY_MAX);
	});

	it("stores markup as literal text", () => {
		const html = "<script>alert(1)</script>";
		expect(applyParagraphEdit(block, html).body).toBe(html);
	});
});
