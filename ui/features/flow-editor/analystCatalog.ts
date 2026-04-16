/** Display metadata for palette + canvas labels; IDs align with `enabled_analysts` in run config. */
export const ANALYST_CATALOG: { id: string; label: string; short: string }[] = [
  { id: 'market', label: 'Market Analyst', short: 'Market' },
  { id: 'news', label: 'News Analyst', short: 'News' },
  { id: 'fundamentals', label: 'Fundamentals Analyst', short: 'Fundamentals' },
  { id: 'social', label: 'Social Analyst', short: 'Social' },
]

export function analystLabel(id: string): string {
  return ANALYST_CATALOG.find((a) => a.id === id)?.label ?? id
}
