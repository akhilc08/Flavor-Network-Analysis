import type { Metadata } from 'next'
import './globals.css'
import TopNav from '@/components/TopNav'
import { Cormorant_Garamond, DM_Sans } from 'next/font/google'

const cormorant = Cormorant_Garamond({
  subsets: ['latin'],
  variable: '--font-serif',
  weight: ['300', '400', '500', '600'],
  style: ['normal', 'italic'],
  display: 'swap',
})

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'FlavorNet',
  description: 'Discover hidden flavor pairings using graph neural networks.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${cormorant.variable} ${dmSans.variable}`}>
      <body className="bg-bg min-h-screen">
        <TopNav />
        <main className="mx-auto max-w-[1280px] px-12 py-10">
          {children}
        </main>
      </body>
    </html>
  )
}
