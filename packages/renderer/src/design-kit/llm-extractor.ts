/**
 * LLM-based token extraction — f.light fallback for HTML without CSS custom properties.
 * Only called when extractCSSVars() finds < 3 tokens.
 */
import type { ThemeTokens } from "../theme/tokens.js";

const EXTRACT_PROMPT = `You are a CSS design token extractor.

Analyze the following HTML and extract its visual design tokens.
Look for background colors, text colors, accent colors, border colors, and font families.
Map them to this schema:
- colorBg: main page background color
- colorBgCard: card/surface background color
- colorText: primary text color
- colorTextSoft: secondary/muted text color
- colorAccent: primary accent/brand color

Return ONLY valid JSON matching this structure:
{
  "colorBg": "#hex",
  "colorBgCard": "#hex",
  "colorText": "#hex",
  "colorTextSoft": "#hex",
  "colorAccent": "#hex"
}

HTML (first 8000 chars):
{html_excerpt}`;

export async function llmExtractTokens(
  html: string,
  llmClient: { chat: (opts: unknown) => Promise<{ content: string }> },
): Promise<Partial<ThemeTokens["semantic"]>> {
  const excerpt = html.slice(0, 8000);
  const response = await llmClient.chat({
    model: "f.light",
    messages: [
      {
        role: "user",
        content: EXTRACT_PROMPT.replace("{html_excerpt}", excerpt),
      },
    ],
    temperature: 0.0,
  });

  return JSON.parse(response.content) as Partial<ThemeTokens["semantic"]>;
}
