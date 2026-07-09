import { describe, it, expect } from "vitest";
import { exportByFormat, UnsupportedFormatError } from "../src/index.js";
import type { ExportFormat } from "../src/index.js";
import type { ArtifactContent } from "@oh-my-class/schemas";

const stubArtifact: ArtifactContent = {
  artifact_type: "lesson",
  theme: "default",
  title: "Stub Lesson",
  sections: [{ id: "s1", title: "Intro", content: "Hello" }],
  metadata: {},
  accessibility: { language: "en", reading_level: "grade-5", alt_texts: {} },
};

/** Formats that throw UnsupportedFormatError (no TS implementation yet). */
const unsupportedFormats: ExportFormat[] = [
  "html",
  "anki_apkg",
  "flashcard_tsv",
  "pptx",
];

/** Formats with stub generators that also throw UnsupportedFormatError. */
const stubFormats: ExportFormat[] = ["gift", "h5p", "qti"];

describe("exportByFormat", () => {
  describe.each(unsupportedFormats)("unsupported format %s", (fmt) => {
    it("throws UnsupportedFormatError", async () => {
      await expect(exportByFormat(fmt, [stubArtifact])).rejects.toThrow(
        UnsupportedFormatError,
      );
    });

    it("sets .format to the format name", async () => {
      try {
        await exportByFormat(fmt, [stubArtifact]);
        expect.fail("should have thrown");
      } catch (err) {
        expect(err).toBeInstanceOf(UnsupportedFormatError);
        expect((err as UnsupportedFormatError).format).toBe(fmt);
      }
    });
  });

  describe.each(stubFormats)("stub format %s", (fmt) => {
    it("throws UnsupportedFormatError (generator not yet wired)", async () => {
      await expect(exportByFormat(fmt, [stubArtifact])).rejects.toThrow(
        UnsupportedFormatError,
      );
    });
  });
});

describe("ExportFormat type", () => {
  it("covers all 7 canonical formats", () => {
    const allFormats: ExportFormat[] = [
      "html",
      "gift",
      "h5p",
      "qti",
      "anki_apkg",
      "flashcard_tsv",
      "pptx",
    ];
    // If the type only covered fewer formats, this would be a compile error.
    const _assert: ExportFormat[] = allFormats;
    expect(_assert).toHaveLength(7);
  });
});
