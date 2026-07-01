import type { PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";

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

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function list(items: readonly string[], className: string): string {
  if (items.length === 0) return "";
  return `<ul class="${className}">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function teacherPanel(title: string, items: readonly string[]): string {
  if (items.length === 0) return "";
  return `<aside class="teacher-panel"><strong>${escapeHtml(title)}</strong>${list(items, "teacher-list")}</aside>`;
}

function teachingBody(cluster: SemanticAnchorCluster, audience: SemanticAnchorProjectionAudience): string {
  const warningPanel = audience === "teacher" ? teacherPanel("Review flags", cluster.warnings) : "";
  const sourcePanel = audience === "teacher" ? teacherPanel("Source notes", cluster.teacher_source_notes) : "";
  const confidence = audience === "teacher" ? `<p class="teacher-meta">Title confidence: ${(cluster.title_confidence * 100).toFixed(0)}%</p>` : "";
  const anchors = cluster.anchors.map((anchor) => {
    const teacherOnly = audience === "teacher"
      ? `${teacherPanel("Teacher script", [anchor.teacher_script_vi])}${teacherPanel("Edge cases", anchor.edge_cases)}${teacherPanel("Anchor source notes", anchor.source_notes)}`
      : "";
    return `<article class="anchor-card">
      <h2>${escapeHtml(anchor.word)}</h2>
      <p><strong>Ấn tượng:</strong> ${escapeHtml(anchor.impression_vi)}</p>
      <p><strong>Core trigger:</strong> ${escapeHtml(anchor.core_trigger_en)}</p>
      <p><strong>Visual cue:</strong> ${escapeHtml(anchor.visual_cue_vi)}</p>
      ${list(anchor.semantic_chain, "semantic-chain")}
      <p><strong>Example:</strong> ${escapeHtml(anchor.example_en)}</p>
      <p><strong>Contrast:</strong> ${escapeHtml(anchor.contrast_note_vi)}</p>
      <p>${escapeHtml(anchor.student_explanation_vi)}</p>
      ${teacherOnly}
    </article>`;
  }).join("");
  return `${warningPanel}${confidence}${sourcePanel}<section class="summary"><h2>Cluster summary</h2>${list(cluster.summary_rows, "summary-list")}${list(cluster.contrast_notes, "contrast-list")}</section>${anchors}`;
}

function practiceBody(
  cluster: SemanticAnchorCluster,
  practiceSet: PracticeSet | undefined,
  audience: SemanticAnchorProjectionAudience,
): string {
  if (!practiceSet) {
    return `<section class="empty-state"><p>No practice set is attached to ${escapeHtml(cluster.title)}.</p></section>`;
  }
  return practiceSet.items.map((item, index) => {
    const teacherOnly = audience === "teacher"
      ? `<details class="teacher-panel" open><summary>Answer rationale</summary><p><strong>Answer:</strong> ${escapeHtml(item.answer)}</p><p>${escapeHtml(item.rationale)}</p></details>`
      : "";
    return `<article class="practice-item"><p class="eyebrow">${escapeHtml(item.intent.replaceAll("_", " "))}</p><h2>Practice ${index + 1}</h2><p>${escapeHtml(item.prompt)}</p>${teacherOnly}</article>`;
  }).join("");
}

function standaloneHtml(title: string, body: string, lang: string): string {
  return `<!DOCTYPE html>
<html lang="${escapeHtml(lang)}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)} — oh-my-class</title>
  <style>
    :root { color-scheme: light; --ink:#172033; --muted:#5d6678; --line:#d9e0ec; --surface:#ffffff; --panel:#f6f8fb; --accent:#4f46e5; }
    * { box-sizing: border-box; }
    body { margin:0; background:#f3f6fb; color:var(--ink); font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; line-height:1.55; }
    header, main, footer { width:min(960px, calc(100% - 32px)); margin:0 auto; }
    header { padding:32px 0 16px; }
    main { display:grid; gap:18px; padding-bottom:32px; }
    .brand, .eyebrow { color:var(--accent); font-size:12px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
    h1, h2 { margin:.2rem 0 .6rem; line-height:1.15; }
    .anchor-card, .practice-item, .summary, .empty-state { background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:20px; box-shadow:0 10px 24px rgba(23,32,51,.06); }
    .teacher-panel { background:#fff7ed; border:1px solid #fed7aa; border-radius:14px; color:#7c2d12; margin-top:12px; padding:12px; }
    .teacher-meta { color:var(--muted); font-size:14px; }
    ul { margin:10px 0 0; padding-left:22px; }
    footer { border-top:1px solid var(--line); color:var(--muted); padding:18px 0 32px; }
    @media print { body { background:white; } .anchor-card, .practice-item, .summary { box-shadow:none; break-inside:avoid; } }
  </style>
</head>
<body>
  <header><p class="brand">oh-my-class semantic anchoring</p><h1>${escapeHtml(title)}</h1></header>
  <main>${body}</main>
  <footer>Generated by oh-my-class</footer>
</body>
</html>`;
}

export function renderSemanticAnchorProjection(request: SemanticAnchorProjectionRequest): string {
  const body = request.kind === "teaching"
    ? teachingBody(request.cluster, request.audience)
    : practiceBody(request.cluster, request.practiceSet, request.audience);
  const audienceLabel = request.audience === "teacher" ? "Teacher" : "Student";
  const kindLabel = request.kind === "teaching" ? "Teaching" : "Practice";
  return standaloneHtml(`${request.cluster.title} · ${audienceLabel} ${kindLabel}`, body, request.lang ?? "vi");
}

export function renderSemanticAnchorProjectionSet(
  cluster: SemanticAnchorCluster,
  practiceSet: PracticeSet,
): SemanticAnchorProjectionSet {
  return {
    teachingTeacherHtml: renderSemanticAnchorProjection({ cluster, practiceSet, audience: "teacher", kind: "teaching" }),
    teachingStudentHtml: renderSemanticAnchorProjection({ cluster, practiceSet, audience: "student", kind: "teaching" }),
    practiceTeacherHtml: renderSemanticAnchorProjection({ cluster, practiceSet, audience: "teacher", kind: "practice" }),
    practiceStudentHtml: renderSemanticAnchorProjection({ cluster, practiceSet, audience: "student", kind: "practice" }),
  };
}
