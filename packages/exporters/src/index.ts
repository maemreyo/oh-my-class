/**
 * Unified export API.
 * All formats generated from the same ArtifactContent JSON — format-agnostic internal model.
 */

import type { ArtifactContent } from "@oh-my-class/schemas";

export type ExportFormat = "gift" | "h5p" | "qti";

export async function exportByFormat(
	format: ExportFormat,
	artifacts: ArtifactContent[],
): Promise<Buffer> {
	switch (format) {
		case "gift": {
			const { generateGift } = await import("./gift/gift.js");
			return generateGift(artifacts);
		}
		case "h5p": {
			const { generateH5P } = await import("./h5p/h5p.js");
			return generateH5P(artifacts);
		}
		case "qti": {
			const { generateQTI } = await import("./qti/qti.js");
			return generateQTI(artifacts);
		}
		default: {
			const _exhaustive: never = format;
			throw new Error(`Unknown export format: ${_exhaustive}`);
		}
	}
}
