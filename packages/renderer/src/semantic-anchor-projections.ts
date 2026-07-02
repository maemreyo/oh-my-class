/**
 * Semantic anchor projections — Artifact UI implementation (Issue 005).
 *
 * Delegates to renderArtifactUi() with the navy-ticket family.
 * Old inline CSS and string building removed.
 * Public types remain unchanged for backward compatibility.
 */

import type { PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";
import { renderArtifactUi } from "./artifact-ui/renderer.js";

export type SemanticAnchorProjectionAudience = "teacher" | "student";
export type SemanticAnchorProjectionKind = "teaching" | "practice";

export type SemanticAnchorProjectionRequest = {
  readonly cluster: SemanticAnchorCluster;
  readonly practiceSet?: PracticeSet;
  readonly audience: SemanticAnchorProjectionAudience;
  readonly kind: SemanticAnchorProjectionKind;
  readonly lang?: string;
};

export type SemanticAnchorProjectionSet = {
  readonly teachingTeacherHtml: string;
  readonly teachingStudentHtml: string;
  readonly practiceTeacherHtml: string;
  readonly practiceStudentHtml: string;
};

export async function renderSemanticAnchorProjection(
  request: SemanticAnchorProjectionRequest,
): Promise<string> {
  if (request.kind === "practice") {
    if (!request.practiceSet) {
      throw new Error(
        `renderSemanticAnchorProjection: kind='practice' requires a practiceSet for cluster "${request.cluster.cluster_id}".`,
      );
    }
    return renderArtifactUi({
      family: "navy-ticket",
      kind: "practice",
      audience: request.audience,
      cluster: request.cluster,
      practiceSet: request.practiceSet,
      lang: request.lang,
    });
  }
  return renderArtifactUi({
    family: "navy-ticket",
    kind: "teaching",
    audience: request.audience,
    cluster: request.cluster,
    lang: request.lang,
  });
}

export async function renderSemanticAnchorProjectionSet(
  cluster: SemanticAnchorCluster,
  practiceSet: PracticeSet,
): Promise<SemanticAnchorProjectionSet> {
  const [teachingTeacherHtml, teachingStudentHtml, practiceTeacherHtml, practiceStudentHtml] =
    await Promise.all([
      renderArtifactUi({ family: "navy-ticket", kind: "teaching", audience: "teacher", cluster }),
      renderArtifactUi({ family: "navy-ticket", kind: "teaching", audience: "student", cluster }),
      renderArtifactUi({ family: "navy-ticket", kind: "practice", audience: "teacher", cluster, practiceSet }),
      renderArtifactUi({ family: "navy-ticket", kind: "practice", audience: "student", cluster, practiceSet }),
    ]);
  return { teachingTeacherHtml, teachingStudentHtml, practiceTeacherHtml, practiceStudentHtml };
}
