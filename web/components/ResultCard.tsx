import type { Pairing } from '@/lib/types'
import ScoreBar from './ScoreBar'
import LabelPill from './LabelPill'
import MoleculeTag from './MoleculeTag'

function whyItWorks(molecules: string[]): string {
  if (!molecules.length) return ''
  if (molecules.length === 1) return `Both share the compound ${molecules[0]}.`
  const last = molecules[molecules.length - 1]
  const rest = molecules.slice(0, -1).join(', ')
  return `Both contain ${rest} and ${last}, bridging their flavor profiles.`
}

export default function ResultCard({ pairing }: { pairing: Pairing }) {
  return (
    <div className="group bg-card border border-muted rounded p-7 pb-6 flex flex-col gap-4 shadow-card transition-all duration-150 hover:shadow-card-hover hover:-translate-y-0.5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-serif text-[26px] font-normal text-dark leading-[1.15]">
          {pairing.name.charAt(0).toUpperCase() + pairing.name.slice(1)}
        </h3>
        <div className="mt-1 flex-shrink-0">
          <LabelPill label={pairing.label} />
        </div>
      </div>

      {/* Score bars */}
      <ScoreBar label="Pairing Score" value={pairing.pairing_score} variant="pairing" />
      <ScoreBar label="Surprise Score" value={pairing.surprise_score} variant="surprise" />

      {/* Molecules */}
      <div className="flex flex-wrap gap-1.5">
        {pairing.shared_molecules.length > 0
          ? pairing.shared_molecules.map((m) => <MoleculeTag key={m} name={m} />)
          : <span className="font-sans text-[11px] italic text-warm-light">No shared molecules</span>
        }
      </div>

      {/* Why it works */}
      {pairing.shared_molecules.length > 0 && (
        <p className="font-serif text-[13px] italic text-warm-mid leading-relaxed pt-3 border-t border-muted">
          {whyItWorks(pairing.shared_molecules)}
        </p>
      )}
    </div>
  )
}
