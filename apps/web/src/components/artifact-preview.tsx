"use client";

import { motion } from "motion/react";
import type { Artifact } from "@/types";

interface ArtifactPreviewProps {
	artifact: Artifact;
}

/**
 * Renders LLM-generated HTML in a sandboxed iframe.
 * Security: sandbox="allow-same-origin" only — no allow-scripts.
 * The HTML is self-contained (no CDN, no external assets).
 */
export function ArtifactPreview({ artifact }: ArtifactPreviewProps) {
	const htmlContent = artifact.rendered_html || "";

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			className="overflow-hidden rounded-lg border border-border bg-card"
		>
			<div className="flex items-center justify-between border-b border-border p-3">
				<h3 className="font-medium">{artifact.title}</h3>
				<span className="text-xs text-muted-foreground">
					{artifact.artifact_type}
				</span>
			</div>
			<iframe
				srcDoc={htmlContent}
				sandbox="allow-same-origin"
				className="h-[600px] w-full border-0"
				title={artifact.title}
			/>
		</motion.div>
	);
}
