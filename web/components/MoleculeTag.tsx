export default function MoleculeTag({ name }: { name: string }) {
  return (
    <span className="font-sans text-[11px] italic text-warm-mid bg-bg border border-muted rounded-sm px-2 py-0.5 inline-block">
      {name}
    </span>
  )
}
