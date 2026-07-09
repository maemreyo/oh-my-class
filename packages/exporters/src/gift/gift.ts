/**
 * Moodle GIFT format generator.
 *
 * Line-oriented text format. Supports: MCQ, TF, short answer, matching,
 * numerical, essay.  See {@link GIFTExporter} in `gift-impl/` for the
 * low-level serialiser.
 *
 * @param artifacts - Array of {@link ArtifactContent} objects to convert.
 * @returns A `Buffer` containing GIFT-formatted text.
 * @throws {UnsupportedFormatError} Always — GIFT generation is not yet wired.
 */
import type { ArtifactContent } from "@oh-my-class/schemas";
import { UnsupportedFormatError } from "../qti/qti.js";

export async function generateGift(
	_artifacts: ArtifactContent[],
): Promise<Buffer> {
	throw new UnsupportedFormatError(
		"gift",
		"GIFT generation is not yet wired. Use gift-impl/GIFTExporter directly.",
	);
}
