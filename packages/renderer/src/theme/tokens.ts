/**
 * Three-tier CSS token structure.
 * Tier 1 (primitives): raw values — not used directly in templates
 * Tier 2 (semantic):   purpose-named — used in components
 * Tier 3 (component):  component-scoped overrides — optional
 */

export interface PrimitiveTokens {
  colorPalette: Record<string, string>;
  spacing: Record<string, string>;
  fontFamilyHeading: string;
  fontFamilyBody: string;
  fontFamilyMono: string;
  fontSizeScale: Record<string, string>;
  fontWeightScale: Record<string, number>;
  borderRadius: Record<string, string>;
  shadow: Record<string, string>;
}

export interface SemanticTokens {
  colorBg: string;
  colorBgCard: string;
  colorBgDeep: string;
  colorText: string;
  colorTextSoft: string;
  colorTextFaint: string;
  colorBorder: string;
  colorBorderSoft: string;
  colorAccent: string;
  colorAccentDeep: string;
  colorAccentTint: string;
  colorSuccess: string;
  colorWarning: string;
  colorError: string;
  categoryColors: Record<string, { base: string; tint: string }>;
}

export interface ComponentTokens {
  questionCardRadius?: string;
  questionCardShadow?: string;
  flashcardHeight?: string;
  flashcardRadius?: string;
}

export interface ThemeTokens {
  name: string;
  primitives: PrimitiveTokens;
  semantic: SemanticTokens;
  component?: ComponentTokens;
}
