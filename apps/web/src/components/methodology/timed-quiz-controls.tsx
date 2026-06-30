export type TimedQuizIntensity = "low-pressure" | "balanced" | "challenge";

export interface TimedQuizSettings {
	readonly durationMinutes: number;
	readonly intensity: TimedQuizIntensity;
}

export function updateTimedQuizSettings(
	settings: TimedQuizSettings,
	patch: Partial<TimedQuizSettings>,
): TimedQuizSettings {
	return { ...settings, ...patch };
}

export function validateTimedQuizDuration(durationMinutes: number): string[] {
	if (!Number.isInteger(durationMinutes) || durationMinutes < 1) return ["timed_quiz.duration_minutes"];
	if (durationMinutes > 180) return ["timed_quiz.duration_minutes"];
	return [];
}

export function TimedQuizControls({
	settings,
}: {
	readonly settings: TimedQuizSettings;
}) {
	const errors = validateTimedQuizDuration(settings.durationMinutes);
	return (
		<section className="mt-3 rounded-md border border-border bg-background p-3" aria-label="Timed Quiz controls">
			<h4 className="font-medium">Timing purpose</h4>
			<p className="mt-1 text-sm text-muted-foreground">Use time as pacing guidance, not pressure. Printed packs show text badges and avoid live countdown requirements.</p>
			<div className="mt-3 grid gap-2 md:grid-cols-2">
				<label className="space-y-1 text-sm">
					<span className="font-medium">Duration minutes</span>
					<input className="h-10 w-full rounded-md border border-input bg-background px-3" type="number" min={1} max={180} value={settings.durationMinutes} readOnly aria-invalid={errors.length > 0} />
				</label>
				<label className="space-y-1 text-sm">
					<span className="font-medium">Intensity</span>
					<select className="h-10 w-full rounded-md border border-input bg-background px-3" defaultValue={settings.intensity} aria-readonly="true">
						<option value="low-pressure">Low-pressure</option>
						<option value="balanced">Balanced</option>
						<option value="challenge">Challenge</option>
					</select>
				</label>
			</div>
			{errors.length > 0 ? <p role="alert" className="mt-2 text-sm text-destructive">Invalid duration: {errors.join(", ")}</p> : null}
			<p className="mt-3 text-sm text-muted-foreground">Preview metadata: {settings.durationMinutes} minutes, {settings.intensity} intensity.</p>
		</section>
	);
}
