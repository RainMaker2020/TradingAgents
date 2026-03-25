'use client'
type Props = { content: string; speakerA: string; speakerB: string }

export default function DebateView({ content, speakerA, speakerB }: Props) {
  if (!content) {
    return <p className="text-[#8c909f] text-sm">Waiting for debate to complete…</p>
  }
  const turns = content.split(/\n{2,}/).filter(Boolean)

  // Try to infer speaker from a leading "Name:" prefix; fall back to parity.
  function resolveSpeaker(turn: string, index: number): { isA: boolean; body: string } {
    const prefixMatch = turn.match(/^([^:\n]{1,40}):\s*/)
    if (prefixMatch) {
      const prefix = prefixMatch[1].trim().toLowerCase()
      const aKey = speakerA.toLowerCase()
      const bKey = speakerB.toLowerCase()
      if (prefix.includes(aKey) || aKey.includes(prefix))
        return { isA: true,  body: turn.slice(prefixMatch[0].length) }
      if (prefix.includes(bKey) || bKey.includes(prefix))
        return { isA: false, body: turn.slice(prefixMatch[0].length) }
    }
    return { isA: index % 2 === 0, body: turn }
  }

  return (
    <div className="space-y-3">
      {turns.map((turn, i) => {
        const { isA, body } = resolveSpeaker(turn, i)
        return (
          <div
            key={i}
            className={`rounded-lg p-4 ${isA ? 'bg-[#171f33]' : 'bg-[#131b2e]'}`}
          >
            <div
              className="text-[11px] font-semibold mb-2 uppercase tracking-wider"
              style={{
                color: isA ? '#adc6ff' : '#c2c6d6',
                fontFamily: 'var(--font-manrope)',
              }}
            >
              {isA ? speakerA : speakerB}
            </div>
            <p className="text-sm text-[#c2c6d6] leading-relaxed">{body}</p>
          </div>
        )
      })}
    </div>
  )
}
