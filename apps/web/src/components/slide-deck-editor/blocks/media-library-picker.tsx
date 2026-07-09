"use client";

import { useEffect, useState } from "react";
import type { SlideDeckMedia } from "@oh-my-class/schemas";
import { Button } from "@/components/ui/button";
import { apiClient, gatewayUrl } from "@/lib/api-client";

/** Mirrors `MediaAssetResponse` in `services/gateway/routers/media_assets.py`. */
export interface MediaAsset {
	readonly asset_id: string;
	readonly filename: string;
	readonly content_type: string;
	readonly tags: readonly string[];
	readonly alt_text: string | null;
	readonly storage_key: string;
	readonly created_at: string;
}

export function mediaAssetFileUrl(assetId: string): string {
	return `${gatewayUrl()}/media-assets/${assetId}/file`;
}

/**
 * Maps a library asset onto a `SlideDeckMedia` block reference.
 *
 * `tier` is always `"online_optional"`, never `"packaged"` — these assets
 * are served from the gateway over http(s), not bundled with the renderer,
 * and `SlideDeckMedia`'s model_validator (`common/contracts/slide_deck.py`)
 * rejects `"packaged"` media with an http(s) `source`. `"online_optional"`
 * in turn requires `requires_network` and a non-empty `fallback_text`.
 *
 * `alt_text` can never be empty either way, so a still-`None` library
 * `alt_text` (the SDX-04 integration point — `None` until AI-authored alt
 * text or a teacher edit fills it in) falls back to the filename; the
 * teacher can still edit it via the existing "Alt text (required for
 * accessibility)" field in `image-block.tsx`.
 */
export function buildMediaFromAsset(asset: MediaAsset): SlideDeckMedia {
	return {
		media_id: asset.asset_id,
		media_type: "image",
		source: mediaAssetFileUrl(asset.asset_id),
		tier: "online_optional",
		alt_text: asset.alt_text?.trim() || asset.filename,
		fallback_text: asset.filename,
		requires_network: true,
	};
}

/** SDX-02: teacher-scoped media library picker, integrated into
 * `image-block.tsx`'s edit mode. Lists the calling teacher's own uploaded
 * assets (the gateway scopes `/media-assets` to the authenticated teacher —
 * no cross-teacher visibility), with filename search and upload. */
export function MediaLibraryPicker({
	onSelect,
	onClose,
}: {
	readonly onSelect: (media: SlideDeckMedia) => void;
	readonly onClose: () => void;
}) {
	const [assets, setAssets] = useState<MediaAsset[]>([]);
	const [query, setQuery] = useState("");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		let cancelled = false;
		setLoading(true);
		setError(null);
		const search = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
		apiClient
			.get<MediaAsset[]>(`/media-assets${search}`)
			.then((result) => {
				if (!cancelled) setAssets(result);
			})
			.catch((err: unknown) => {
				if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load library");
			})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});
		return () => {
			cancelled = true;
		};
	}, [query]);

	async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
		const file = event.target.files?.[0];
		event.target.value = "";
		if (!file) return;
		const form = new FormData();
		form.append("file", file);
		setLoading(true);
		setError(null);
		try {
			const created = await apiClient.postForm<MediaAsset>("/media-assets", form);
			setAssets((previous) => [created, ...previous]);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Upload failed");
		} finally {
			setLoading(false);
		}
	}

	return (
		<div
			role="dialog"
			aria-label="Media library"
			className="space-y-3 rounded-md border border-border bg-popover p-3 shadow-md"
		>
			<div className="flex items-center justify-between gap-2">
				<p className="text-sm font-medium">Choose from your library</p>
				<Button type="button" variant="ghost" size="sm" onClick={onClose}>
					Close
				</Button>
			</div>
			<input
				type="text"
				value={query}
				onChange={(event) => setQuery(event.target.value)}
				placeholder="Search by filename or tag"
				aria-label="Search media library"
				className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
			/>
			<label className="block text-xs text-muted-foreground">
				Upload a new image
				<input type="file" accept="image/*" onChange={handleUpload} aria-label="Upload a new image" className="mt-1 block text-sm" />
			</label>
			{error ? <p className="text-xs text-destructive">{error}</p> : null}
			{loading ? <p className="text-xs text-muted-foreground">Loading…</p> : null}
			<ul className="max-h-48 space-y-1 overflow-y-auto">
				{assets.map((asset) => (
					<li key={asset.asset_id}>
						<button
							type="button"
							onClick={() => onSelect(buildMediaFromAsset(asset))}
							className="w-full rounded-md border border-transparent px-2 py-1 text-left text-sm hover:border-border hover:bg-muted"
						>
							{asset.filename}
							{asset.tags.length > 0 ? (
								<span className="ml-2 text-xs text-muted-foreground">{asset.tags.join(", ")}</span>
							) : null}
						</button>
					</li>
				))}
				{!loading && assets.length === 0 ? (
					<li className="text-xs text-muted-foreground">No assets yet — upload one above.</li>
				) : null}
			</ul>
		</div>
	);
}
