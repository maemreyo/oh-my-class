// ColorTheme — WCAG-compliant colors for infographic generation
export interface ColorTheme {
  primary:    string   // headings, accents
  secondary:  string   // supporting elements
  background: string   // page background
  text:       string   // body text
  accent:     string[] // data series (3-6 colors)
  contrastRatios: {
    textOnBg:      number   // must be >= 4.5:1
    largeTextOnBg: number   // must be >= 3:1
  }
}

// DiagramData — DG3: LLM generates SVG, renderer sanitizes + embeds
export interface DiagramNode {
  id:    string
  label: string
  x?:    number
  y?:    number
  style?: string
}

export interface DiagramEdge {
  from:   string
  to:     string
  label?: string
}

export interface DiagramData {
  type:  'flowchart' | 'venn' | 'cycle' | 'hierarchy' | 'timeline'
  nodes: DiagramNode[]
  edges: DiagramEdge[]
}

export type RichTextContent = string   // HTML string, sanitized before rendering

// InfographicSection — one visual block within an infographic
export interface InfographicSectionStyle {
  backgroundColor?: string
  textColor?:       string
  icon?:            string
  borderStyle?:     'solid' | 'dashed' | 'none'
}

export interface FullInfographicSection {
  id:      string
  type:    'header' | 'body' | 'stat' | 'quote' | 'step' | 'comparison_column' | 'diagram' | 'callout'
  title?:  string
  content: RichTextContent
  position?: { x: number; y: number; width: number; height: number }
  style?:    InfographicSectionStyle
  diagramData?: DiagramData
}

// FullInfographic — rich agent-generated infographic (separate from thin InfographicData renderer type)
export interface FullInfographic {
  id:      string
  title:   string
  subject: string
  topic:   string
  layout:  'vertical' | 'horizontal' | 'grid' | 'timeline' | 'flowchart' | 'comparison' | 'diagram'
  width:   number   // px
  height:  number   // px
  theme:   ColorTheme
  sections: FullInfographicSection[]
  alternativeText: string
  longDescription?: string
}
