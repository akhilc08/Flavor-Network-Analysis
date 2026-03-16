'use client'

import { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { getGraph } from '@/lib/api'
import type { GraphResponse } from '@/lib/types'

const FlavorGraph = dynamic(() => import('@/components/FlavorGraph'), { ssr: false })

export default function GraphPage() {
  const [center, setCenter] = useState('vanilla')
  const [maxNodes, setMaxNodes] = useState(30)
  const [minScore, setMinScore] = useState(0.5)
  const [data, setData] = useState<GraphResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function fetchGraph() {
    setLoading(true)
    setError(null)
    try {
      const result = await getGraph(center, maxNodes, minScore)
      setData(result)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Fetch on initial mount
  useEffect(() => {
    fetchGraph()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="font-serif text-[32px] font-normal text-dark mb-1">Flavor Network</h1>
        <p className="font-sans text-[13px] text-warm-mid tracking-[0.02em]">
          Explore ingredient relationships
        </p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-4 mb-8 items-end">
        <div>
          <label className="block font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-1.5">
            Center ingredient
          </label>
          <input
            type="text"
            value={center}
            onChange={(e) => setCenter(e.target.value)}
            placeholder="e.g. vanilla"
            className="font-serif text-base text-dark bg-card border-[1.5px] border-muted rounded px-3.5 py-2.5 outline-none transition-all duration-150 focus:border-accent focus:shadow-[0_0_0_2px_rgba(196,98,42,0.12)] placeholder:text-warm-light"
          />
        </div>

        <div>
          <label className="block font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-1.5">
            Max nodes
          </label>
          <input
            type="number"
            value={maxNodes}
            min={5}
            max={100}
            onChange={(e) => setMaxNodes(Number(e.target.value))}
            className="w-24 font-serif text-base text-dark bg-card border-[1.5px] border-muted rounded px-3.5 py-2.5 outline-none transition-all duration-150 focus:border-accent focus:shadow-[0_0_0_2px_rgba(196,98,42,0.12)]"
          />
        </div>

        <div>
          <label className="block font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-warm-mid mb-1.5">
            Min score
          </label>
          <input
            type="number"
            value={minScore}
            min={0}
            max={1}
            step={0.1}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-24 font-serif text-base text-dark bg-card border-[1.5px] border-muted rounded px-3.5 py-2.5 outline-none transition-all duration-150 focus:border-accent focus:shadow-[0_0_0_2px_rgba(196,98,42,0.12)]"
          />
        </div>

        <button
          onClick={fetchGraph}
          disabled={!center.trim() || loading}
          className="font-sans text-[11px] font-bold tracking-[0.08em] uppercase text-bg bg-accent px-6 py-2.5 rounded border-none cursor-pointer transition-colors duration-150 hover:bg-accent/80 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Explore
        </button>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="h-[500px] animate-pulse bg-card rounded-xl" />
      )}

      {/* Error */}
      {!loading && error && (
        <p className="font-serif text-[15px] italic text-warm-mid py-6">{error}</p>
      )}

      {/* Graph */}
      {!loading && data && (
        <>
          <div className="rounded-xl overflow-hidden border border-muted">
            <FlavorGraph data={data} />
          </div>
          <p className="font-sans text-[13px] text-warm-mid mt-3">
            {data.nodes.length} nodes, {data.edges.length} edges
          </p>
        </>
      )}

      {/* Empty state */}
      {!loading && !error && !data && (
        <p className="font-serif text-[15px] italic text-warm-mid py-6">
          Enter an ingredient above and click Explore to visualize its flavor network.
        </p>
      )}
    </>
  )
}
