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

/** Same visual language as Profile presets (Fast / Balanced / Deep): btn-secondary + accent when active. */
export default function SegmentedControl({
  segments,
  activeId,
  onChange,
  ariaLabel,
}: SegmentedControlProps) {
  return (
    <div className="flex flex-wrap gap-2" role="tablist" aria-label={ariaLabel}>
      {segments.map((segment) => {
        const active = segment.id === activeId
        return (
          <button
            key={segment.id}
            type="button"
            role="tab"
            aria-selected={active}
            className="btn-secondary !h-[34px] !px-3 !py-0 text-xs"
            style={active ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : undefined}
            onClick={() => onChange(segment.id)}
          >
            {segment.label}
          </button>
        )
      })}
    </div>
  )
}
