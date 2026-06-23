"use client";

import { motion } from "motion/react";
import type { Run } from "@/types";

interface RunCardProps {
	run: Run;
}

export function RunCard({ run }: RunCardProps) {
	return (
		<motion.div
			initial={{ opacity: 0, y: 10 }}
			animate={{ opacity: 1, y: 0 }}
			className="rounded-lg border border-border bg-card p-4 shadow-sm"
		>
			<div className="flex items-center justify-between">
				<h3 className="font-semibold">{run.topic || `Run ${run.run_id}`}</h3>
				<span className="rounded-full bg-primary/10 px-2 py-1 text-xs text-primary">
					{run.status}
				</span>
			</div>
			<p className="mt-2 text-sm text-muted-foreground">
				Step {run.current_step}/13 | {run.artifact_types?.join(", ")}
			</p>
			<a
				href={`/runs/${run.run_id}`}
				className="mt-2 inline-block text-sm text-primary hover:underline"
			>
				View details →
			</a>
		</motion.div>
	);
}
