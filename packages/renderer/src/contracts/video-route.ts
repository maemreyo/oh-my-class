/**
 * Video Learning Route contract (Issue 013).
 *
 * Used exclusively by renderArtifactUi() with the transit-route family.
 * NOT added to ArtifactDataMap — render-layer concept only (ADR-024).
 *
 * INVARIANT-04: No <video> or <iframe> src in output — videoMetadata is
 * metadata only. The template renders a placeholder, not an embedded video.
 */

export interface VideoRouteCue {
  text: string;
  emphasis?: boolean;
}

export interface VideoRouteStation {
  code: string;
  title: string;
  description: string;
  catIndex?: number;   // 1–7, maps to --art-cat-1..7; auto-assigned if omitted
  cues?: VideoRouteCue[];
}

export interface VideoRouteMetadata {
  videoDuration?: string;    // display string e.g. "3:20"
  videoTitle?: string;       // title of the source video
  channel?: string;          // channel/author name — NOT a URL
  difficulty?: "easy" | "medium" | "hard";
}

export interface VideoRouteData {
  title: string;
  subject: string;
  gradeLevel: string;
  unit?: string;              // e.g. "Unit 2 · Travel & Transport"
  routeTitle?: string;        // header line under title (defaults to title)
  estimatedMinutes?: number;
  videoMetadata?: VideoRouteMetadata;
  stations: VideoRouteStation[];
  completionBadge?: string;   // e.g. "5/6 trạm hoàn thành tốt"
  theme?: string;
  lang?: string;
}
