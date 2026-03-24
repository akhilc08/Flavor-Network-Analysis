import type { Pairing } from '@/lib/types'
import ScoreBar from './ScoreBar'
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
    <div className="py-8 flex flex-col gap-3">
      {/* Ingredient name — display scale */}
      <h3 className="font-serif font-light text-[38px] text-dark leading-none capitalize">
        {pairing.name.charAt(0).toUpperCase() + pairing.name.slice(1)}
      </h3>

      {/* Score bar */}
      <ScoreBar label="Pairing Score" value={pairing.pairing_score} variant="pairing" />

      {/* Molecules */}
      <div className="flex flex-wrap gap-1.5">
        {pairing.shared_molecules.length > 0
          ? pairing.shared_molecules.map((m) => <MoleculeTag key={m} name={m} />)
          : <span className="font-sans text-[11px] italic text-warm-light">No shared molecules</span>
        }
      </div>

      {/* Why it works */}
      {pairing.shared_molecules.length > 0 && (
        <p className="font-serif text-[14px] italic text-warm-mid leading-relaxed">
          {whyItWorks(pairing.shared_molecules)}
        </p>
      )}
    </div>
  )
}
