/**
 * QTI 2.1 XML generator (Year 2+).
 * Most interoperable standard (1EdTech). Export-only.
 * Structure: imsmanifest.xml + assessments/test.xml + items/*.xml.
 */

import type { ArtifactContent } from "@oh-my-class/schemas";

export async function generateQTI(
	_artifacts: ArtifactContent[],
): Promise<Buffer> {
	// TODO: Implement QTI 2.1 generation (Year 2+)
	throw new Error("Not yet implemented");
}
