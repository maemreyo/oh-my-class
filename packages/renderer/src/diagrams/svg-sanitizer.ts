import sanitizeHtmlLib from 'sanitize-html'

// SVG-safe allowlist: structural + presentation elements, no scripts/foreignObject
const SVG_ALLOWLIST = {
  allowedTags: [
    'svg', 'g', 'defs', 'title', 'desc',
    // shapes
    'circle', 'ellipse', 'line', 'path', 'polygon', 'polyline', 'rect',
    // text
    'text', 'tspan', 'textPath',
    // layout
    'use', 'symbol', 'marker', 'clipPath', 'mask',
    // style
    'linearGradient', 'radialGradient', 'stop', 'pattern',
    // structural (group/container)
    'a', 'image',
  ],
  allowedAttributes: {
    '*': [
      // geometry
      'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry',
      'width', 'height', 'd', 'points', 'transform',
      // presentation
      'fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap',
      'stroke-linejoin', 'opacity', 'fill-opacity', 'stroke-opacity',
      'font-size', 'font-family', 'font-weight', 'text-anchor',
      'dominant-baseline', 'alignment-baseline',
      // ids/refs
      'id', 'class', 'style',
      // viewBox / namespace
      'viewBox', 'preserveAspectRatio', 'xmlns',
      // aria
      'aria-label', 'aria-hidden', 'role',
    ],
    'svg':  ['width', 'height', 'viewBox', 'xmlns', 'version'],
    'use':  ['href', 'xlink:href'],
    'a':    [], // strip href from <a> — no navigation from embedded SVG
    'image': ['href', 'xlink:href', 'x', 'y', 'width', 'height'],
  },
  allowedSchemes: ['data'],
  allowVulnerableTags: true,   // svg/style elements in SVG are intentional
}

/**
 * Sanitize LLM-generated SVG before inline embedding (DG3).
 * Strips: script, foreignObject, event handlers, external URLs.
 * Wraps bare SVG markup that lacks a root <svg> element.
 */
export function sanitizeSVG(raw: string): string {
  const trimmed = raw.trim()

  // Extract just the <svg>...</svg> if the LLM wrapped it in markdown/prose
  const svgMatch = trimmed.match(/<svg[\s\S]*?<\/svg>/i)
  const svgContent = svgMatch ? svgMatch[0] : trimmed

  const clean = sanitizeHtmlLib(svgContent, SVG_ALLOWLIST as Parameters<typeof sanitizeHtmlLib>[1])

  // If sanitizer stripped the svg root, wrap it
  if (!clean.trim().startsWith('<svg')) {
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">${clean}</svg>`
  }

  return clean
}
