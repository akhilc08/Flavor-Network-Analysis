import type { PairingLabel } from '@/lib/types'

const STYLES: Record<PairingLabel, string> = {
  Surprising: 'bg-green/10 text-green border-green/25',
  Unexpected: 'bg-gold/10 text-gold border-gold/25',
  Classic:    'bg-accent/10 text-accent border-accent/25',
}

export default function LabelPill({ label }: { label: PairingLabel }) {
  return (
    <span
      className={[
        'font-sans text-[11px] font-semibold tracking-[0.08em] uppercase',
        'px-[10px] py-1 rounded-sm border whitespace-nowrap',
        STYLES[label] ?? STYLES.Classic,
      ].join(' ')}
    >
      {label}
    </span>
  )
}
