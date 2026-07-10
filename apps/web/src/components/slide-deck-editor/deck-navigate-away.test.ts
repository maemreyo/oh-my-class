import { describe, expect, it, vi } from "vitest";
import { handleNavigateAway } from "./deck-navigate-away";

describe("handleNavigateAway", () => {
	it("navigates immediately, without prompting, when there are no unsaved changes", async () => {
		const confirmLeave = vi.fn().mockReturnValue(true);
		const save = vi.fn();
		const navigate = vi.fn();

		await handleNavigateAway({ hasUnsavedChanges: false, confirmLeave, save, navigate });

		expect(confirmLeave).not.toHaveBeenCalled();
		expect(save).not.toHaveBeenCalled();
		expect(navigate).toHaveBeenCalledTimes(1);
	});

	it("shows the confirm prompt when there are unsaved changes", async () => {
		const confirmLeave = vi.fn().mockReturnValue(false);
		const save = vi.fn();
		const navigate = vi.fn();

		await handleNavigateAway({ hasUnsavedChanges: true, confirmLeave, save, navigate });

		expect(confirmLeave).toHaveBeenCalledTimes(1);
	});

	it("stays on the page (no save, no navigate) when the teacher declines the prompt", async () => {
		const confirmLeave = vi.fn().mockReturnValue(false);
		const save = vi.fn();
		const navigate = vi.fn();

		await handleNavigateAway({ hasUnsavedChanges: true, confirmLeave, save, navigate });

		expect(save).not.toHaveBeenCalled();
		expect(navigate).not.toHaveBeenCalled();
	});

	it("saves exactly once and then navigates when the teacher confirms", async () => {
		const confirmLeave = vi.fn().mockReturnValue(true);
		const save = vi.fn().mockResolvedValue({ ok: true });
		const navigate = vi.fn();

		await handleNavigateAway({ hasUnsavedChanges: true, confirmLeave, save, navigate });

		expect(save).toHaveBeenCalledTimes(1);
		expect(navigate).toHaveBeenCalledTimes(1);
	});

	it("stays on the page when the confirmed save fails (e.g. a 409)", async () => {
		const confirmLeave = vi.fn().mockReturnValue(true);
		const save = vi.fn().mockResolvedValue({ ok: false });
		const navigate = vi.fn();

		await handleNavigateAway({ hasUnsavedChanges: true, confirmLeave, save, navigate });

		expect(save).toHaveBeenCalledTimes(1);
		expect(navigate).not.toHaveBeenCalled();
	});
});
