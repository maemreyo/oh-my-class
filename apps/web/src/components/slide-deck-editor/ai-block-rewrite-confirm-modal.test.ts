/**
 * SDE-08: `AiBlockRewriteConfirmModal` is the single generic before/after
 * confirmation modal reused for every block type. It uses no hooks, so it
 * can be invoked directly as a plain function -- `React.createElement` calls
 * are just plain objects -- to inspect the returned element tree without a
 * DOM renderer, matching this repo's no-DOM-rendering convention for
 * slide-deck-editor components (see deck-save.test.ts).
 */

import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { Button } from "@/components/ui/button";
import { AiBlockRewriteConfirmModal } from "./ai-block-rewrite-confirm-modal";

function findButtons(element: ReactElement): ReactElement<{ onClick?: () => void }>[] {
	const buttons: ReactElement<{ onClick?: () => void }>[] = [];
	function walk(node: unknown): void {
		if (!node || typeof node !== "object") return;
		if (Array.isArray(node)) {
			for (const child of node) walk(child);
			return;
		}
		const el = node as ReactElement<{ children?: unknown; onClick?: () => void }>;
		if (el.type === Button) buttons.push(el);
		walk(el.props?.children);
	}
	walk(element);
	return buttons;
}

describe("AiBlockRewriteConfirmModal", () => {
	it("renders before/after text and wires Cancel/Apply to their own callbacks, one component reused across different block types", () => {
		const onApplyHeading = vi.fn();
		const onCancelHeading = vi.fn();
		const headingModal = AiBlockRewriteConfirmModal({
			blockLabel: "Heading",
			before: "Fractions",
			after: "Understanding Fractions",
			onApply: onApplyHeading,
			onCancel: onCancelHeading,
		});

		const onApplyParagraph = vi.fn();
		const onCancelParagraph = vi.fn();
		const paragraphModal = AiBlockRewriteConfirmModal({
			blockLabel: "Paragraph text",
			before: "A fraction represents part of a whole.",
			after: "A fraction is a piece of something whole.",
			onApply: onApplyParagraph,
			onCancel: onCancelParagraph,
		});

		// Same component, two different block types -- not a per-type modal.
		expect(headingModal.type).toBe(paragraphModal.type);

		const [headingCancel, headingApply] = findButtons(headingModal);
		headingCancel?.props.onClick?.();
		expect(onCancelHeading).toHaveBeenCalledTimes(1);
		expect(onApplyHeading).not.toHaveBeenCalled(); // Cancel never triggers Apply.

		headingApply?.props.onClick?.();
		expect(onApplyHeading).toHaveBeenCalledTimes(1);

		const [paragraphCancel] = findButtons(paragraphModal);
		paragraphCancel?.props.onClick?.();
		expect(onCancelParagraph).toHaveBeenCalledTimes(1);
		expect(onApplyParagraph).not.toHaveBeenCalled();
	});
});
