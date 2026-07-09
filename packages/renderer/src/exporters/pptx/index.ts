import PptxGenJSValue from "pptxgenjs";

import type { SlideDeckData, SlideDeckMedia } from "../../contracts/slide_deck.js";
import {
  projectSlideDeckSurface,
  type ProjectedSlideDeckBlock,
  type ProjectedSlideDeckInteraction,
  type SlideDeckRenderSurface,
} from "../../slide-deck-projection.js";

// Re-exported so callers can catch the same fail-closed error the HTML
// renderer throws for the 20 ADR-041 layouts without a template (SDE-02).
export { SlideDeckUnsupportedLayoutError } from "../../slide-deck-projection.js";

// ponytail: pptxgenjs's .d.ts (UMD-style `export default` + `export as
// namespace`) gets mis-typed by `moduleResolution: NodeNext` as the whole
// module rather than unwrapped to its default export — re-assert the type
// that's already correct at runtime (verified: default import IS the ctor).
const PptxGenJS = PptxGenJSValue as unknown as typeof import("pptxgenjs")["default"];
type PptxSlide = ReturnType<InstanceType<typeof PptxGenJS>["addSlide"]>;

const SLIDE_WIDTH_IN = 10;
const MARGIN_IN = 0.5;
const CONTENT_WIDTH_IN = SLIDE_WIDTH_IN - MARGIN_IN * 2;
const CONTENT_TOP_IN = 1.3;
const CONTENT_BOTTOM_IN = 6.8;
const BLOCK_HEIGHT_IN = 0.9;
const IMAGE_HEIGHT_IN = 2.2;

/**
 * Converts a SlideDeckData into a visually-reasonable .pptx file (SDX-05).
 *
 * ponytail: one generic per-slide template (title + stacked blocks +
 * interactions) covers every layout — exact ADR-041 per-layout fidelity is
 * explicitly out of scope per the issue's AC2. Upgrade to per-layout
 * templates if/when PPTX becomes a primary (not offline-fallback) surface.
 *
 * Reuses `projectSlideDeckSurface` for the fail-closed unsupported-layout
 * gate and the teacher/student/print content split, so this export can
 * never leak teacher-only data any more than the HTML renderer already
 * can — no separate leak-guard reimplementation needed here.
 */
export class PPTXExporter {
  async export(deck: SlideDeckData, surface: SlideDeckRenderSurface = "student"): Promise<Buffer> {
    const projected = projectSlideDeckSurface({ ...deck, render_surface: surface });
    const mediaByBlockId = collectMedia(deck);
    const pptx = new PptxGenJS();
    pptx.title = projected.title;

    for (const slide of projected.slides) {
      const pptxSlide = pptx.addSlide();
      pptxSlide.addText(slide.title, {
        x: MARGIN_IN, y: 0.3, w: CONTENT_WIDTH_IN, h: 0.8,
        fontSize: 28, bold: true,
      });

      let y = CONTENT_TOP_IN;
      for (const block of slide.blocks) {
        if (y >= CONTENT_BOTTOM_IN) break; // ponytail: overflow slides aren't split, see follow-up note below
        y += renderBlock(pptxSlide, block, mediaByBlockId.get(block.blockId) ?? null, y);
      }
      for (const interaction of slide.interactions) {
        if (y >= CONTENT_BOTTOM_IN) break;
        y += renderInteraction(pptxSlide, interaction, y);
      }

      const differentiationNotes = slide.differentiationGuidance.map((note) => `[${note.level}] ${note.guidance}`);
      const notes = [...slide.facilitationNotes, ...slide.answerKeyNotes, ...differentiationNotes].join("\n");
      if (notes) pptxSlide.addNotes(notes);
    }

    const output = await pptx.write({ outputType: "nodebuffer" });
    return Buffer.isBuffer(output) ? output : Buffer.from(output as ArrayBuffer);
  }
}

export const pptxExporter = new PPTXExporter();

function collectMedia(deck: SlideDeckData): Map<string, SlideDeckMedia | null> {
  const byBlockId = new Map<string, SlideDeckMedia | null>();
  for (const slide of deck.slides) {
    for (const block of slide.blocks) {
      byBlockId.set(block.block_id, block.media ?? null);
    }
  }
  return byBlockId;
}

// Only embeds already-inline (data:) images, matching the renderer's
// existing inline-only asset policy for HTML — no network fetches here.
function renderBlock(
  pptxSlide: PptxSlide,
  block: ProjectedSlideDeckBlock,
  media: SlideDeckMedia | null,
  y: number,
): number {
  const inlineImageSource = media?.media_type === "image" && media.source.startsWith("data:") ? media.source : null;
  if (inlineImageSource) {
    pptxSlide.addImage({
      data: inlineImageSource,
      x: MARGIN_IN, y, w: 3, h: IMAGE_HEIGHT_IN,
      altText: media?.alt_text || block.mediaAltText,
    });
    return IMAGE_HEIGHT_IN;
  }
  const text = block.body || placeholderText(block);
  pptxSlide.addText(text || " ", {
    x: MARGIN_IN, y, w: CONTENT_WIDTH_IN, h: BLOCK_HEIGHT_IN,
    fontSize: block.blockType === "heading" ? 20 : 14,
    bold: block.blockType === "heading",
    bullet: block.blockType === "paragraph" || block.blockType === "callout",
  });
  return BLOCK_HEIGHT_IN;
}

function placeholderText(block: ProjectedSlideDeckBlock): string {
  if (block.mediaAltText) return `[${block.blockType}: ${block.mediaAltText}]`;
  return block.fallbackText;
}

function renderInteraction(pptxSlide: PptxSlide, interaction: ProjectedSlideDeckInteraction, y: number): number {
  const options = interaction.options
    .map((option) => `${option.correct ? "* " : "- "}${option.label}`)
    .join("\n");
  const text = [interaction.prompt, options].filter(Boolean).join("\n");
  pptxSlide.addText(text, {
    x: MARGIN_IN, y, w: CONTENT_WIDTH_IN, h: BLOCK_HEIGHT_IN,
    fontSize: 14, italic: true,
  });
  return BLOCK_HEIGHT_IN;
}
