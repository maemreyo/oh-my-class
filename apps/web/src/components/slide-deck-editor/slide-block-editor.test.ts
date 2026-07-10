/**
 * SDE-08: proves `SlideBlockEditor` wires the SAME `BlockRewriteControls`
 * instance (not a per-block-type variant) for at least two different block
 * types. `SlideBlockEditor` itself calls no hooks, so it can be invoked
 * directly as a plain function -- the JSX it returns is just plain
 * `React.createElement` objects -- to inspect the element tree without a DOM
 * renderer, matching this repo's no-DOM-rendering convention (see
 * deck-save.test.ts).
 */

import type { ReactElement } from "react";
import { SlideDeckBlockSchema, type SlideDeckBlock } from "@oh-my-class/schemas";
import { describe, expect, it, vi } from "vitest";
import { BlockRewriteControls } from "./block-rewrite-controls";
import { SlideBlockEditor } from "./slide-block-editor";

function findRewriteControls(element: ReactElement): ReactElement<{ blockLabel: string; onApply: (body: string) => void }> | undefined {
	function walk(node: unknown): ReactElement | undefined {
		if (!node || typeof node !== "object") return undefined;
		if (Array.isArray(node)) {
			for (const child of node) {
				const found = walk(child);
				if (found) return found;
			}
			return undefined;
		}
		const el = node as ReactElement<{ children?: unknown }>;
		if (el.type === BlockRewriteControls) return el;
		return walk(el.props?.children);
	}
	return walk(element) as ReactElement<{ blockLabel: string; onApply: (body: string) => void }> | undefined;
}

const headingBlock: SlideDeckBlock = SlideDeckBlockSchema.parse({ block_id: "block-heading", block_type: "heading", body: "Fractions" });
const paragraphBlock: SlideDeckBlock = SlideDeckBlockSchema.parse({
	block_id: "block-paragraph",
	block_type: "paragraph",
	body: "A fraction represents part of a whole.",
});

describe("SlideBlockEditor's generic AI-rewrite control", () => {
	it("uses the identical BlockRewriteControls component for both a heading and a paragraph block, each with its own label", () => {
		const headingEditor = SlideBlockEditor({
			block: headingBlock,
			onChange: vi.fn(),
			runId: "run-1",
			snapshotId: "snap-1",
			onBlockRewriteApplied: vi.fn(),
		});
		const paragraphEditor = SlideBlockEditor({
			block: paragraphBlock,
			onChange: vi.fn(),
			runId: "run-1",
			snapshotId: "snap-1",
			onBlockRewriteApplied: vi.fn(),
		});

		const headingControls = findRewriteControls(headingEditor);
		const paragraphControls = findRewriteControls(paragraphEditor);

		expect(headingControls).toBeDefined();
		expect(paragraphControls).toBeDefined();
		// Same component reference across two different block types -- not a
		// heading-specific and a paragraph-specific rewrite control.
		expect(headingControls?.type).toBe(paragraphControls?.type);
		expect(headingControls?.props.blockLabel).toBe("Heading");
		expect(paragraphControls?.props.blockLabel).toBe("Paragraph text");
	});

	it("applying a suggestion updates the block body and reports the block as AI-assisted, without touching other blocks", () => {
		const onChange = vi.fn();
		const onBlockRewriteApplied = vi.fn();
		const editor = SlideBlockEditor({
			block: paragraphBlock,
			onChange,
			runId: "run-1",
			snapshotId: "snap-1",
			onBlockRewriteApplied,
		});
		const controls = findRewriteControls(editor);

		controls?.props.onApply("A fraction is a piece of something whole.");

		expect(onChange).toHaveBeenCalledWith({ ...paragraphBlock, body: "A fraction is a piece of something whole." });
		expect(onBlockRewriteApplied).toHaveBeenCalledWith("block-paragraph");
	});
});
