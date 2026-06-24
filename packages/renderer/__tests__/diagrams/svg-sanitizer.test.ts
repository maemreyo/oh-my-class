import { describe, it, expect } from 'vitest'
import { sanitizeSVG } from '../../src/diagrams/svg-sanitizer.js'

describe('sanitizeSVG', () => {
  it('passes clean SVG through unchanged in structure', () => {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="blue"/></svg>'
    const out = sanitizeSVG(svg)
    expect(out).toContain('<circle')
    expect(out).toContain('<svg')
  })

  it('strips <script> elements', () => {
    const svg = '<svg><script>alert("xss")</script><rect width="100" height="100"/></svg>'
    const out = sanitizeSVG(svg)
    expect(out).not.toContain('<script')
    expect(out).not.toContain('alert')
  })

  it('strips <foreignObject> and <div> elements (not SVG tags)', () => {
    const svg = '<svg><foreignObject><div>label text</div></foreignObject><circle r="5"/></svg>'
    const out = sanitizeSVG(svg)
    expect(out).not.toContain('foreignObject')
    expect(out).not.toContain('<div')
    expect(out).toContain('<circle')
  })

  it('strips inline event handlers (onclick, onload)', () => {
    const svg = '<svg><rect onclick="evil()" onload="evil()" width="100" height="100"/></svg>'
    const out = sanitizeSVG(svg)
    expect(out).not.toContain('onclick')
    expect(out).not.toContain('onload')
    expect(out).not.toContain('evil()')
  })

  it('preserves geometric attributes', () => {
    const svg = '<svg viewBox="0 0 200 200"><rect x="10" y="10" width="80" height="80" fill="red" stroke="black" stroke-width="2"/></svg>'
    const out = sanitizeSVG(svg)
    expect(out).toContain('x="10"')
    expect(out).toContain('fill="red"')
    expect(out).toContain('stroke-width="2"')
  })

  it('preserves text elements', () => {
    const svg = '<svg><text x="20" y="30" font-size="16">Hello</text></svg>'
    const out = sanitizeSVG(svg)
    expect(out).toContain('<text')
    expect(out).toContain('Hello')
  })

  it('extracts <svg> from LLM prose/markdown wrapper', () => {
    const wrapped = 'Here is your SVG:\n```\n<svg viewBox="0 0 100 100"><circle r="10"/></svg>\n```'
    const out = sanitizeSVG(wrapped)
    expect(out).toContain('<svg')
    expect(out).toContain('<circle')
    expect(out).not.toContain('Here is your SVG')
  })

  it('wraps bare SVG content (no root <svg>) in a default svg element', () => {
    const bare = '<circle cx="50" cy="50" r="20" fill="green"/>'
    const out = sanitizeSVG(bare)
    expect(out.trim()).toMatch(/^<svg/)
    expect(out).toContain('<circle')
  })

  it('handles empty string gracefully', () => {
    const out = sanitizeSVG('')
    expect(out).toBeDefined()
    expect(typeof out).toBe('string')
  })
})
