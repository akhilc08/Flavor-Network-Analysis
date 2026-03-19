'use client'
import { useState, useEffect, useCallback } from 'react'
import PairCard from '@/components/PairCard'
import { RatePairSkeleton } from '@/components/Skeleton'
import { getUncertainPairs, submitRatings } from '@/lib/api'
import type { UncertainPair, RateResponse } from '@/lib/types'

function pairKey(pair: UncertainPair): string {
  return pair.pair_id
}

export default function RatePage() {
  const [pairs, setPairs] = useState<UncertainPair[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [ratings, setRatings] = useState<Record<string, number>>({})
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<RateResponse | null>(null)

  const fetchPairs = useCallback(async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    setRatings({})
    try {
      const data = await getUncertainPairs()
      setPairs(data.pairs)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load pairs. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPairs()
  }, [fetchPairs])

  function handleRate(key: string, value: number) {
    setRatings((prev) => ({ ...prev, [key]: value }))
  }

  const allRated = pairs.length > 0 && pairs.every((p) => (ratings[pairKey(p)] ?? 0) > 0)

  async function handleSubmit() {
    setSubmitting(true)
    setError(null)
    try {
      const ratingsList = pairs.map((p) => ({
        ingredient_a: p.ingredient_a,
        ingredient_b: p.ingredient_b,
        rating: ratings[pairKey(p)],
      }))
      const res = await submitRatings({ ratings: ratingsList })
      setResult(res)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Submission failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }


  return (
    <>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="font-serif text-[32px] font-normal text-dark mb-1">Rate Pairings</h1>
        <p className="font-sans text-[13px] text-warm-mid tracking-[0.02em]">
          Rate these flavor pairings to help improve the recommendation model
        </p>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <RatePairSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Error state */}
      {error && (
        <p className="font-serif text-[15px] italic text-warm-mid py-6">{error}</p>
      )}

      {/* Result panel */}
      {result && !loading && (
        <div className="bg-card border border-[#e8d5bc] rounded-xl p-8 flex flex-col gap-4 mb-8">
          <h2 className="font-serif text-[24px] font-normal text-dark">Ratings submitted</h2>
          <p className="font-sans text-[13px] text-warm-mid">
            Thank you — your feedback helps improve the recommendation model.
          </p>
          <button
            type="button"
            onClick={fetchPairs}
            className="self-start font-sans text-[11px] font-bold tracking-[0.08em] uppercase text-bg bg-accent px-6 py-2.5 rounded border-none cursor-pointer transition-colors duration-150 hover:bg-accent/80"
          >
            Rate more
          </button>
        </div>
      )}

      {/* Pair cards */}
      {!loading && !result && pairs.length > 0 && (
        <div className="flex flex-col gap-4">
          {pairs.map((pair) => (
            <PairCard
              key={pairKey(pair)}
              pair={pair}
              rating={ratings[pairKey(pair)] ?? 0}
              onRate={(v) => handleRate(pairKey(pair), v)}
            />
          ))}

          {/* Submit button */}
          <div className="mt-4">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!allRated || submitting}
              className="font-sans text-[11px] font-bold tracking-[0.08em] uppercase text-bg bg-accent px-8 py-3 rounded border-none cursor-pointer transition-colors duration-150 hover:bg-accent/80 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {submitting && (
                <span
                  className="inline-block h-3.5 w-3.5 rounded-full border-2 border-bg/40 border-t-bg animate-spin"
                  aria-hidden="true"
                />
              )}
              Submit Ratings
            </button>
            {!allRated && (
              <p className="font-sans text-[12px] text-warm-mid mt-2">
                Rate all {pairs.length} pairing{pairs.length !== 1 ? 's' : ''} to submit
              </p>
            )}
          </div>
        </div>
      )}

      {/* Empty / no pairs state */}
      {!loading && !error && !result && pairs.length === 0 && (
        <p className="font-serif text-[15px] italic text-warm-mid py-6">
          No pairs available for rating right now.
        </p>
      )}
    </>
  )
}
