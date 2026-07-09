import { SlideDeckMediaSchema } from "@oh-my-class/schemas";
import { describe, expect, it } from "vitest";
import { buildMediaFromAsset, mediaAssetFileUrl, type MediaAsset } from "./media-library-picker";

function asset(overrides: Partial<MediaAsset> = {}): MediaAsset {
	return {
		asset_id: "media-abc",
		filename: "frog-lifecycle.png",
		content_type: "image/png",
		tags: ["biology"],
		alt_text: null,
		storage_key: "teacher-media/teacher-1/media-abc.png",
		created_at: "2026-07-09T00:00:00Z",
		...overrides,
	};
}

describe("buildMediaFromAsset", () => {
	it("produces a SlideDeckMedia that passes the real contract schema", () => {
		const media = buildMediaFromAsset(asset());
		expect(() => SlideDeckMediaSchema.parse(media)).not.toThrow();
	});

	it("points source at the gateway's file-serving endpoint for that asset", () => {
		const media = buildMediaFromAsset(asset());
		expect(media.source).toBe(mediaAssetFileUrl("media-abc"));
	});

	it("falls back alt_text to the filename when the library entry has none yet (SDX-04 hook)", () => {
		const media = buildMediaFromAsset(asset({ alt_text: null }));
		expect(media.alt_text).toBe("frog-lifecycle.png");
	});

	it("uses the library alt_text once SDX-04 (or a teacher) fills it in", () => {
		const media = buildMediaFromAsset(asset({ alt_text: "A frog's four-stage lifecycle" }));
		expect(media.alt_text).toBe("A frog's four-stage lifecycle");
	});

	it("always sets online_optional tier with requires_network and fallback_text", () => {
		const media = buildMediaFromAsset(asset());
		expect(media.tier).toBe("online_optional");
		expect(media.requires_network).toBe(true);
		expect(media.fallback_text).toBe("frog-lifecycle.png");
	});
});
