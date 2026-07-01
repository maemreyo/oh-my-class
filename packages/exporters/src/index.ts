/**
 * Unified export API.
 * All formats generated from the same ArtifactContent JSON — format-agnostic internal model.
 */

import type { ArtifactContent } from "@oh-my-class/schemas";

export type ExportFormat = "gift" | "h5p" | "qti";
export {
  INVERSE_THINKING_FORMAT_SUPPORT,
  UnsupportedInverseThinkingExportError,
  buildInverseThinkingGoogleFormsRequests,
  exportInverseThinkingGift,
  exportInverseThinkingH5P,
  exportInverseThinkingQTI,
  supportForInverseThinking,
} from "./inverse-thinking.js";
export {
  buildVocabularyBatchPackage,
} from "./vocabulary-batch/index.js";
export type {
  VocabularyBatchClusterInput,
  VocabularyBatchExportFormat,
  VocabularyBatchManifest,
  VocabularyBatchManifestCluster,
  VocabularyBatchManifestFile,
  VocabularyBatchPackage,
  VocabularyBatchPackageOptions,
} from "./vocabulary-batch/index.js";

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
