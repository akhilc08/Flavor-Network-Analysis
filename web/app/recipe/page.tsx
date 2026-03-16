'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { streamRecipe } from '@/lib/api'

const INGREDIENTS = [
  'vanilla',
  'coffee',
  'chocolate',
  'strawberry',
  'lemon',
  'cinnamon',
  'butter',
  'cream',
  'honey',
  'cardamom',
  'rose',
  'ginger',
  'orange',
  'almond',
  'coconut',
  'caramel',
]

const MAX_SELECTED = 6

export default function RecipePage() {
  const [selected, setSelected] = useState<string[]>([])
  const [recipe, setRecipe] = useState<string>('')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  function toggle(ingredient: string) {
    setSelected(prev => {
      if (prev.includes(ingredient)) {
        return prev.filter(i => i !== ingredient)
      }
      if (prev.length >= MAX_SELECTED) return prev
      return [...prev, ingredient]
    })
  }

  async function handleGenerate() {
    if (selected.length < 2 || generating) return
    setGenerating(true)
    setRecipe('')
    setError(null)
    setDone(false)

    streamRecipe(
      { ingredients: selected, shared_molecules: [], flavor_labels: {} },
      (chunk) => setRecipe(prev => prev + chunk),
      () => {
        setGenerating(false)
        setDone(true)
      },
      (err) => {
        setError(err.message)
        setGenerating(false)
      },
    )
  }

  function handleReset() {
    setRecipe('')
    setDone(false)
    setError(null)
  }

  const canGenerate = selected.length >= 2 && !generating

  return (
    <main className="min-h-screen bg-bg py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <h1 className="font-serif text-3xl text-dark mb-2">Recipe Generator</h1>
        <p className="text-muted font-serif mb-8">Select 2–6 ingredients to generate a recipe</p>

        {/* Ingredient grid */}
        <section className="bg-card border border-[#e8d5bc] rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-lg text-dark">Ingredients</h2>
            <span className="text-sm text-muted font-sans">{selected.length}/{MAX_SELECTED} selected</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {INGREDIENTS.map(ingredient => {
              const isSelected = selected.includes(ingredient)
              return (
                <button
                  key={ingredient}
                  onClick={() => toggle(ingredient)}
                  className={[
                    'px-4 py-1.5 rounded-full text-sm font-sans capitalize transition-colors',
                    isSelected
                      ? 'bg-accent text-bg'
                      : 'bg-card border border-[#e8d5bc] text-dark hover:border-accent hover:text-accent',
                  ].join(' ')}
                >
                  {ingredient}
                </button>
              )
            })}
          </div>
        </section>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={!canGenerate}
          className={[
            'w-full py-3 rounded-lg font-sans text-base transition-colors flex items-center justify-center gap-2',
            canGenerate
              ? 'bg-accent text-bg hover:bg-accent/90 cursor-pointer'
              : 'bg-[#e8d5bc] text-muted cursor-not-allowed',
          ].join(' ')}
        >
          {generating && (
            <span className="inline-block w-4 h-4 border-2 border-bg border-t-transparent rounded-full animate-spin" />
          )}
          Generate Recipe
        </button>

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-card border border-red-300 rounded-lg text-sm font-sans text-red-700">
            {error}
          </div>
        )}

        {/* Recipe output */}
        {(recipe || generating) && !error && (
          <div className="mt-8 bg-card border border-[#e8d5bc] rounded-lg p-6">
            <div className="recipe-prose">
              <ReactMarkdown>{recipe}</ReactMarkdown>
              {generating && (
                <span
                  className="inline-block w-px h-4 bg-dark ml-0.5 align-middle"
                  style={{ animation: 'blink 1s step-end infinite' }}
                />
              )}
            </div>
          </div>
        )}

        {/* Generate Another */}
        {done && !generating && (
          <button
            onClick={handleReset}
            className="mt-6 w-full py-3 rounded-lg font-sans text-base bg-card border border-[#e8d5bc] text-dark hover:border-accent hover:text-accent transition-colors"
          >
            Generate Another
          </button>
        )}
      </div>

      <style jsx global>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </main>
  )
}
