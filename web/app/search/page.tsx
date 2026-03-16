'use client'
import { useState, useRef } from 'react'
import ResultCard from '@/components/ResultCard'
import { CardSkeleton } from '@/components/Skeleton'
import { searchIngredient } from '@/lib/api'
import type { SearchResponse } from '@/lib/types'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleSearch(q: string) {
    const trimmed = q.trim()
    if (!trimmed) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await searchIngredient(trimmed)
      setResult(data)
    } catch (e) {
      const err = e as { status?: number }
      setError(err.status === 404
        ? `Ingredient "${trimmed}" not found. Try another name.`
        : 'Something went wrong. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="font-serif text-[32px] font-normal text-dark mb-1">Ingredient Search</h1>
        <p className="font-sans text-[13px] text-warm-mid tracking-[0.02em]">
          Molecular gastronomy &middot; Top 10 pairings ranked by surprise
        </p>
      </div>

      {/* Search input */}
      <form
        onSubmit={(e) => { e.preventDefault(); handleSearch(query) }}
        className="flex gap-3 mb-10"
      >
        <div className="flex-1 relative">
          <label className="block font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-1.5">
            Find pairings for any ingredient
          </label>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. strawberry, miso, cardamom"
            className="w-full font-serif text-base text-dark bg-card border-[1.5px] border-muted rounded px-3.5 py-2.5 outline-none transition-all duration-150 focus:border-accent focus:shadow-[0_0_0_2px_rgba(196,98,42,0.12)] placeholder:text-warm-light"
          />
        </div>
        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="self-end font-sans text-[11px] font-bold tracking-[0.08em] uppercase text-bg bg-accent px-6 py-2.5 rounded border-none cursor-pointer transition-colors duration-150 hover:bg-accent/80 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Search
        </button>
      </form>

      {/* Loading state */}
      {loading && (
        <div>
          <div className="h-10 w-64 bg-muted/60 animate-pulse rounded mb-6" />
          <div className="grid grid-cols-2 gap-6">
            {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="font-serif text-[15px] italic text-warm-mid py-6">{error}</p>
      )}

      {/* Results */}
      {result && (
        <div>
          <div className="flex items-baseline justify-between pb-4 mb-6 border-b border-muted">
            <h2 className="font-serif text-[28px] font-normal text-dark">
              Pairings for{' '}
              <em className="not-italic text-accent">{result.ingredient.charAt(0).toUpperCase() + result.ingredient.slice(1)}</em>
            </h2>
            <span className="font-sans text-[13px] text-warm-mid">{result.pairings.length} results</span>
          </div>
          <div className="grid grid-cols-2 gap-6">
            {result.pairings.map((p) => (
              <ResultCard key={p.name} pairing={p} />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && !result && (
        <p className="font-serif text-[15px] italic text-warm-mid py-6">
          Enter an ingredient above to explore its flavor pairings.
        </p>
      )}
    </>
  )
}
