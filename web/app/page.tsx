import Link from 'next/link'

const STATS = [
  { value: '935',  label: 'Ingredients' },
  { value: '436k', label: 'Scored pairs' },
  { value: '128',  label: 'Embedding dims' },
  { value: 'GAT',  label: 'Model architecture' },
]

const FEATURES = [
  {
    num: '01', href: '/search', title: 'Ingredient Search',
    desc: 'Type any ingredient and surface its top molecular pairings, ranked by a surprise score that balances pairing quality against culinary familiarity.',
    tag: 'Search',
  },
  {
    num: '02', href: '/rate', title: 'Rate & Improve',
    desc: 'The model is uncertain about some pairs — those whose predicted co-occurrence score hovers near 0.5. Rate them to trigger active learning fine-tuning.',
    tag: 'Active Learning',
  },
  {
    num: '03', href: '/graph', title: 'Flavor Graph',
    desc: 'Navigate the ingredient network visually. Click any node to re-center. Edge width reflects surprise score — thicker means more unexpected.',
    tag: 'Network Explorer',
  },
  {
    num: '04', href: '/recipe', title: 'Recipe Generation',
    desc: 'Pick 2–3 surprising ingredients and generate a recipe with molecular rationale. Claude explains the chemical bridges and proposes a dish.',
    tag: 'AI Generation',
  },
]

export default function Home() {
  return (
    <div className="-mx-12 -mt-10">
      {/* ── HERO ── */}
      <section className="relative px-16 pt-20 pb-[72px] border-b border-muted overflow-hidden">
        {/* SVG network decoration */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <svg
            viewBox="0 0 600 400"
            className="absolute right-0 top-0 w-[55%] h-full opacity-[0.18]"
            xmlns="http://www.w3.org/2000/svg"
          >
            <g stroke="#c4622a" strokeWidth="1" fill="none">
              <line x1="300" y1="200" x2="480" y2="100"/>
              <line x1="300" y1="200" x2="520" y2="220"/>
              <line x1="300" y1="200" x2="450" y2="320"/>
              <line x1="300" y1="200" x2="180" y2="80"/>
              <line x1="300" y1="200" x2="150" y2="280"/>
              <line x1="300" y1="200" x2="420" y2="180"/>
              <line x1="300" y1="200" x2="370" y2="310"/>
              <line x1="480" y1="100" x2="520" y2="220"/>
              <line x1="480" y1="100" x2="420" y2="180"/>
              <line x1="450" y1="320" x2="520" y2="220"/>
              <line x1="450" y1="320" x2="370" y2="310"/>
              <line x1="180" y1="80"  x2="420" y2="180"/>
              <line x1="150" y1="280" x2="370" y2="310"/>
              <line x1="100" y1="160" x2="180" y2="80"/>
              <line x1="100" y1="160" x2="150" y2="280"/>
              <line x1="560" y1="340" x2="520" y2="220"/>
              <line x1="560" y1="340" x2="450" y2="320"/>
            </g>
            <g fill="#c4622a">
              <circle cx="300" cy="200" r="7"/>
              <circle cx="480" cy="100" r="5"/>
              <circle cx="520" cy="220" r="4"/>
              <circle cx="450" cy="320" r="5"/>
              <circle cx="180" cy="80"  r="4"/>
              <circle cx="150" cy="280" r="4"/>
              <circle cx="420" cy="180" r="3.5"/>
              <circle cx="370" cy="310" r="3.5"/>
              <circle cx="100" cy="160" r="3"/>
              <circle cx="560" cy="340" r="3"/>
            </g>
          </svg>
        </div>

        <p className="font-sans text-[10px] font-bold tracking-[0.18em] uppercase text-accent mb-5">
          Graph Neural Network &middot; Molecular Gastronomy
        </p>
        <h1 className="font-serif font-normal text-dark leading-none tracking-[-0.03em] mb-6"
            style={{ fontSize: 'clamp(52px, 7vw, 88px)' }}>
          Discover hidden<br />
          <em className="not-italic text-accent">flavor pairings</em>
        </h1>
        <p className="font-sans text-base text-warm-mid leading-[1.7] max-w-[520px] mb-11">
          A graph neural network trained on flavor chemistry surfaces ingredient
          combinations that are scientifically compatible but culinarily underexplored.
          Explore the molecular bridges between unexpected ingredients.
        </p>
        <div className="flex gap-4">
          <Link href="/search"
            className="inline-flex items-center gap-2.5 bg-dark text-bg font-sans text-[11px] font-bold tracking-[0.12em] uppercase px-7 py-3.5 rounded-[3px] transition-all duration-150 hover:bg-accent hover:-translate-y-px"
          >
            Start Exploring <span className="text-sm">→</span>
          </Link>
          <Link href="/graph"
            className="inline-flex items-center gap-2.5 bg-transparent text-dark border border-muted font-sans text-[11px] font-bold tracking-[0.12em] uppercase px-7 py-3.5 rounded-[3px] transition-all duration-150 hover:border-accent hover:text-accent hover:-translate-y-px"
          >
            Explore Graph
          </Link>
        </div>
      </section>

      {/* ── STATS BAR ── */}
      <div className="flex border-b border-muted">
        {STATS.map((s, i) => (
          <div key={i} className={`flex-1 px-10 py-7 ${i < STATS.length - 1 ? 'border-r border-muted' : ''}`}>
            <div className="font-serif text-[36px] font-normal text-dark leading-none mb-1.5">{s.value}</div>
            <div className="font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── FEATURES ── */}
      <section className="px-16 pt-14 pb-16">
        <p className="font-serif text-[11px] tracking-[0.14em] uppercase text-warm-mid mb-8">What you can do</p>
        <div className="grid grid-cols-2 gap-px bg-muted border border-muted rounded overflow-hidden">
          {FEATURES.map((f) => (
            <Link
              key={f.href}
              href={f.href}
              className="group bg-card p-9 pb-8 flex flex-col gap-3 no-underline hover:bg-bg transition-colors duration-150"
            >
              <div className="font-sans text-[10px] font-bold tracking-[0.14em] uppercase text-accent">{f.num}</div>
              <div className="font-serif text-[22px] font-normal text-dark leading-snug">{f.title}</div>
              <p className="font-sans text-[13px] text-warm-mid leading-[1.65] flex-1">{f.desc}</p>
              <div className="flex items-center justify-between pt-4 mt-1 border-t border-muted">
                <span className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-accent bg-accent/8 border border-accent/20 px-2.5 py-0.5 rounded-sm">
                  {f.tag}
                </span>
                <span className="text-[18px] text-accent transition-transform duration-150 group-hover:translate-x-1">→</span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="px-16 py-6 border-t border-muted flex items-center justify-between">
        <span className="font-serif text-sm text-warm-mid">FlavorNet</span>
        <span className="font-sans text-[11px] text-warm-light tracking-[0.04em]">
          Graph Neural Network &middot; Flavor Chemistry &middot; Active Learning
        </span>
      </footer>
    </div>
  )
}
