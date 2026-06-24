import type { ThemeTokens } from "./tokens.js";

export class ThemeCSSGenerator {
  /**
   * Convert ThemeTokens → CSS custom properties string for injection into :root {}.
   * Only semantic + component tokens become CSS vars — primitives are internal.
   */
  generate(tokens: ThemeTokens): string {
    const vars: string[] = [];

    const { semantic } = tokens;
    vars.push(
      `--color-bg: ${semantic.colorBg};`,
      `--color-bg-card: ${semantic.colorBgCard};`,
      `--color-bg-deep: ${semantic.colorBgDeep};`,
      `--color-text: ${semantic.colorText};`,
      `--color-text-soft: ${semantic.colorTextSoft};`,
      `--color-text-faint: ${semantic.colorTextFaint};`,
      `--color-border: ${semantic.colorBorder};`,
      `--color-border-soft: ${semantic.colorBorderSoft};`,
      `--color-accent: ${semantic.colorAccent};`,
      `--color-accent-deep: ${semantic.colorAccentDeep};`,
      `--color-accent-tint: ${semantic.colorAccentTint};`,
      `--color-success: ${semantic.colorSuccess};`,
      `--color-warning: ${semantic.colorWarning};`,
      `--color-error: ${semantic.colorError};`,
    );

    for (const [key, val] of Object.entries(semantic.categoryColors ?? {})) {
      vars.push(
        `--color-category-${key}: ${val.base};`,
        `--color-category-${key}-tint: ${val.tint};`,
      );
    }

    vars.push(
      `--font-heading: ${tokens.primitives.fontFamilyHeading};`,
      `--font-body: ${tokens.primitives.fontFamilyBody};`,
      `--font-mono: ${tokens.primitives.fontFamilyMono};`,
    );

    if (tokens.component) {
      const c = tokens.component;
      if (c.questionCardRadius) vars.push(`--question-card-radius: ${c.questionCardRadius};`);
      if (c.questionCardShadow) vars.push(`--question-card-shadow: ${c.questionCardShadow};`);
      if (c.flashcardHeight) vars.push(`--flashcard-height: ${c.flashcardHeight};`);
      if (c.flashcardRadius) vars.push(`--flashcard-radius: ${c.flashcardRadius};`);
    }

    return vars.join("\n      ");
  }
}
