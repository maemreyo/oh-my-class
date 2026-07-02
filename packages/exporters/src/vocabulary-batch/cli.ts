import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { stdin } from "node:process";
import { join } from "node:path";
import { z } from "zod";
import type { PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";

import { buildVocabularyBatchPackage } from "./index.js";

const PayloadSchema = z.object({
  batchId: z.string().min(1),
  title: z.string().min(1),
  outputDir: z.string().min(1),
  formats: z.array(z.enum(["html", "gift", "h5p"])).optional(),
  clusters: z.array(z.object({
    cluster: z.custom<SemanticAnchorCluster>((value) => typeof value === "object" && value !== null),
    practiceSet: z.custom<PracticeSet>((value) => typeof value === "object" && value !== null).optional(),
    teacherApproved: z.boolean().optional(),
    diagnostics: z.array(z.string()).optional(),
  })),
});

export async function runVocabularyBatchPackageCli(raw: string): Promise<string> {
  const payload = PayloadSchema.parse(JSON.parse(raw));
  const result = await buildVocabularyBatchPackage({
    batchId: payload.batchId,
    title: payload.title,
    formats: payload.formats,
    clusters: payload.clusters,
  });
  await mkdir(payload.outputDir, { recursive: true });
  const path = join(payload.outputDir, `${payload.batchId}.vocabulary-batch.zip`);
  await writeFile(path, result.zip);
  return JSON.stringify({ path, manifest: result.manifest });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  process.stdout.write(await runVocabularyBatchPackageCli(await readStdin()));
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)));
  }
  return Buffer.concat(chunks).toString("utf8");
}
