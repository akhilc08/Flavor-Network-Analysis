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
    <div className="bg-card rounded-xl border border-[#e8d5bc] p-6 flex flex-col gap-4">
      {/* Ingredient names */}
      <div className="flex flex-col gap-1">
        <p className="font-serif text-[22px] font-normal text-dark">
          {pair.ingredient_a}{' '}
          <span className="text-warm-mid font-sans text-[18px]">+</span>{' '}
          {pair.ingredient_b}
        </p>
      </div>

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
