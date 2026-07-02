/**
 * Transit-Route adapter (Issue 013).
 *
 * Converts VideoRouteData into TransitRouteVideoTemplateData for
 * the transit-route/video-route.html template.
 *
 * INVARIANT-04: No <video> or <iframe> src emitted — videoMetadata is
 * metadata only. The template renders a placeholder, not an embedded video.
 */

import type { VideoRouteData, VideoRouteStation } from "../../contracts/video-route.js";

const CAT_NAMES = ["cat1", "cat2", "cat3", "cat4", "cat5", "cat6", "cat7"] as const;

export interface TemplateStation {
  code: string;
  cat: string;
  title: string;
  sub: string;
  cueText?: string;
}

export interface TransitRouteVideoTemplateData {
  artifactCss: string;
  lang: string;
  title: string;
  routeTitle?: string;
  unit?: string;
  videoDuration?: string;
  estimatedMinutes?: number;
  stations: TemplateStation[];
  completionBadge?: string;
}

function mapStation(s: VideoRouteStation, index: number): TemplateStation {
  const catIndex = s.catIndex != null ? s.catIndex - 1 : index;
  const cat = CAT_NAMES[catIndex % CAT_NAMES.length];
  const cueText = s.cues?.map((c) => c.text).join(" · ");
  return {
    code: s.code,
    cat,
    title: s.title,
    sub: s.description,
    cueText,
  };
}

export function adaptVideoRoute(
  data: VideoRouteData,
  artifactCss: string,
): TransitRouteVideoTemplateData {
  return {
    artifactCss,
    lang: data.lang ?? "vi",
    title: data.title,
    routeTitle: data.routeTitle,
    unit: data.unit,
    videoDuration: data.videoMetadata?.videoDuration,
    estimatedMinutes: data.estimatedMinutes,
    stations: data.stations.map((s, i) => mapStation(s, i)),
    completionBadge: data.completionBadge,
  };
}

// ── Legacy VideoRouteInput shape — kept for callers not yet on VideoRouteData ──

export interface VideoRouteStation_Legacy {
  code: string;
  cat: string;
  title: string;
  sub: string;
  cueText?: string;
}

export interface VideoRouteInput {
  title: string;
  routeTitle?: string;
  unit?: string;
  videoDuration?: string;
  estimatedMinutes?: number;
  stations: VideoRouteStation_Legacy[];
  completionBadge?: string;
  lang?: string;
}

export function adaptVideoRouteLegacy(
  input: VideoRouteInput,
  artifactCss: string,
): TransitRouteVideoTemplateData {
  return {
    artifactCss,
    lang: input.lang ?? "vi",
    title: input.title,
    routeTitle: input.routeTitle,
    unit: input.unit,
    videoDuration: input.videoDuration,
    estimatedMinutes: input.estimatedMinutes,
    stations: input.stations,
    completionBadge: input.completionBadge,
  };
}
