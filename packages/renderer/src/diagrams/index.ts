import type { DiagramData } from '../contracts/schemas/infographic.js'
import { sanitizeSVG } from './svg-sanitizer.js'

export { sanitizeSVG } from './svg-sanitizer.js'

type LLMClient = {
  chat(opts: {
    model:       string
    messages:    Array<{ role: string; content: string }>
    temperature?: number
  }): Promise<{ content: string }>
}

/**
 * DG3: LLM generates SVG from diagram data; renderer sanitizes + embeds inline.
 * Uses f.light (fast, zero-cost) since diagram generation is deterministic.
 */
export async function renderDiagram(data: DiagramData, llmClient: LLMClient): Promise<string> {
  const prompt = buildDiagramPrompt(data)
  const response = await llmClient.chat({
    model:       'f.light',
    messages:    [{ role: 'user', content: prompt }],
    temperature: 0.0,
  })
  return sanitizeSVG(response.content)
}

function buildDiagramPrompt(data: DiagramData): string {
  const nodeList = data.nodes.map(n => `  - ${n.id}: "${n.label}"`).join('\n')
  const edgeList = data.edges.map(e =>
    `  - ${e.from} → ${e.to}${e.label ? ` (${e.label})` : ''}`
  ).join('\n')

  return `Generate a clean SVG diagram for the following ${data.type} structure.
Output ONLY valid SVG markup — no prose, no markdown, no code fences.
Width: 600px, height: 400px, viewBox="0 0 600 400".
Use simple shapes (rect, circle, text, line, path). No scripts or external resources.

Nodes:
${nodeList}

Edges:
${edgeList}

SVG:`
}
