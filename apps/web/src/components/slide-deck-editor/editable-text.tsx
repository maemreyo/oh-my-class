"use client";

import { useState, type KeyboardEvent } from "react";

type EditableTextTag = "h2" | "p" | "span";

/**
 * Click-to-edit text primitive shared by every block/interaction editor.
 *
 * Pure UI mechanics only — no validation lives here. `onCommit` always
 * receives the raw draft string; callers run it through `clampOrReject`
 * (block-constraints.ts) before applying it, so this component never needs
 * to know a field's registry bounds beyond the `maxLength` HTML attribute
 * (a UX nicety, not the enforcement point).
 */
export function EditableText({
	value,
	onCommit,
	maxLength,
	as = "p",
	className = "",
	multiline = false,
	emptyLabel = "Click to add text",
	ariaLabel,
}: {
	readonly value: string;
	readonly onCommit: (draft: string) => void;
	readonly maxLength: number;
	readonly as?: EditableTextTag;
	readonly className?: string;
	readonly multiline?: boolean;
	readonly emptyLabel?: string;
	readonly ariaLabel?: string;
}) {
	const [editing, setEditing] = useState(false);
	const [draft, setDraft] = useState(value);

	function startEditing() {
		setDraft(value);
		setEditing(true);
	}

	function commit() {
		onCommit(draft);
		setEditing(false);
	}

	function cancel() {
		setDraft(value);
		setEditing(false);
	}

	function handleKeyDown(event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) {
		if (event.key === "Escape") cancel();
		if (event.key === "Enter" && !multiline) commit();
	}

	const fieldClassName = `w-full rounded-md border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring ${className}`;

	if (editing) {
		return multiline ? (
			<textarea
				autoFocus
				rows={3}
				className={fieldClassName}
				value={draft}
				maxLength={maxLength}
				aria-label={ariaLabel}
				onChange={(event) => setDraft(event.currentTarget.value)}
				onBlur={commit}
				onKeyDown={handleKeyDown}
			/>
		) : (
			<input
				autoFocus
				className={fieldClassName}
				value={draft}
				maxLength={maxLength}
				aria-label={ariaLabel}
				onChange={(event) => setDraft(event.currentTarget.value)}
				onBlur={commit}
				onKeyDown={handleKeyDown}
			/>
		);
	}

	const Tag = as;
	return (
		<Tag
			role="button"
			tabIndex={0}
			aria-label={ariaLabel}
			className={`cursor-text rounded-md px-2 py-1 hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring ${className}`}
			onClick={startEditing}
			onKeyDown={(event) => {
				if (event.key === "Enter") startEditing();
			}}
		>
			{value || <span className="italic text-muted-foreground">{emptyLabel}</span>}
		</Tag>
	);
}
