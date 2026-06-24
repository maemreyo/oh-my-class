/**
 * Mulberry32 PRNG — deterministic, seed-based.
 * Same seed always produces the same sequence.
 * Required for reproducible/auditable exam variants (EV1).
 */

function mulberry32(seed: number): () => number {
  let s = seed | 0
  return function(): number {
    s = (s + 0x6D2B79F5) | 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function deterministicShuffle<T>(items: T[], seed: number): T[] {
  const rng    = mulberry32(seed)
  const result = [...items]
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [result[i], result[j]] = [result[j]!, result[i]!]
  }
  return result
}
