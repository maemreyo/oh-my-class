/**
 * QTI 2.1 XML generator (Year 2+).
 *
 * Most interoperable standard (1EdTech). Export-only.
 * Structure: `imsmanifest.xml` + `assessments/test.xml` + `items/*.xml`.
 *
 * @param artifacts - Array of {@link ArtifactContent} objects to convert.
 * @returns A `Buffer` containing the QTI ZIP package.
 * @throws {UnsupportedFormatError} Always — QTI generation is not yet wired.
 */
import type { ArtifactContent } from "@oh-my-class/schemas";

export class UnsupportedFormatError extends Error {
	readonly format: string;

	constructor(format: string, message?: string) {
		super(message ?? `Format "${format}" is not yet implemented`);
		this.name = "UnsupportedFormatError";
		this.format = format;
	}
}

export async function generateQTI(
	_artifacts: ArtifactContent[],
): Promise<Buffer> {
	throw new UnsupportedFormatError(
		"qti",
		"QTI export is not yet implemented. Use GIFT or H5P instead.",
	);
}
