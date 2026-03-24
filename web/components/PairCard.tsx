import type { UncertainPair } from '@/lib/types'
import MoleculeTag from '@/components/MoleculeTag'
import StarRating from '@/components/StarRating'

interface PairCardProps {
  pair: UncertainPair
  rating: number
  onRate: (v: number) => void
}

export default function PairCard({ pair, rating, onRate }: PairCardProps) {
  return (
    <div className="bg-card border border-muted rounded p-7 flex flex-col gap-5">
      {/* Ingredient names — display scale */}
      <h3 className="font-serif font-light text-[32px] text-dark leading-tight">
        <span className="capitalize">{pair.ingredient_a}</span>
        <span className="font-sans text-[18px] text-warm-light mx-3 align-middle">+</span>
        <span className="capitalize">{pair.ingredient_b}</span>
      </h3>

      {/* Molecule tags */}
      {pair.shared_molecules.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {pair.shared_molecules.map((mol) => (
            <MoleculeTag key={mol} name={mol} />
          ))}
        </div>
      )}

      {/* Star rating */}
      <StarRating value={rating} onChange={onRate} />
    </div>
  )
}
