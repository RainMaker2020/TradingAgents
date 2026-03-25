type Segment = {
  id: string
  label: string
}

type SegmentedControlProps = {
  segments: Segment[]
  activeId: string
  onChange: (id: string) => void
  ariaLabel: string
}

export default function SegmentedControl({
  segments,
  activeId,
  onChange,
  ariaLabel,
}: SegmentedControlProps) {
  return (
    <div className="ws-segmented" role="tablist" aria-label={ariaLabel}>
      {segments.map((segment) => {
        const active = segment.id === activeId
        return (
          <button
            key={segment.id}
            type="button"
            role="tab"
            aria-selected={active}
            className={`ws-segment ${active ? 'ws-segment-active' : ''}`.trim()}
            onClick={() => onChange(segment.id)}
          >
            {segment.label}
          </button>
        )
      })}
    </div>
  )
}
