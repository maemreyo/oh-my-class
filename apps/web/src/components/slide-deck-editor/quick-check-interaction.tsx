"use client";

import type { SlideDeckInteraction } from "@oh-my-class/schemas";
import {
	INTERACTION_PROMPT_MAX,
	INTERACTION_PROMPT_MIN,
	OPTION_LABEL_MAX,
	OPTION_LABEL_MIN,
	RATIONALE_MAX,
	RATIONALE_MIN,
	clampOrReject,
} from "./block-constraints";
import { EditableText } from "./editable-text";

/**
 * SDE-02 registry: `quick_check` interaction (the only answer-bearing
 * interaction type the 5 renderer-supported layouts currently emit — see
 * `_practice_slide` in content_materialization.py). `multiple_choice_single`
 * shares the identical shape, so this component covers both, but only
 * `quick_check` ships in the deterministic generator today.
 */
export function applyQuickCheckPromptEdit(interaction: SlideDeckInteraction, draft: string): SlideDeckInteraction {
	const result = clampOrReject(draft, INTERACTION_PROMPT_MIN, INTERACTION_PROMPT_MAX);
	return result.ok ? { ...interaction, prompt: result.value } : interaction;
}

export function applyQuickCheckOptionLabelEdit(
	interaction: SlideDeckInteraction,
	optionId: string,
	draft: string,
): SlideDeckInteraction {
	const result = clampOrReject(draft, OPTION_LABEL_MIN, OPTION_LABEL_MAX);
	if (!result.ok) return interaction;
	const options = interaction.options ?? [];
	return {
		...interaction,
		options: options.map((option) => (option.option_id === optionId ? { ...option, label: result.value } : option)),
	};
}

/** Single-select: marking one option correct always replaces the whole set. */
export function setQuickCheckCorrectOption(interaction: SlideDeckInteraction, optionId: string): SlideDeckInteraction {
	if (!interaction.teacher_only) return interaction;
	return { ...interaction, teacher_only: { ...interaction.teacher_only, correct_option_ids: [optionId] } };
}

export function applyQuickCheckRationaleEdit(interaction: SlideDeckInteraction, draft: string): SlideDeckInteraction {
	if (!interaction.teacher_only) return interaction;
	const result = clampOrReject(draft, RATIONALE_MIN, RATIONALE_MAX);
	return result.ok ? { ...interaction, teacher_only: { ...interaction.teacher_only, rationale: result.value } } : interaction;
}

export function QuickCheckInteraction({
	interaction,
	onChange,
}: {
	readonly interaction: SlideDeckInteraction;
	readonly onChange: (next: SlideDeckInteraction) => void;
}) {
	const options = interaction.options ?? [];
	const correctIds = new Set(interaction.teacher_only?.correct_option_ids ?? []);

	return (
		<div
			className="space-y-3 rounded-md border border-primary/40 bg-primary/5 p-3"
			aria-label="Quick check interaction"
		>
			<p className="text-xs font-semibold uppercase tracking-wide text-primary">Quick check</p>
			<EditableText
				as="p"
				className="font-medium"
				value={interaction.prompt}
				maxLength={INTERACTION_PROMPT_MAX}
				multiline
				ariaLabel="Quick check question"
				onCommit={(draft) => onChange(applyQuickCheckPromptEdit(interaction, draft))}
			/>
			<ul className="space-y-2">
				{options.map((option) => (
					<li key={option.option_id} className="flex items-center gap-2">
						<input
							type="radio"
							name={`${interaction.interaction_id}-correct`}
							checked={correctIds.has(option.option_id)}
							aria-label={`Mark "${option.label}" as the correct answer`}
							onChange={() => onChange(setQuickCheckCorrectOption(interaction, option.option_id))}
						/>
						<div className="flex-1">
							<EditableText
								as="span"
								className="block text-sm"
								value={option.label}
								maxLength={OPTION_LABEL_MAX}
								ariaLabel="Answer option text"
								onCommit={(draft) => onChange(applyQuickCheckOptionLabelEdit(interaction, option.option_id, draft))}
							/>
						</div>
					</li>
				))}
			</ul>
			{interaction.teacher_only ? (
				<div>
					<p className="text-xs font-medium text-muted-foreground">Teacher-only rationale</p>
					<EditableText
						as="p"
						className="text-sm"
						value={interaction.teacher_only.rationale}
						maxLength={RATIONALE_MAX}
						multiline
						ariaLabel="Teacher-only rationale"
						onCommit={(draft) => onChange(applyQuickCheckRationaleEdit(interaction, draft))}
					/>
				</div>
			) : null}
		</div>
	);
}
