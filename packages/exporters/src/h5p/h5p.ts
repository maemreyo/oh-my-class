/**
 * H5P ZIP package generator.
 * Bundle: h5p.json + content/content.json + library files.
 * Generate only content/content.json — pre-built libraries handle rendering.
 */

import type { ArtifactContent } from "@oh-my-class/schemas";

export async function generateH5P(
	_artifacts: ArtifactContent[],
): Promise<Buffer> {
	// TODO: Implement H5P generation
	throw new Error("Not yet implemented");
}
