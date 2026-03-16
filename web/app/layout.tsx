import type { Metadata } from 'next'
import './globals.css'
import TopNav from '@/components/TopNav'

export const metadata: Metadata = {
  title: 'FlavorNet',
  description: 'Discover hidden flavor pairings using graph neural networks.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-bg min-h-screen">
        <TopNav />
        <main className="mx-auto max-w-[1280px] px-12 py-10">
          {children}
        </main>
      </body>
    </html>
  )
}
