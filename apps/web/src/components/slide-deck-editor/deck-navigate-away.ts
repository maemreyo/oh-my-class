/**
 * SDE-07: in-app "navigate away" guard, decoupled from `window.confirm`/
 * router calls so it's unit-testable. Only fires the confirm prompt (and the
 * single save call) when there's an actual unsaved draft -- no prompt, no
 * save, no-op navigate otherwise.
 */
export async function handleNavigateAway(args: {
	readonly hasUnsavedChanges: boolean;
	readonly confirmLeave: () => boolean;
	readonly save: () => Promise<{ readonly ok: boolean }>;
	readonly navigate: () => void;
}): Promise<void> {
	if (!args.hasUnsavedChanges) {
		args.navigate();
		return;
	}
	if (!args.confirmLeave()) return; // teacher chose to stay -- draft is untouched.
	const result = await args.save();
	if (result.ok) args.navigate();
	// On failure (incl. 409) stay put; the save() caller is responsible for
	// surfacing the error state and keeping the draft.
}
