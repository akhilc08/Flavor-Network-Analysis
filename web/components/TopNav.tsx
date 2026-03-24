'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV_LINKS = [
  { href: '/search', label: 'Search' },
  { href: '/rate', label: 'Rate' },
  { href: '/graph', label: 'Graph' },
  { href: '/recipe', label: 'Recipe' },
]

export default function TopNav() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-50 bg-dark border-b border-white/10">
      <nav className="mx-auto max-w-[1280px] px-12 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="font-serif text-[17px] text-bg tracking-tight hover:text-accent transition-colors duration-150"
        >
          FlavorNet
        </Link>

        {/* Nav links */}
        <ul className="flex items-center gap-8">
          {NAV_LINKS.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={[
                    'font-sans text-[10px] font-bold tracking-[0.14em] uppercase',
                    'transition-colors duration-150 pb-px',
                    active
                      ? 'text-bg border-b-2 border-accent'
                      : 'text-bg/50 hover:text-bg',
                  ].join(' ')}
                >
                  {label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
    </header>
  )
}
