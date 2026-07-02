/**
 * Artifact UI family registry.
 *
 * Adding a new family = one new entry here + CSS files + Eta templates + adapter.
 * No changes to loader, renderer, or existing families.
 */

export interface ArtifactFamily {
  /** Unique ID — matches data-artifact-theme attribute value */
  readonly id: string;
  /** Human-readable display name */
  readonly name: string;
  /** Relative path to family token CSS (under src/artifact-ui/tokens/) */
  readonly tokenFile: string;
  /** Relative path to family component CSS (under src/artifact-ui/families/) */
  readonly familyFile: string;
  /** Eta template subdirectory (under templates/artifact/) */
  readonly templateDir: string;
  /** Adapter module name (under src/artifact-ui/adapters/) */
  readonly adapterName: string;
  /** Template kinds this family supports (maps to <kind>.html filenames) */
  readonly supportedKinds: readonly string[];
}

export const ARTIFACT_FAMILIES = [
  {
    id: "navy-ticket",
    name: "Navy Ticket",
    tokenFile: "tokens/navy-ticket.css",
    familyFile: "families/navy-ticket.css",
    templateDir: "navy-ticket",
    adapterName: "navy-ticket",
    supportedKinds: ["teaching.teacher", "teaching.student", "practice.teacher", "practice.student"],
  },
  {
    id: "paper-dossier",
    name: "Paper Dossier",
    tokenFile: "tokens/paper-dossier.css",
    familyFile: "families/paper-dossier.css",
    templateDir: "paper-dossier",
    adapterName: "paper-dossier",
    supportedKinds: ["lesson", "answer-key", "root-cause-session"],
  },
  {
    id: "transit-route",
    name: "Transit Route",
    tokenFile: "tokens/transit-route.css",
    familyFile: "families/transit-route.css",
    templateDir: "transit-route",
    adapterName: "transit-route",
    supportedKinds: ["video-route"],
  },
  {
    id: "investigation-folder",
    name: "Investigation Folder",
    tokenFile: "tokens/investigation-folder.css",
    familyFile: "families/investigation-folder.css",
    templateDir: "investigation-folder",
    adapterName: "investigation-folder",
    supportedKinds: ["inverse-thinking"],
  },
] as const satisfies readonly ArtifactFamily[];

export type ArtifactFamilyId = (typeof ARTIFACT_FAMILIES)[number]["id"];

/** Look up a family by ID. Throws a descriptive error for unknown IDs. */
export function getFamily(familyId: string): ArtifactFamily {
  const family = ARTIFACT_FAMILIES.find((f) => f.id === familyId);
  if (!family) {
    const known = ARTIFACT_FAMILIES.map((f) => f.id).join(", ");
    throw new Error(
      `Unknown Artifact UI family: "${familyId}". Known families: ${known}. ` +
      `To add a new family, see docs/artifact-ui-adding-a-family.md.`
    );
  }
  return family;
}
