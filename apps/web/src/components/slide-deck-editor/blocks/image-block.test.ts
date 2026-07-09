import { SlideDeckBlockSchema, type SlideDeckMedia } from "@oh-my-class/schemas";
import { describe, expect, it } from "vitest";
import { BLOCK_BODY_MAX, MEDIA_ALT_TEXT_MAX } from "../block-constraints";
import { applyImageAltTextEdit, applyImageCaptionEdit, applyMediaSelection } from "./image-block";

// Parsed through the real schema so the fixture stays valid as the contract
// grows new optional/defaulted fields.
const block = SlideDeckBlockSchema.parse({
	block_id: "block-visual",
	block_type: "image",
	body: "Original caption",
	media: {
		media_id: "media-model",
		media_type: "image",
		source: "packaged/example.svg",
		tier: "packaged",
		alt_text: "Original alt text",
	},
});

const blockWithoutMedia = SlideDeckBlockSchema.parse({ block_id: "block-visual", block_type: "image", body: "Caption" });

describe("applyImageCaptionEdit", () => {
	it("accepts a valid caption edit", () => {
		expect(applyImageCaptionEdit(block, "New caption").body).toBe("New caption");
	});

	it("rejects an empty caption and keeps the original body", () => {
		expect(applyImageCaptionEdit(block, "").body).toBe("Original caption");
	});

	it("clamps a caption longer than the registry max", () => {
		const draft = "c".repeat(BLOCK_BODY_MAX + 10);
		expect(applyImageCaptionEdit(block, draft).body).toHaveLength(BLOCK_BODY_MAX);
	});
});

describe("applyImageAltTextEdit", () => {
	it("accepts a valid alt text edit", () => {
		const result = applyImageAltTextEdit(block, "New alt text");
		expect(result.media?.alt_text).toBe("New alt text");
	});

	it("rejects clearing alt text — the registry requires it for image blocks", () => {
		const result = applyImageAltTextEdit(block, "   ");
		expect(result.media?.alt_text).toBe("Original alt text");
	});

	it("clamps alt text longer than the registry max", () => {
		const draft = "a".repeat(MEDIA_ALT_TEXT_MAX + 20);
		const result = applyImageAltTextEdit(block, draft);
		expect(result.media?.alt_text).toHaveLength(MEDIA_ALT_TEXT_MAX);
	});

	it("is a no-op when the block has no media attached", () => {
		expect(applyImageAltTextEdit(blockWithoutMedia, "Some alt text")).toBe(blockWithoutMedia);
	});
});

describe("applyMediaSelection", () => {
	it("attaches a library-selected media reference to the block", () => {
		const selected: SlideDeckMedia = {
			media_id: "media-from-library",
			media_type: "image",
			source: "http://localhost:8101/media-assets/media-from-library/file",
			tier: "online_optional",
			alt_text: "frog-lifecycle.png",
			fallback_text: "frog-lifecycle.png",
			requires_network: true,
		};

		const result = applyMediaSelection(blockWithoutMedia, selected);

		expect(result.media).toEqual(selected);
		expect(result.body).toBe(blockWithoutMedia.body); // only `media` changes
	});
});
