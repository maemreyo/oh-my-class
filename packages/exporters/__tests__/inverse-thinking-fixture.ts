import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import type { InverseThinkingPack } from '../src/inverse-thinking.js'

const currentDir = dirname(fileURLToPath(import.meta.url))
const fixturePath = resolve(currentDir, '../../../tests/fixtures/inverse_thinking/positive/english_grammar.json')
const fixture = JSON.parse(readFileSync(fixturePath, 'utf8')) as { pack: InverseThinkingPack }

export const inverseThinkingPack = fixture.pack
