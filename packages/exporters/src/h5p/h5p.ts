/**
 * H5P ZIP package generator.
 *
 * Bundle: `h5p.json` + `content/content.json` + library files.
 * Generate only `content/content.json` — pre-built libraries handle rendering.
 *
 * @param artifacts - Array of {@link ArtifactContent} objects to convert.
 * @returns A `Buffer` containing the H5P ZIP package.
 * @throws {UnsupportedFormatError} Always — H5P generation is not yet wired.
 */
import type { ArtifactContent } from "@oh-my-class/schemas";
import { UnsupportedFormatError } from "../qti/qti.js";

export async function generateH5P(
	_artifacts: ArtifactContent[],
): Promise<Buffer> {
	throw new UnsupportedFormatError(
		"h5p",
		"H5P generation is not yet wired. Use the H5P library directly.",
	);
}
