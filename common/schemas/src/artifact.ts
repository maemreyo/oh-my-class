/**
 * @deprecated This file is HAND-WRITTEN. The canonical Zod schema is now
 * auto-generated in ./generated/artifact.ts from Pydantic models.
 * This file will be removed after migration. Use generated version instead.
 */

import { z } from "zod";

export const ArtifactContentSchema = z.object({
  artifact_type: z.enum([
    "lesson",
    "worksheet",
    "quiz",
    "drill",
    "recap",
    "infographic",
  ]),
  theme: z.string().default("default"),
  title: z.string().min(3).max(200),
  sections: z.array(z.record(z.unknown())).min(1),
  metadata: z.record(z.unknown()).default({}),
  accessibility: z
    .object({
      language: z.string().default("vi"),
      reading_level: z.string().optional(),
      alt_texts: z.record(z.string()).default({}),
    })
    .default({}),
});

export type ArtifactContent = z.infer<typeof ArtifactContentSchema>;
