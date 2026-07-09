/**
 * Unified export API.
 * All formats generated from the same ArtifactContent JSON — format-agnostic internal model.
 *
 * @packageDocumentation
 */

import type { ArtifactContent } from "@oh-my-class/schemas";
import { UnsupportedFormatError } from "./qti/qti.js";

export { UnsupportedFormatError } from "./qti/qti.js";

/**
 * Canonical export formats supported by the teaching-pack pipeline.
 *
 * - `"html"` — standalone HTML (via renderer, not exported here)
 * - `"gift"` — Moodle GIFT text format
 * - `"h5p"` — H5P interactive ZIP package
 * - `"qti"` — QTI 2.1 XML ZIP package
 * - `"anki_apkg"` — Anki deck package (via CLI bridge)
 * - `"flashcard_tsv"` — TSV flashcard list (via CLI bridge)
 * - `"pptx"` — PowerPoint slide deck
 *
 * Formats without a TypeScript implementation throw {@link UnsupportedFormatError}
 * when called through {@link exportByFormat}.
 */
export type ExportFormat =
	| "html"
	| "gift"
	| "h5p"
	| "qti"
	| "anki_apkg"
	| "flashcard_tsv"
	| "pptx";

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

/**
 * Export artifacts in the given format.
 *
 * Dynamically imports format-specific generators to keep the bundle small.
 * Formats without a TypeScript implementation (html, anki_apkg, flashcard_tsv,
 * google_forms, pptx) throw {@link UnsupportedFormatError} — use the Python
 * export adapter or CLI bridge for those.
 *
 * @param format - Target export format (one of {@link ExportFormat}).
 * @param artifacts - Array of {@link ArtifactContent} objects to export.
 * @returns A `Buffer` containing the exported file content.
 * @throws {UnsupportedFormatError} When the format has no TypeScript implementation yet.
 */
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
		case "html":
		case "anki_apkg":
		case "flashcard_tsv":
		case "pptx": {
			throw new UnsupportedFormatError(format);
		}
	}
}
