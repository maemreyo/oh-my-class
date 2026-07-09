import { describe, it, expect } from "vitest";
import { generateQTI, UnsupportedFormatError } from "../src/qti/qti.js";
import type { ArtifactContent } from "@oh-my-class/schemas";

const stubArtifact: ArtifactContent = {
  artifact_type: "lesson",
  theme: "default",
  title: "Stub Lesson",
  sections: [{ id: "s1", title: "Intro", content: "Hello" }],
  metadata: {},
  accessibility: { language: "en", reading_level: "grade-5", alt_texts: {} },
};

describe("generateQTI", () => {
  it("throws UnsupportedFormatError", async () => {
    await expect(generateQTI([stubArtifact])).rejects.toThrow(
      UnsupportedFormatError,
    );
  });

  it("includes remediation guidance in message", async () => {
    await expect(generateQTI([stubArtifact])).rejects.toThrow(
      /GIFT or H5P/,
    );
  });

  it("sets .format to 'qti'", async () => {
    try {
      await generateQTI([stubArtifact]);
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(UnsupportedFormatError);
      expect((err as UnsupportedFormatError).format).toBe("qti");
    }
  });
});

describe("UnsupportedFormatError", () => {
  it("defaults message when none provided", () => {
    const err = new UnsupportedFormatError("gift");
    expect(err.message).toBe('Format "gift" is not yet implemented');
    expect(err.name).toBe("UnsupportedFormatError");
    expect(err.format).toBe("gift");
  });

  it("accepts custom message", () => {
    const err = new UnsupportedFormatError("csv", "No CSV support");
    expect(err.message).toBe("No CSV support");
  });
});
