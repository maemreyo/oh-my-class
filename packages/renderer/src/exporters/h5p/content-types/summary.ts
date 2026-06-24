import type { RecapData } from '../../../contracts/recap.js'

export interface H5PSummaryContent {
  intro:      string
  summaries:  Array<{
    subContentId: string
    tip:          string
    summary:      string[]
  }>
  behaviour: { enableRetry: boolean; enableSolutionsButton: boolean }
  l10n: { resultLabel: string; scoreBarLabel: string }
}

export function recapToH5PSummary(recap: RecapData): H5PSummaryContent {
  return {
    intro: `<p>${recap.title}</p>`,
    summaries: recap.items.map((item, i) => ({
      subContentId: `recap-${i}`,
      tip:          item.concept,
      summary:      [item.summary],
    })),
    behaviour: { enableRetry: true, enableSolutionsButton: true },
    l10n:      { resultLabel: 'Your result', scoreBarLabel: 'Progress' },
  }
}
