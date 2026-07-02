import { strToU8, zip } from "fflate";
import type { PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";
import { renderBatch } from "@oh-my-class/renderer";
import type { RenderContext, RenderRequest, RenderResponse } from "@oh-my-class/renderer";
import { buildH5PPackage } from "../h5p-impl/packager.js";

export type VocabularyBatchExportFormat = "html" | "gift" | "h5p";

export type VocabularyBatchClusterInput = {
  readonly cluster: SemanticAnchorCluster;
  readonly practiceSet?: PracticeSet;
  readonly teacherApproved?: boolean;
  readonly diagnostics?: readonly string[];
};

export type VocabularyBatchPackageOptions = {
  readonly batchId: string;
  readonly title: string;
  readonly clusters: readonly VocabularyBatchClusterInput[];
  readonly formats?: readonly VocabularyBatchExportFormat[];
};

export type VocabularyBatchManifestFile = {
  readonly kind: string;
  readonly path: string;
  readonly manifest?: RenderResponse["manifest"];
};

export type VocabularyBatchManifestCluster = {
  readonly clusterId: string;
  readonly title: string;
  readonly terms: readonly string[];
  readonly status: SemanticAnchorCluster["review_status"];
  readonly exportStatus: "passed" | "needs_review" | "failed";
  readonly teacherApproved: boolean;
  readonly warnings: readonly string[];
  readonly files: readonly VocabularyBatchManifestFile[];
};

export type VocabularyBatchManifest = {
  readonly packageType: "vocabulary_batch";
  readonly batchId: string;
  readonly title: string;
  readonly generatedBy: "oh-my-class";
  readonly clusters: readonly VocabularyBatchManifestCluster[];
};

export type VocabularyBatchPackage = {
  readonly zip: Uint8Array;
  readonly manifest: VocabularyBatchManifest;
};

type ZipFileMap = Record<string, Uint8Array>;

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function safeSegment(value: string): string {
  const segment = value.toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
  return segment.length > 0 ? segment : "cluster";
}

function requestedFormats(formats: readonly VocabularyBatchExportFormat[] | undefined): ReadonlySet<VocabularyBatchExportFormat> {
  return new Set(formats ?? ["html"]);
}

function exportStatus(input: VocabularyBatchClusterInput): VocabularyBatchManifestCluster["exportStatus"] {
  if (input.cluster.review_status === "failed") return "failed";
  if (input.cluster.review_status === "needs_review" && input.teacherApproved !== true) return "needs_review";
  return "passed";
}

function addText(files: ZipFileMap, path: string, content: string): void {
  files[path] = strToU8(content);
}

function renderContext(audience: RenderContext["audience"], requestId: string): RenderContext {
  return {
    audience,
    locale: "vi",
    theme: "default",
    renderMode: "export",
    requestId,
    versions: { rendererVersion: "vocabulary-batch-exporter-v1" },
    assetPolicy: "inline-only",
  };
}

function vocabularyProjectionRequests(cluster: SemanticAnchorCluster, practiceSet: PracticeSet): readonly RenderRequest[] {
  return [
    {
      kind: "navy-ticket.teaching",
      input: { cluster },
      context: renderContext("teacher", `${cluster.cluster_id}:teaching:teacher`),
    },
    {
      kind: "navy-ticket.practice",
      input: { cluster, practiceSet },
      context: renderContext("teacher", `${cluster.cluster_id}:practice:teacher`),
    },
    {
      kind: "navy-ticket.teaching",
      input: { cluster },
      context: renderContext("student", `${cluster.cluster_id}:teaching:student`),
    },
    {
      kind: "navy-ticket.practice",
      input: { cluster, practiceSet },
      context: renderContext("student", `${cluster.cluster_id}:practice:student`),
    },
  ];
}

async function renderVocabularyProjections(cluster: SemanticAnchorCluster, practiceSet: PracticeSet): Promise<readonly RenderResponse[]> {
  return renderBatch({ requests: vocabularyProjectionRequests(cluster, practiceSet) });
}

function giftEscape(value: string): string {
  return value
    .replace(/\\/g, "\\\\")
    .replace(/~/g, "\\~")
    .replace(/=/g, "\\=")
    .replace(/\{/g, "\\{")
    .replace(/\}/g, "\\}")
    .replace(/#/g, "\\#");
}

function practiceGift(cluster: SemanticAnchorCluster, practiceSet: PracticeSet): string {
  const lines = [`$CATEGORY: oh-my-class/${giftEscape(cluster.cluster_id)}`, ""];
  for (const item of practiceSet.items) {
    lines.push(`::${giftEscape(item.item_id)}::[html]${giftEscape(item.prompt)}{`);
    lines.push(`  =${giftEscape(item.answer)}`);
    lines.push("}");
    lines.push("");
  }
  return lines.join("\n");
}

async function practiceH5P(cluster: SemanticAnchorCluster, practiceSet: PracticeSet): Promise<Uint8Array> {
  const cards = practiceSet.items.map((item) => ({
    text: item.prompt,
    answer: item.answer,
  }));
  return buildH5PPackage({
    title: `${cluster.title} Practice`,
    mainLibrary: "H5P.Flashcards",
    content: { cards },
    language: "vi",
  });
}

function diagnosticsHtml(input: VocabularyBatchClusterInput): string {
  const diagnostics = input.diagnostics ?? input.cluster.warnings;
  const items = diagnostics.length > 0 ? diagnostics : ["Cluster failed without additional diagnostics."];
  return `<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>${escapeHtml(input.cluster.title)} diagnostics — oh-my-class</title><style>body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:32px;line-height:1.5;color:#172033}main{max-width:780px}li{margin:.5rem 0}.status{color:#b91c1c;font-weight:800}</style></head><body><main><p>oh-my-class vocabulary diagnostics</p><h1>${escapeHtml(input.cluster.title)}</h1><p class="status">Failed cluster</p><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></main></body></html>`;
}

function renderIndex(manifest: VocabularyBatchManifest): string {
  const clusterCards = manifest.clusters.map((cluster) => {
    const warningHtml = cluster.warnings.length > 0
      ? `<ul>${cluster.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>`
      : "<p>No warnings.</p>";
    const links = cluster.files.length > 0
      ? `<ul>${cluster.files.map((file) => `<li><a href="${escapeHtml(file.path)}">${escapeHtml(file.kind)}</a></li>`).join("")}</ul>`
      : "<p>No export files available.</p>";
    return `<article><h2>${escapeHtml(cluster.title)}</h2><p><strong>Status:</strong> ${escapeHtml(cluster.exportStatus)}</p><p><strong>Terms:</strong> ${escapeHtml(cluster.terms.join(", "))}</p><h3>Warnings</h3>${warningHtml}<h3>Files</h3>${links}</article>`;
  }).join("");
  return `<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(manifest.title)} — oh-my-class</title>
  <style>body{margin:0;background:#f3f6fb;color:#172033;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.55}header,main,footer{width:min(1040px,calc(100% - 32px));margin:0 auto}header{padding:32px 0 16px}.brand{color:#4f46e5;font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}main{display:grid;gap:16px;padding-bottom:32px}article{background:#fff;border:1px solid #d9e0ec;border-radius:18px;padding:20px}a{color:#3730a3;font-weight:700}footer{border-top:1px solid #d9e0ec;color:#5d6678;padding:18px 0 32px}@media print{body{background:white}article{break-inside:avoid}}</style>
</head>
<body><header><p class="brand">oh-my-class vocabulary batch</p><h1>${escapeHtml(manifest.title)}</h1></header><main>${clusterCards}</main><footer>Generated by oh-my-class</footer></body>
</html>`;
}

async function zipFiles(files: ZipFileMap): Promise<Uint8Array> {
  return new Promise((resolve, reject) => {
    zip(files, (error, data) => {
      if (error) reject(error);
      else resolve(data);
    });
  });
}

export async function buildVocabularyBatchPackage(options: VocabularyBatchPackageOptions): Promise<VocabularyBatchPackage> {
  const formats = requestedFormats(options.formats);
  const files: ZipFileMap = {};
  const manifestClusters: VocabularyBatchManifestCluster[] = [];

  for (const input of options.clusters) {
    const cluster = input.cluster;
    const folder = `clusters/${safeSegment(cluster.cluster_id)}`;
    const status = exportStatus(input);
    const manifestFiles: VocabularyBatchManifestFile[] = [];

    if (status === "failed") {
      const path = `${folder}/diagnostics.html`;
      addText(files, path, diagnosticsHtml(input));
      manifestFiles.push({ kind: "diagnostics", path });
    } else if (formats.has("html")) {
      if (!input.practiceSet) {
        throw new Error(`Vocabulary batch cluster ${cluster.cluster_id} cannot export HTML without a PracticeSet`);
      }
      const [teachingTeacher, practiceTeacher, teachingStudent, practiceStudent] = await renderVocabularyProjections(cluster, input.practiceSet);
      const teacherTeaching = `${folder}/teaching-teacher.html`;
      addText(files, teacherTeaching, teachingTeacher.html);
      manifestFiles.push({ kind: "teaching_teacher_html", path: teacherTeaching, manifest: teachingTeacher.manifest });
      const teacherPractice = `${folder}/practice-teacher.html`;
      addText(files, teacherPractice, practiceTeacher.html);
      manifestFiles.push({ kind: "practice_teacher_html", path: teacherPractice, manifest: practiceTeacher.manifest });
      if (status === "passed") {
        const studentTeaching = `${folder}/teaching-student.html`;
        addText(files, studentTeaching, teachingStudent.html);
        manifestFiles.push({ kind: "teaching_student_html", path: studentTeaching, manifest: teachingStudent.manifest });
        const studentPractice = `${folder}/practice-student.html`;
        addText(files, studentPractice, practiceStudent.html);
        manifestFiles.push({ kind: "practice_student_html", path: studentPractice, manifest: practiceStudent.manifest });
      }
    }

    if (status === "passed" && input.practiceSet) {
      if (formats.has("gift")) {
        const path = `${folder}/practice.gift.txt`;
        addText(files, path, practiceGift(cluster, input.practiceSet));
        manifestFiles.push({ kind: "gift", path });
      }
      if (formats.has("h5p")) {
        const path = `${folder}/practice.h5p`;
        files[path] = await practiceH5P(cluster, input.practiceSet);
        manifestFiles.push({ kind: "h5p", path });
      }
    }

    manifestClusters.push({
      clusterId: cluster.cluster_id,
      title: cluster.title,
      terms: cluster.terms,
      status: cluster.review_status,
      exportStatus: status,
      teacherApproved: input.teacherApproved === true,
      warnings: cluster.warnings,
      files: manifestFiles,
    });
  }

  const manifest: VocabularyBatchManifest = {
    packageType: "vocabulary_batch",
    batchId: options.batchId,
    title: options.title,
    generatedBy: "oh-my-class",
    clusters: manifestClusters,
  };
  addText(files, "manifest.json", JSON.stringify(manifest, null, 2));
  addText(files, "index.html", renderIndex(manifest));
  return { zip: await zipFiles(files), manifest };
}
