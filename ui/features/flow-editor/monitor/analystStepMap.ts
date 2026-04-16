import type { AgentStep } from '@/lib/types/run'

/** Maps UI analyst ids (enabled_analysts) to LangGraph step keys streamed from the server. */
export const ANALYST_ID_TO_STEP: Record<string, AgentStep> = {
  market: 'market_analyst',
  news: 'news_analyst',
  fundamentals: 'fundamentals_analyst',
  social: 'social_analyst',
}

export function stepStatusForAnalyst(
  analystId: string,
  steps: Record<AgentStep, 'pending' | 'running' | 'done'>,
): 'pending' | 'running' | 'done' {
  const key = ANALYST_ID_TO_STEP[analystId]
  if (!key) return 'pending'
  return steps[key] === 'running' ? 'running' : steps[key] === 'done' ? 'done' : 'pending'
}
